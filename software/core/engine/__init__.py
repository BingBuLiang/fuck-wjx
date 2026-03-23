"""引擎模块按需导出，避免初始化阶段循环导入。"""

from __future__ import annotations

from importlib import import_module
from typing import Any, Dict, Tuple

# name -> (module, attribute)
_EXPORTS: Dict[str, Tuple[str, str]] = {
    "parse_survey_questions_from_html": ("software.core.survey.parser", "parse_survey_questions_from_html"),
    "_extract_survey_title_from_html": ("software.core.survey.parser", "extract_survey_title_from_html"),
    "_normalize_html_text": ("software.core.survey.parser", "_normalize_html_text"),
    "_normalize_question_type_code": ("software.core.survey.parser", "_normalize_question_type_code"),
    "create_playwright_driver": ("software.core.engine.driver_factory", "create_playwright_driver"),
    "_is_headless_mode": ("software.core.engine.runtime_control", "_is_headless_mode"),
    "_timed_mode_active": ("software.core.engine.runtime_control", "_timed_mode_active"),
    "_handle_submission_failure": ("software.core.engine.runtime_control", "_handle_submission_failure"),
    "_wait_if_paused": ("software.core.engine.runtime_control", "_wait_if_paused"),
    "_trigger_target_reached_stop": ("software.core.engine.runtime_control", "_trigger_target_reached_stop"),
    "_driver_question_looks_like_rating": ("wjx.providers.wjx.dom_helpers", "_driver_question_looks_like_rating"),
    "_driver_question_looks_like_reorder": ("wjx.providers.wjx.dom_helpers", "_driver_question_looks_like_reorder"),
    "_count_choice_inputs_driver": ("wjx.providers.wjx.dom_helpers", "_count_choice_inputs_driver"),
    "try_click_start_answer_button": ("software.core.engine.navigation", "try_click_start_answer_button"),
    "dismiss_resume_dialog_if_present": ("software.core.engine.navigation", "dismiss_resume_dialog_if_present"),
    "detect": ("wjx.providers.wjx.detection", "detect"),
    "_human_scroll_after_question": ("software.core.engine.navigation", "_human_scroll_after_question"),
    "_click_next_page_button": ("software.core.engine.navigation", "_click_next_page_button"),
    "_click_submit_button": ("software.core.engine.submission", "_click_submit_button"),
    "_sleep_with_stop": ("software.core.engine.runtime_control", "_sleep_with_stop"),
    "brush": ("software.core.engine.answering", "brush"),
    "submit": ("software.core.engine.submission", "submit"),
    "_normalize_url_for_compare": ("software.core.engine.submission", "_normalize_url_for_compare"),
    "_is_wjx_domain": ("software.core.engine.submission", "_is_wjx_domain"),
    "_looks_like_wjx_survey_url": ("software.core.engine.submission", "_looks_like_wjx_survey_url"),
    "_page_looks_like_wjx_questionnaire": ("software.core.engine.submission", "_page_looks_like_wjx_questionnaire"),
    "_is_device_quota_limit_page": ("software.core.engine.submission", "_is_device_quota_limit_page"),
    "run": ("software.core.engine.runner", "run"),
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


