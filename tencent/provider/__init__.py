"""腾讯问卷平台实现。"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

_EXPORTS: Dict[str, Tuple[str, str]] = {
    "QQ_SUPPORTED_PROVIDER_TYPES": ("tencent.provider.parser", "QQ_SUPPORTED_PROVIDER_TYPES"),
    "QQ_PROVIDER_TYPE_TO_INTERNAL": ("tencent.provider.parser", "QQ_PROVIDER_TYPE_TO_INTERNAL"),
    "parse_qq_survey": ("tencent.provider.parser", "parse_qq_survey"),
    "brush_qq": ("tencent.provider.runtime", "brush_qq"),
    "qq_is_completion_page": ("tencent.provider.runtime", "qq_is_completion_page"),
    "qq_submission_requires_verification": ("tencent.provider.runtime", "qq_submission_requires_verification"),
    "qq_submission_validation_message": ("tencent.provider.runtime", "qq_submission_validation_message"),
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
