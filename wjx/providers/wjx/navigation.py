"""问卷星页面导航能力（provider 入口）。"""

from software.core.engine.navigation import (
    _click_next_page_button,
    _human_scroll_after_question,
    dismiss_resume_dialog_if_present,
    try_click_start_answer_button,
)

__all__ = [
    "_click_next_page_button",
    "_human_scroll_after_question",
    "dismiss_resume_dialog_if_present",
    "try_click_start_answer_button",
]


