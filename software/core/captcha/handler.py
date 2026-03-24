"""兼容层：阿里云智能验证逻辑已迁移到问卷星 provider。"""

from __future__ import annotations

from software.core.engine.submission import EmptySurveySubmissionError
from wjx.provider.submission import (
    AliyunCaptchaBypassError,
    wait_for_submission_verification,
)


def reset_captcha_popup_state() -> None:
    """兼容旧接口；当前弹窗状态由 TaskContext 内的问卷星 provider 流程维护。"""


def handle_aliyun_captcha(*args, **kwargs):
    """兼容旧接口，转发到问卷星 provider 的提交风控检测。"""
    return wait_for_submission_verification(*args, **kwargs)


__all__ = [
    "AliyunCaptchaBypassError",
    "EmptySurveySubmissionError",
    "handle_aliyun_captcha",
    "reset_captcha_popup_state",
]
