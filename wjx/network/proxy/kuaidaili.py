"""
快代理 (kuaidaili.com) 认证与代理获取模块

支持两种认证方式：
1. 密钥令牌 (token) - 推荐，secret_key 仅传输一次获取令牌
2. 数字签名 (hmacsha1) - 最安全，secret_key 永不传输

注意：快代理 API 强制签名验证，不支持纯 IP 白名单认证。
使用代理时的认证（用户名密码 vs IP白名单）是另一回事，通过 get_proxy_authorization() 获取。
"""

import base64
import hashlib
import hmac
import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)

# API 端点
AUTH_API_BASE = "https://auth.kdlapi.com"
DPS_API_BASE = "https://dps.kdlapi.com"
DEV_API_BASE = "https://dev.kdlapi.com"

# 令牌提前刷新时间（秒）
TOKEN_REFRESH_MARGIN = 180  # 3分钟


@dataclass
class TokenInfo:
    """令牌信息"""
    token: str
    expire_at: float  # Unix 时间戳


class KuaidailiAuth:
    """快代理认证管理类
    
    支持密钥令牌和数字签名两种认证方式。
    
    使用示例:
        auth = KuaidailiAuth(secret_id, secret_key)
        
        # 密钥令牌方式
        params = auth.build_request_params({"num": 1}, auth_mode="token")
        
        # 数字签名方式
        params = auth.build_request_params({"num": 1}, auth_mode="signature")
    """
    
    def __init__(self, secret_id: str, secret_key: str):
        """
        Args:
            secret_id: 快代理 Secret ID
            secret_key: 快代理 Secret Key
        """
        self.secret_id = secret_id
        self.secret_key = secret_key
        self._token_info: Optional[TokenInfo] = None
    
    def get_signature(self, method: str, endpoint: str, params: Dict) -> str:
        """生成 HMAC-SHA1 数字签名
        
        签名原文格式: METHOD/endpoint?param1=value1&param2=value2
        参数按字母顺序排序，不包含 signature、timeout、max_retries 参数
        
        注意：sign_type 参数需要参与签名计算（与官方SDK一致）
        
        Args:
            method: HTTP 方法，如 "GET"
            endpoint: API 端点，如 "/api/getdps"
            params: 请求参数字典（不含 signature）
        
        Returns:
            Base64 编码的签名字符串
        """
        # 移除不参与签名的参数（与SDK的clear_req_params一致）
        sign_params = {k: v for k, v in params.items() if k not in ('timeout', 'max_retries', 'signature')}
        
        # 参数按字母顺序排序，使用 & 连接（不做 URL 编码）
        query_str = '&'.join(f"{k}={sign_params[k]}" for k in sorted(sign_params))
        
        # 构造签名原文: METHOD/endpoint?query_string
        raw_str = f"{method.upper()}{endpoint}?{query_str}"
        
        logger.debug(f"签名原文: {raw_str}")
        
        # HMAC-SHA1 签名
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            raw_str.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Base64 编码
        result = base64.b64encode(signature).decode('utf-8')
        logger.debug(f"签名结果: {result}")
        return result
    
    def get_secret_token(self, force_refresh: bool = False) -> str:
        """获取密钥令牌
        
        令牌会被缓存，在过期前 3 分钟自动刷新。
        
        Args:
            force_refresh: 是否强制刷新令牌
        
        Returns:
            密钥令牌字符串
        
        Raises:
            KuaidailiAuthError: 认证失败
        """
        now = time.time()
        
        # 检查缓存的令牌是否有效
        if not force_refresh and self._token_info:
            if now < self._token_info.expire_at - TOKEN_REFRESH_MARGIN:
                return self._token_info.token
            logger.debug("令牌即将过期，自动刷新")
        
        # 请求新令牌
        url = f"{AUTH_API_BASE}/api/get_secret_token"
        data = {
            "secret_id": self.secret_id,
            "secret_key": self.secret_key,
        }
        
        logger.debug(f"获取令牌请求: URL={url}, secret_id={self.secret_id[:8]}***")
        
        try:
            resp = requests.post(url, data=data, timeout=10)
            logger.debug(f"获取令牌响应: status={resp.status_code}")
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as e:
            logger.error(f"获取令牌请求失败: {e}")
            raise KuaidailiAuthError(f"网络请求失败: {e}") from e
        
        # 解析响应
        if result.get("code") != 0:
            msg = result.get("msg", "未知错误")
            logger.error(f"获取令牌失败: {msg}")
            raise KuaidailiAuthError(f"认证失败: {msg}")
        
        token_data = result.get("data", {})
        token = token_data.get("secret_token")
        expire = token_data.get("expire", 3600)
        
        if not token:
            raise KuaidailiAuthError("响应中缺少 secret_token")
        
        # 缓存令牌
        self._token_info = TokenInfo(
            token=token,
            expire_at=now + expire
        )
        
        logger.debug(f"获取新令牌成功，有效期 {expire} 秒")
        return token
    
    def build_request_params(
        self,
        base_params: Dict,
        auth_mode: str,
        endpoint: str = "/api/getdps",
        method: str = "GET"
    ) -> Dict:
        """根据认证模式构建完整请求参数
        
        Args:
            base_params: 基础请求参数
            auth_mode: 认证模式 ("token", "signature"/"hmacsha1")
            endpoint: API 端点，如 "/api/getdps"
            method: HTTP 方法（签名模式需要）
        
        Returns:
            包含认证参数的完整请求参数字典
        
        Raises:
            ValueError: 不支持的认证模式
        """
        params = dict(base_params)
        params["secret_id"] = self.secret_id
        
        if auth_mode == "token":
            # 密钥令牌方式
            token = self.get_secret_token()
            params["signature"] = token
            
        elif auth_mode in ("signature", "hmacsha1"):
            # 数字签名方式
            # sign_type 参数需要参与签名计算
            params["sign_type"] = "hmacsha1"
            params["timestamp"] = int(time.time())
            signature = self.get_signature(method, endpoint, params)
            params["signature"] = signature
            
        else:
            raise ValueError(f"不支持的认证模式: {auth_mode}，请使用 'token' 或 'signature'")
        
        return params
    
    def clear_token_cache(self):
        """清除令牌缓存"""
        self._token_info = None
        logger.debug("令牌缓存已清除")


