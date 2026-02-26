"""完全模拟模式 - 仿真人类操作行为"""
import threading
from typing import Deque, List, Optional

import wjx.modes.duration_control as duration_control
from wjx.core.task_context import TaskContext
from wjx.modes.duration_control import DURATION_CONTROL_STATE as _DURATION_CONTROL_STATE


def _sync_full_sim_state_from_ctx(ctx: TaskContext) -> None:
    """将 TaskContext 中的时长控制配置同步到模块状态。"""
    _DURATION_CONTROL_STATE.enabled = bool(ctx.duration_control_enabled)
    _DURATION_CONTROL_STATE.estimated_seconds = int(ctx.duration_control_estimated_seconds or 0)
    _DURATION_CONTROL_STATE.total_duration_seconds = int(ctx.duration_control_total_duration_seconds or 0)


def _full_simulation_active(ctx: TaskContext) -> bool:
    _sync_full_sim_state_from_ctx(ctx)
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


def _simulate_answer_duration_delay(
    ctx: TaskContext,
    stop_signal: Optional[threading.Event] = None,
) -> bool:
    """委托到模块实现，从 ctx 获取配置范围。"""
    return duration_control.simulate_answer_duration_delay(
        stop_signal, ctx.answer_duration_range_seconds
    )
