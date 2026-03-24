"""兼容层：旧路径 software.core.providers.registry 转发到 software.providers.registry。"""

from software.providers.registry import (
    SURVEY_PROVIDER_QQ,
    SURVEY_PROVIDER_WJX,
    detect_survey_provider,
    fill_survey,
    is_completion_page,
    parse_survey,
    submission_requires_verification,
    submission_validation_message,
)

__all__ = [
    "SURVEY_PROVIDER_WJX",
    "SURVEY_PROVIDER_QQ",
    "detect_survey_provider",
    "parse_survey",
    "fill_survey",
    "is_completion_page",
    "submission_requires_verification",
    "submission_validation_message",
]