class KuaidailiAuthError(Exception):
    """快代理认证错误"""
    pass


class KuaidailiAPIError(Exception):
    """快代理API调用错误"""
    pass


# ============================================================
# Phase 2: 代理获取与白名单管理
# ============================================================

# 公网IP检测服务（按优先级排序）
PUBLIC_IP_SERVICES = [
    "https://httpbin.org/ip",
    "https://api.ipify.org?format=json",
    "https://ifconfig.me/ip",
]


def get_public_ip(timeout: int = 5) -> str:
    """获取本机公网IP
    
    尝试多个服务，返回第一个成功的结果。
    
    Args:
        timeout: 请求超时时间（秒）
    
    Returns:
        公网IP地址字符串
    
    Raises:
        KuaidailiAPIError: 无法获取公网IP
    """
    errors = []
    
    for url in PUBLIC_IP_SERVICES:
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            
            # 解析响应
            if "json" in resp.headers.get("Content-Type", ""):
                data = resp.json()
                # httpbin.org 返回 {"origin": "ip"}
                # ipify 返回 {"ip": "ip"}
                ip = data.get("origin") or data.get("ip")
            else:
                ip = resp.text.strip()
            
            if ip:
                logger.debug(f"获取公网IP成功: {ip}")
                return ip
                
        except Exception as e:
            errors.append(f"{url}: {e}")
            continue
    
    error_msg = "; ".join(errors)
    logger.error(f"获取公网IP失败: {error_msg}")
    raise KuaidailiAPIError(f"无法获取公网IP: {error_msg}")


def fetch_kuaidaili_proxies(
    auth: KuaidailiAuth,
    count: int = 1,
    auth_mode: str = "token",
    areas: Optional[List[str]] = None,
    timeout: int = 10
) -> List[str]:
    """从快代理获取代理列表
    
    Args:
        auth: 认证对象
        count: 获取数量（1-100）
        auth_mode: 认证方式 ("token", "signature", "whitelist")
        areas: 地区名称列表，如 ["上海", "广东"]，为空表示全国随机
               如果指定多个地区，每次请求随机选择一个
               支持中文省份名称，如：北京、上海、广东、浙江等
        timeout: 请求超时时间（秒）
    
    Returns:
        代理地址列表，格式: ["ip:port", ...]
    
    Raises:
        KuaidailiAPIError: API调用失败
        KuaidailiAuthError: 认证失败
    """
    import random
    
    # 构建基础参数
    base_params = {
        "num": min(max(count, 1), 100),  # 限制 1-100
        "pt": 1,   # 返回格式: ip:port
        "format": "json",  # 返回 JSON 格式
    }
    
    # 如果指定了地区，随机选择一个（使用中文名称）
    if areas:
        selected_area = random.choice(areas)
        base_params["area"] = selected_area
        logger.debug(f"选择地区: {selected_area}")
    
    # 构建认证参数
    endpoint = "/api/getdps"
    params = auth.build_request_params(base_params, auth_mode, endpoint, "GET")
    
    # 发送请求
    url = f"{DPS_API_BASE}{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"获取代理请求失败: {e}")
        raise KuaidailiAPIError(f"网络请求失败: {e}") from e
    
    # 解析响应
    try:
        result = resp.json()
    except ValueError:
        # 可能直接返回代理列表文本
        text = resp.text.strip()
        if text and not text.startswith("{"):
            proxies = [p.strip() for p in text.split() if p.strip()]
            if proxies:
                logger.info(f"获取到 {len(proxies)} 个代理")
                return proxies
        raise KuaidailiAPIError(f"无法解析响应: {resp.text[:200]}")
    
    # JSON 响应处理
    code = result.get("code", -1)
    if code != 0:
        msg = result.get("msg", "未知错误")
        logger.error(f"获取代理失败: {msg}")
        raise KuaidailiAPIError(f"API错误: {msg}")
    
    # 解析代理列表
    data = result.get("data", {})
    proxy_list = data.get("proxy_list", [])
    
    if not proxy_list:
        logger.warning("API返回空代理列表")
        return []
    
    logger.info(f"获取到 {len(proxy_list)} 个代理")
    return proxy_list


