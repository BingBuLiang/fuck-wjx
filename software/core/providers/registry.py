"""Provider 调度入口。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from software.core.providers.common import (
    SURVEY_PROVIDER_QQ,
    SURVEY_PROVIDER_WJX,
    detect_survey_provider,
    normalize_survey_provider,
)
from tencent.parser import parse_qq_survey
from wjx.providers.wjx.parser import parse_wjx_survey


def _resolve_provider(*, provider: Optional[str] = None, ctx: Any = None) -> str:
    if provider is not None:
        return normalize_survey_provider(provider, default=SURVEY_PROVIDER_WJX)
    if ctx is not None:
        return normalize_survey_provider(
            getattr(ctx, "survey_provider", None),
            default=SURVEY_PROVIDER_WJX,
        )
    return SURVEY_PROVIDER_WJX


def parse_survey(url: str) -> Tuple[List[Dict[str, Any]], str, str]:
    """解析问卷结构，返回 (questions_info, title, provider)。"""
    provider = detect_survey_provider(url)
    if provider == SURVEY_PROVIDER_QQ:
        info, title = parse_qq_survey(url)
        return info, title, SURVEY_PROVIDER_QQ

    info, title = parse_wjx_survey(url)
    return info, title, SURVEY_PROVIDER_WJX


def fill_survey(
    driver: Any,
    ctx: Any,
    *,
    stop_signal: Any = None,
    thread_name: str = "",
    psycho_plan: Any = None,
    provider: Optional[str] = None,
) -> bool:
    """Provider 运行时答题分发。"""
    resolved = _resolve_provider(provider=provider, ctx=ctx)
    if resolved == SURVEY_PROVIDER_QQ:
        # 延迟导入，避免引入 provider runtime 与 core.engine 的循环依赖。
        from tencent.runtime import brush_qq

        return bool(
            brush_qq(
                driver,
                ctx,
                stop_signal=stop_signal,
                thread_name=thread_name,
                psycho_plan=psycho_plan,
            )
        )

    if resolved == SURVEY_PROVIDER_WJX:
        from wjx.providers.wjx.runtime import fill_survey as fill_wjx_survey

        return bool(
            fill_wjx_survey(
                driver,
                ctx,
                stop_signal=stop_signal,
                thread_name=thread_name,
                psycho_plan=psycho_plan,
            )
        )

    raise RuntimeError(f"不支持的问卷 provider: {resolved}")


def is_completion_page(driver: Any, provider: Optional[str] = None) -> bool:
    """Provider 完成页识别分发。"""
    resolved = _resolve_provider(provider=provider)
    if resolved == SURVEY_PROVIDER_QQ:
        from tencent.runtime import qq_is_completion_page

        return bool(qq_is_completion_page(driver))
    return False


def submission_requires_verification(driver: Any, provider: Optional[str] = None) -> bool:
    """Provider 提交后风控/验证识别分发。"""
    resolved = _resolve_provider(provider=provider)
    if resolved == SURVEY_PROVIDER_QQ:
        from tencent.runtime import qq_submission_requires_verification

        return bool(qq_submission_requires_verification(driver))
    return False


def submission_validation_message(driver: Any, provider: Optional[str] = None) -> str:
    """Provider 提交后校验文案提取分发。"""
    resolved = _resolve_provider(provider=provider)
    if resolved == SURVEY_PROVIDER_QQ:
        from tencent.runtime import qq_submission_validation_message

        return str(qq_submission_validation_message(driver) or "").strip()
    return ""


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


