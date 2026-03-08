"""快代理凭证持久化模块

将快代理凭证（secret_id 和 secret_key）独立存储到 configs/credentials.yml 文件中，
实现凭证的全局共享，避免每次解析新问卷时重复填写。

文件格式：
```yaml
kuaidaili:
  secret_id: "your_secret_id_here"
  secret_key: "your_secret_key_here"
  proxy_username: "proxy_username_here"
  proxy_password: "proxy_password_here"
```

注意：所有字段均为明文存储，便于跨设备复制使用。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

from wjx.utils.io.load_save import get_runtime_directory

__all__ = [
    "KuaidailiCredentials",
    "get_credentials_file_path",
    "load_kuaidaili_credentials",
    "save_kuaidaili_credentials",
]

# YAML 文件名
_CREDENTIALS_FILENAME = "credentials.yml"


@dataclass
class KuaidailiCredentials:
    """快代理凭证数据类
    
    Attributes:
        secret_id: 快代理账户标识符
        secret_key: 快代理密钥
        proxy_username: 代理鉴权用户名
        proxy_password: 代理鉴权密码
    
    注意：所有字段均为明文存储，便于跨设备复制使用。
    """
    secret_id: str = ""
    secret_key: str = ""
    proxy_username: str = ""
    proxy_password: str = ""


def get_credentials_file_path() -> str:
    """获取凭证文件路径
    
    Returns:
        凭证文件的完整路径: configs/credentials.yml
        
    Requirement 1.1: 使用 configs/credentials.yml 作为凭证存储文件路径
    """
    base = get_runtime_directory()
    return os.path.join(base, "configs", _CREDENTIALS_FILENAME)


def _ensure_configs_dir(file_path: Optional[str] = None) -> str:
    """确保凭证文件所在目录存在
    
    Args:
        file_path: 可选的凭证文件路径，如果提供则确保其父目录存在
        
    Returns:
        目录的完整路径
        
    Requirement 1.2: 当 configs 目录不存在时，自动创建该目录
    """
    if file_path:
        # 如果提供了自定义路径，确保其父目录存在
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        return parent_dir or "."
    else:
        # 默认使用项目根目录下的 configs 目录
        base = get_runtime_directory()
        configs_dir = os.path.join(base, "configs")
        os.makedirs(configs_dir, exist_ok=True)
        return configs_dir


def load_kuaidaili_credentials(path: Optional[str] = None) -> KuaidailiCredentials:
    """从 credentials.yml 加载快代理凭证
    
    Args:
        path: 可选的凭证文件路径，默认使用 get_credentials_file_path()
        
    Returns:
        KuaidailiCredentials 实例，如果文件不存在或解析失败则返回空凭证
        
    Requirements:
        1.3: 当凭证文件不存在时，返回空的默认值（空字符串）
        1.4: 使用 YAML 格式存储凭证数据
        2.2: 使用 decrypt_credential 函数解密 secret_key
        2.3: 以明文形式存储 secret_id
        2.4: 解密失败时返回空字符串并记录警告日志
        6.1: 包含 kuaidaili 顶级键
        6.2: 包含 secret_id 和 secret_key_encrypted 字段
        6.3: 使用 UTF-8 编码
    """
    file_path = path or get_credentials_file_path()
    
    # Requirement 1.3: 文件不存在时返回空凭证
    if not os.path.exists(file_path):
        return KuaidailiCredentials()
    
    try:
        import yaml
    except ImportError:
        logging.warning("PyYAML 库不可用，无法加载凭证文件")
        return KuaidailiCredentials()
    
    try:
        # Requirement 6.3: 使用 UTF-8 编码
        with open(file_path, "r", encoding="utf-8") as fp:
            data = yaml.safe_load(fp)
    except Exception as exc:
        logging.warning(f"读取凭证文件失败: {exc}")
        return KuaidailiCredentials()
    
    return _validate_credentials(data)


def _validate_credentials(data) -> KuaidailiCredentials:
    """验证并解析凭证数据
    
    Args:
        data: 从 YAML 文件加载的原始数据
        
    Returns:
        验证后的 KuaidailiCredentials 实例
    """
    if not isinstance(data, dict):
        return KuaidailiCredentials()
    
    kuaidaili = data.get("kuaidaili", {})
    if not isinstance(kuaidaili, dict):
        return KuaidailiCredentials()
    
    # 所有字段明文读取
    secret_id = str(kuaidaili.get("secret_id", "") or "").strip()
    secret_key = str(kuaidaili.get("secret_key", "") or "").strip()
    proxy_username = str(kuaidaili.get("proxy_username", "") or "").strip()
    proxy_password = str(kuaidaili.get("proxy_password", "") or "").strip()
    
    return KuaidailiCredentials(
        secret_id=secret_id,
        secret_key=secret_key,
        proxy_username=proxy_username,
        proxy_password=proxy_password,
    )


def save_kuaidaili_credentials(
    credentials: KuaidailiCredentials,
    path: Optional[str] = None
) -> None:
    """保存快代理凭证到 credentials.yml（明文存储）
    
    Args:
        credentials: 要保存的凭证
        path: 可选的凭证文件路径，默认使用 get_credentials_file_path()
    """
    try:
        import yaml
    except ImportError:
        logging.error("PyYAML 库不可用，无法保存凭证文件")
        return
    
    file_path = path or get_credentials_file_path()
    
    # 确保目录存在
    _ensure_configs_dir(file_path)
    
    # 构建 YAML 数据结构（所有字段明文存储）
    yaml_data = {
        "kuaidaili": {
            "secret_id": credentials.secret_id,
            "secret_key": credentials.secret_key,
            "proxy_username": credentials.proxy_username,
            "proxy_password": credentials.proxy_password,
        }
    }
    
    try:
        with open(file_path, "w", encoding="utf-8") as fp:
            yaml.dump(
                yaml_data,
                fp,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
    except Exception as exc:
        logging.error(f"保存凭证文件失败: {exc}")