def get_whitelist(auth: KuaidailiAuth, auth_mode: str = "token") -> List[str]:
    """获取当前IP白名单列表
    
    Args:
        auth: 认证对象
        auth_mode: 认证方式
    
    Returns:
        白名单IP列表
    
    Raises:
        KuaidailiAPIError: API调用失败
    """
    endpoint = "/api/getipwhitelist"
    params = auth.build_request_params({}, auth_mode, endpoint, "GET")
    
    url = f"{DEV_API_BASE}{endpoint}"
    logger.info(f"获取白名单请求: URL={url}, auth_mode={auth_mode}")
    logger.debug(f"请求参数: {params}")
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        logger.debug(f"获取白名单响应: status={resp.status_code}, body={resp.text[:500]}")
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        logger.error(f"获取白名单请求失败: {e}")
        raise KuaidailiAPIError(f"网络请求失败: {e}") from e
    except ValueError as e:
        logger.error(f"获取白名单响应解析失败: {e}, body={resp.text[:200]}")
        raise KuaidailiAPIError(f"响应解析失败: {e}") from e
    
    if result.get("code") != 0:
        code = result.get('code')
        msg = result.get("msg", "未知错误")
        logger.error(f"获取白名单API错误: code={code}, msg={msg}")
        
        # 提供更详细的错误说明
        if code == -108:
            logger.error("错误说明: 当前IP不在API调用授权白名单中。")
            logger.error("解决方法: 请登录快代理后台 -> API接口 -> 密钥管理 -> API调用授权 -> 添加当前IP到白名单")
        
        raise KuaidailiAPIError(f"获取白名单失败: {msg}")
    
    data = result.get("data", {})
    ipwhitelist = data.get("ipwhitelist", [])
    
    logger.debug(f"获取白名单成功: {ipwhitelist}")
    
    if not ipwhitelist:
        return []
    
    # API 可能返回 list 或逗号分隔的字符串
    if isinstance(ipwhitelist, list):
        return ipwhitelist
    return [ip.strip() for ip in ipwhitelist.split(",") if ip.strip()]


def add_ip_to_whitelist(
    auth: KuaidailiAuth,
    ip: str,
    auth_mode: str = "token"
) -> bool:
    """添加IP到白名单
    
    Args:
        auth: 认证对象
        ip: 要添加的IP地址
        auth_mode: 认证方式
    
    Returns:
        是否添加成功
    
    Raises:
        KuaidailiAPIError: API调用失败
    """
    logger.info(f"添加IP到白名单: ip={ip}, auth_mode={auth_mode}")
    
    endpoint = "/api/setipwhitelist"
    
    # 先获取现有白名单
    logger.debug("获取现有白名单...")
    current_list = get_whitelist(auth, auth_mode)
    logger.debug(f"现有白名单: {current_list}")
    
    # 检查是否已存在
    if ip in current_list:
        logger.info(f"IP {ip} 已在白名单中")
        return True
    
    # 添加新IP
    new_list = current_list + [ip]
    iplist_str = ",".join(new_list)
    logger.debug(f"新白名单: {iplist_str}")
    
    base_params = {"iplist": iplist_str}
    params = auth.build_request_params(base_params, auth_mode, endpoint, "POST")
    
    url = f"{DEV_API_BASE}{endpoint}"
    logger.debug(f"设置白名单请求: URL={url}")
    
    try:
        resp = requests.post(url, data=params, timeout=10)
        logger.debug(f"设置白名单响应: status={resp.status_code}, body={resp.text[:500]}")
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        logger.error(f"设置白名单请求失败: {e}")
        raise KuaidailiAPIError(f"网络请求失败: {e}") from e
    
    if result.get("code") != 0:
        msg = result.get("msg", "未知错误")
        logger.error(f"设置白名单API错误: code={result.get('code')}, msg={msg}")
        raise KuaidailiAPIError(f"设置白名单失败: {msg}")
    
    logger.info(f"成功添加 {ip} 到白名单")
    return True


