"""平台识别与分发包。

这里采用惰性导出，避免仅导入 `software.providers.common`
时把整套平台注册与运行时模块提前拉起，放大循环依赖风险。
"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

_EXPORTS: Dict[str, Tuple[str, str]] = {
    "SURVEY_PROVIDER_WJX": ("software.providers.common", "SURVEY_PROVIDER_WJX"),
    "SURVEY_PROVIDER_QQ": ("software.providers.common", "SURVEY_PROVIDER_QQ"),
    "SUPPORTED_SURVEY_PROVIDERS": ("software.providers.common", "SUPPORTED_SURVEY_PROVIDERS"),
    "normalize_survey_provider": ("software.providers.common", "normalize_survey_provider"),
    "is_wjx_domain": ("software.providers.common", "is_wjx_domain"),
    "is_wjx_survey_url": ("software.providers.common", "is_wjx_survey_url"),
    "is_qq_survey_url": ("software.providers.common", "is_qq_survey_url"),
    "detect_survey_provider": ("software.providers.common", "detect_survey_provider"),
    "is_supported_survey_url": ("software.providers.common", "is_supported_survey_url"),
    "ensure_question_provider_fields": ("software.providers.common", "ensure_question_provider_fields"),
    "ensure_questions_provider_fields": ("software.providers.common", "ensure_questions_provider_fields"),
    "parse_survey": ("software.providers.registry", "parse_survey"),
    "fill_survey": ("software.providers.registry", "fill_survey"),
    "is_completion_page": ("software.providers.registry", "is_completion_page"),
    "handle_submission_verification_detected": ("software.providers.registry", "handle_submission_verification_detected"),
    "submission_requires_verification": ("software.providers.registry", "submission_requires_verification"),
    "submission_validation_message": ("software.providers.registry", "submission_validation_message"),
    "wait_for_submission_verification": ("software.providers.registry", "wait_for_submission_verification"),
}

__all__ = list(_EXPORTS.keys())


def __getattr__(name: str) -> Any:
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = target
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
