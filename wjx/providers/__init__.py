"""Provider 能力聚合导出（仅导出平台无关常量与工具）。"""

from software.core.providers.common import (
    SURVEY_PROVIDER_QQ,
    SURVEY_PROVIDER_WJX,
    SUPPORTED_SURVEY_PROVIDERS,
    detect_survey_provider,
    ensure_question_provider_fields,
    ensure_questions_provider_fields,
    is_qq_survey_url,
    is_supported_survey_url,
    is_wjx_domain,
    is_wjx_survey_url,
    normalize_survey_provider,
)

__all__ = [
    "SURVEY_PROVIDER_WJX",
    "SURVEY_PROVIDER_QQ",
    "SUPPORTED_SURVEY_PROVIDERS",
    "normalize_survey_provider",
    "is_wjx_domain",
    "is_wjx_survey_url",
    "is_qq_survey_url",
    "detect_survey_provider",
    "is_supported_survey_url",
    "ensure_question_provider_fields",
    "ensure_questions_provider_fields",
]