def remove_ip_from_whitelist(
    auth: KuaidailiAuth,
    ip: str,
    auth_mode: str = "token"
) -> bool:
    """从白名单移除IP
    
    Args:
        auth: 认证对象
        ip: 要移除的IP地址
        auth_mode: 认证方式
    
    Returns:
        是否移除成功
    
    Raises:
        KuaidailiAPIError: API调用失败
    """
    endpoint = "/api/setipwhitelist"
    
    # 获取现有白名单
    current_list = get_whitelist(auth, auth_mode)
    
    # 检查是否存在
    if ip not in current_list:
        logger.info(f"IP {ip} 不在白名单中")
        return True
    
    # 移除IP
    new_list = [x for x in current_list if x != ip]
    iplist_str = ",".join(new_list) if new_list else ""
    
    base_params = {"iplist": iplist_str}
    params = auth.build_request_params(base_params, auth_mode, endpoint, "POST")
    
    url = f"{DEV_API_BASE}{endpoint}"
    try:
        resp = requests.post(url, data=params, timeout=10)
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        logger.error(f"设置白名单请求失败: {e}")
        raise KuaidailiAPIError(f"网络请求失败: {e}") from e
    
    if result.get("code") != 0:
        msg = result.get("msg", "未知错误")
        raise KuaidailiAPIError(f"设置白名单失败: {msg}")
    
    logger.info(f"成功从白名单移除 {ip}")
    return True


def get_proxy_authorization(
    auth: KuaidailiAuth,
    auth_mode: str = "token",
    plaintext: int = 0
) -> dict:
    """获取代理鉴权信息（用户名密码）
    
    用于获取使用代理时的用户名密码，这样就不依赖IP白名单。
    
    Args:
        auth: 认证对象
        auth_mode: 认证方式
        plaintext: 是否返回明文密码 (0=加密, 1=明文)
    
    Returns:
        包含 username 和 password 的字典
    
    Raises:
        KuaidailiAPIError: API调用失败
    """
    endpoint = "/api/getproxyauthorization"
    base_params = {"plaintext": plaintext}
    params = auth.build_request_params(base_params, auth_mode, endpoint, "GET")
    
    url = f"{DEV_API_BASE}{endpoint}"
    logger.info(f"获取代理鉴权请求: URL={url}, auth_mode={auth_mode}, plaintext={plaintext}")
    
    try:
        resp = requests.get(url, params=params, timeout=10)
        logger.debug(f"获取代理鉴权响应: status={resp.status_code}, body={resp.text[:500]}")
        resp.raise_for_status()
        result = resp.json()
    except requests.RequestException as e:
        logger.error(f"获取代理鉴权信息请求失败: {e}")
        raise KuaidailiAPIError(f"网络请求失败: {e}") from e
    
    if result.get("code") != 0:
        msg = result.get("msg", "未知错误")
        logger.error(f"获取代理鉴权API错误: code={result.get('code')}, msg={msg}")
        raise KuaidailiAPIError(f"获取代理鉴权信息失败: {msg}")
    
    data = result.get("data", {})
    logger.info(f"获取代理鉴权成功: data={data}")
    
    return {
        "username": data.get("username", ""),
        "password": data.get("password", ""),
    }


def check_kuaidaili_connection(
    auth: KuaidailiAuth,
    auth_mode: str = "token",
    areas: Optional[List[str]] = None
) -> dict:
    """测试快代理连接
    
    Args:
        auth: 认证对象
        auth_mode: 认证方式
        areas: 地区列表（可选）
    
    Returns:
        测试结果字典:
        {
            "success": bool,
            "message": str,
            "proxy_count": int,  # 成功时返回
            "proxies": List[str]  # 成功时返回
        }
    """
    try:
        proxies = fetch_kuaidaili_proxies(
            auth=auth,
            count=1,
            auth_mode=auth_mode,
            areas=areas
        )
        return {
            "success": True,
            "message": f"连接成功，获取到 {len(proxies)} 个代理",
            "proxy_count": len(proxies),
            "proxies": proxies
        }
    except KuaidailiAuthError as e:
        return {
            "success": False,
            "message": f"认证失败: {e}"
        }
    except KuaidailiAPIError as e:
        return {
            "success": False,
            "message": f"API错误: {e}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"未知错误: {e}"
        }
