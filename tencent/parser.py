"""兼容层：旧路径 tencent.parser 转发到 tencent.provider.parser。"""

from tencent.provider.parser import (
    QQ_PROVIDER_TYPE_TO_INTERNAL,
    QQ_SUPPORTED_PROVIDER_TYPES,
    parse_qq_survey,
)

__all__ = [
    "QQ_SUPPORTED_PROVIDER_TYPES",
    "QQ_PROVIDER_TYPE_TO_INTERNAL",
    "parse_qq_survey",
]
