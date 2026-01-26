import threading
from typing import Deque, List, Optional

import wjx.core.state as state
import wjx.modes.duration_control as duration_control
from wjx.modes.duration_control import DURATION_CONTROL_STATE as _DURATION_CONTROL_STATE


def _sync_full_sim_state_from_globals() -> None:
    """确保时长控制全局变量与模块状态保持一致（主要在 GUI/运行线程之间传递配置时使用）。"""
    _DURATION_CONTROL_STATE.enabled = bool(state.duration_control_enabled)
    _DURATION_CONTROL_STATE.estimated_seconds = int(state.duration_control_estimated_seconds or 0)
    _DURATION_CONTROL_STATE.total_duration_seconds = int(state.duration_control_total_duration_seconds or 0)


def _full_simulation_active() -> bool:
    _sync_full_sim_state_from_globals()
    return bool(_DURATION_CONTROL_STATE.active())


def _reset_full_simulation_runtime_state() -> None:
    _DURATION_CONTROL_STATE.reset_runtime()


def _prepare_full_simulation_schedule(run_count: int, total_duration_seconds: int) -> Deque[float]:
    schedule = _DURATION_CONTROL_STATE.prepare_schedule(run_count, total_duration_seconds)
    return schedule


def _wait_for_next_full_simulation_slot(stop_signal: threading.Event) -> bool:
    return _DURATION_CONTROL_STATE.wait_for_next_slot(stop_signal)


def _calculate_full_simulation_run_target(question_count: int) -> float:
    return _DURATION_CONTROL_STATE.calculate_run_target(question_count)


def _build_per_question_delay_plan(question_count: int, target_seconds: float) -> List[float]:
    return _DURATION_CONTROL_STATE.build_per_question_delay_plan(question_count, target_seconds)


def _simulate_answer_duration_delay(stop_signal: Optional[threading.Event] = None) -> bool:
    # 委托到模块实现，传入当前配置范围以避免模块依赖全局变量
    return duration_control.simulate_answer_duration_delay(stop_signal, state.answer_duration_range_seconds)
