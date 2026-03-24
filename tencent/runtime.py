"""兼容层：旧路径 tencent.runtime 转发到 tencent.provider.runtime。"""

from tencent.provider.runtime import (
    QQ_COMPLETION_MARKERS,
    QQ_VALIDATION_MARKERS,
    QQ_VERIFICATION_MARKERS,
    brush_qq,
    qq_is_completion_page,
    qq_submission_requires_verification,
    qq_submission_validation_message,
)

__all__ = [
    "QQ_COMPLETION_MARKERS",
    "QQ_VERIFICATION_MARKERS",
    "QQ_VALIDATION_MARKERS",
    "brush_qq",
    "qq_is_completion_page",
    "qq_submission_requires_verification",
    "qq_submission_validation_message",
]
