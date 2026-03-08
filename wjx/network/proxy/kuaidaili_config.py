"""快代理配置管理模块

管理快代理的配置信息，包括 Secret ID、Secret Key、认证模式和地区设置。
"""
import logging
from typing import List, Optional

# 快代理配置状态
_kuaidaili_secret_id: str = ""
_kuaidaili_secret_key: str = ""
_kuaidaili_auth_mode: str = "token"
_kuaidaili_areas: List[str] = []


def get_kuaidaili_config() -> dict:
    """获取快代理配置
    
    Returns:
        配置字典:
        {
            "secret_id": str,
            "secret_key": str,
            "auth_mode": str,  # "token", "signature"
            "areas": List[str]  # 地区名称列表
        }
    """
    return {
        "secret_id": _kuaidaili_secret_id,
        "secret_key": _kuaidaili_secret_key,
        "auth_mode": _kuaidaili_auth_mode,
        "areas": list(_kuaidaili_areas),
    }


def set_kuaidaili_config(
    secret_id: Optional[str] = None,
    secret_key: Optional[str] = None,
    auth_mode: Optional[str] = None,
    areas: Optional[List[str]] = None
) -> None:
    """设置快代理配置
    
    Args:
        secret_id: Secret ID
        secret_key: Secret Key
        auth_mode: 认证模式 ("token", "signature")
        areas: 地区名称列表，如 ["上海", "广东"]
    """
    global _kuaidaili_secret_id, _kuaidaili_secret_key, _kuaidaili_auth_mode, _kuaidaili_areas
    
    if secret_id is not None:
        _kuaidaili_secret_id = str(secret_id).strip()
    
    if secret_key is not None:
        _kuaidaili_secret_key = str(secret_key).strip()
    
    if auth_mode is not None:
        if auth_mode in ("token", "signature"):
            _kuaidaili_auth_mode = auth_mode
        else:
            logging.warning(f"无效的认证模式: {auth_mode}，使用默认值 token")
            _kuaidaili_auth_mode = "token"
    
    if areas is not None:
        _kuaidaili_areas = [str(a).strip() for a in areas if a]
    
    logging.debug(f"快代理配置已更新: secret_id={_kuaidaili_secret_id[:4]}***, auth_mode={_kuaidaili_auth_mode}, areas={_kuaidaili_areas}")


def is_kuaidaili_configured() -> bool:
    """检查快代理是否已配置"""
    return bool(_kuaidaili_secret_id and _kuaidaili_secret_key)


def get_kuaidaili_secret_id() -> str:
    """获取 Secret ID"""
    return _kuaidaili_secret_id


def get_kuaidaili_secret_key() -> str:
    """获取 Secret Key"""
    return _kuaidaili_secret_key


def get_kuaidaili_auth_mode() -> str:
    """获取认证模式"""
    return _kuaidaili_auth_mode


def get_kuaidaili_areas() -> List[str]:
    """获取地区列表"""
    return list(_kuaidaili_areas)
