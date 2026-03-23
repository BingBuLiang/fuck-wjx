"""问卷星提交流程能力（provider 入口）。"""

from software.core.engine.submission import (
    _click_submit_button,
    _is_device_quota_limit_page,
    _is_wjx_domain,
    _looks_like_wjx_survey_url,
    _normalize_url_for_compare,
    _page_looks_like_wjx_questionnaire,
    submit,
)

__all__ = [
    "_click_submit_button",
    "_is_device_quota_limit_page",
    "_is_wjx_domain",
    "_looks_like_wjx_survey_url",
    "_normalize_url_for_compare",
    "_page_looks_like_wjx_questionnaire",
    "submit",
]


