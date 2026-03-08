"""快代理适配器

将快代理集成到现有的代理提供者系统中。
"""
import logging
from typing import List, Optional

from wjx.network.proxy.kuaidaili import (
    KuaidailiAuth,
    fetch_kuaidaili_proxies,
    check_kuaidaili_connection,
    KuaidailiAuthError,
    KuaidailiAPIError,
)
from wjx.network.proxy.kuaidaili_config import (
    get_kuaidaili_config,
    is_kuaidaili_configured,
)

logger = logging.getLogger(__name__)


def fetch_proxies_from_kuaidaili(count: int = 1) -> List[str]:
    """从快代理获取代理列表
    
    Args:
        count: 获取数量
    
    Returns:
        代理地址列表，格式: ["ip:port", ...]
    
    Raises:
        RuntimeError: 配置错误或获取失败
    """
    if not is_kuaidaili_configured():
        raise RuntimeError("快代理未配置，请先在设置中填写 Secret ID 和 Secret Key")
    
    config = get_kuaidaili_config()
    auth = KuaidailiAuth(config["secret_id"], config["secret_key"])
    
    try:
        proxies = fetch_kuaidaili_proxies(
            auth=auth,
            count=count,
            auth_mode=config["auth_mode"],
            areas=config["areas"] if config["areas"] else None,
            timeout=10
        )
        
        if not proxies:
            raise RuntimeError("快代理返回空列表")
        
        # 转换为标准格式（添加 http:// 前缀）
        normalized = []
        for proxy in proxies:
            if "://" not in proxy:
                proxy = f"http://{proxy}"
            normalized.append(proxy)
        
        logger.info(f"从快代理获取到 {len(normalized)} 个代理")
        return normalized
        
    except KuaidailiAuthError as e:
        raise RuntimeError(f"快代理认证失败: {e}")
    except KuaidailiAPIError as e:
        raise RuntimeError(f"快代理API错误: {e}")
    except Exception as e:
        raise RuntimeError(f"获取快代理失败: {e}")


def test_kuaidaili_connection() -> dict:
    """测试快代理连接
    
    Returns:
        测试结果字典:
        {
            "success": bool,
            "message": str,
            "proxy_count": int,
            "proxies": List[str]
        }
    """
    if not is_kuaidaili_configured():
        return {
            "success": False,
            "message": "快代理未配置，请先填写 Secret ID 和 Secret Key"
        }
    
    config = get_kuaidaili_config()
    auth = KuaidailiAuth(config["secret_id"], config["secret_key"])
    
    return check_kuaidaili_connection(
        auth=auth,
        auth_mode=config["auth_mode"],
        areas=config["areas"] if config["areas"] else None
    )
