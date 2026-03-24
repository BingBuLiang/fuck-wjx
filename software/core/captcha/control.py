"""兼容层：阿里云智能验证处理已迁移到问卷星 provider。"""

from __future__ import annotations

from wjx.provider.submission import handle_submission_verification_detected


def _handle_aliyun_captcha_detected(ctx, gui_instance, stop_signal) -> None:
    """兼容旧接口，转发到问卷星 provider 的风控命中处理。"""
    handle_submission_verification_detected(ctx, gui_instance, stop_signal)


__all__ = ["_handle_aliyun_captcha_detected"]
