"""核心配置模型与编解码能力。"""

from software.core.config.codec import (
    CURRENT_CONFIG_SCHEMA_VERSION,
    _CURRENT_CONFIG_SCHEMA_VERSION,
    _LEGACY_CONFIG_KEYS,
    _ensure_supported_config_payload,
    _select_user_agent_from_ratios,
    deserialize_question_entry,
    deserialize_runtime_config,
    normalize_runtime_config_payload,
    serialize_question_entry,
    serialize_runtime_config,
)
from software.core.config.schema import RuntimeConfig

__all__ = [
    "CURRENT_CONFIG_SCHEMA_VERSION",
    "_CURRENT_CONFIG_SCHEMA_VERSION",
    "_LEGACY_CONFIG_KEYS",
    "RuntimeConfig",
    "_ensure_supported_config_payload",
    "_select_user_agent_from_ratios",
    "serialize_question_entry",
    "deserialize_question_entry",
    "normalize_runtime_config_payload",
    "serialize_runtime_config",
    "deserialize_runtime_config",
]


