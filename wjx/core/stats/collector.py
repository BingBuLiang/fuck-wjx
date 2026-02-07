"""线程安全的统计数据收集器（单例模式）"""

import copy
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any

from wjx.core.stats.models import SurveyStats


# ── 暂存缓冲区类型定义 ──────────────────────────────────────
# question_num -> [(action_type, *args)]
# action_type: "single" | "multiple" | "matrix" | "scale" | "dropdown" | "slider" | "text"
_PendingAction = tuple  # 动作元组：(类型字符串, 其他参数...)
_PendingBuffer = Dict[int, List[_PendingAction]]


class StatsCollector:
    """线程安全的统计数据收集器（单例模式）
    
    设计：每轮作答先记录到 buffer，只有提交成功才合并到主统计。
    避免因提交失败导致题目统计与提交次数不一致。
    """

    _instance: Optional["StatsCollector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "StatsCollector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._data_lock = threading.Lock()
        self._current_stats: Optional[SurveyStats] = None
        self._pending_buffer: _PendingBuffer = {}  # 当前轮次暂存
        self._enabled = False
        self._initialized = True

    def start_session(self, survey_url: str, survey_title: Optional[str] = None) -> None:
        """开始新的统计会话"""
        with self._data_lock:
            self._current_stats = SurveyStats(
                survey_url=survey_url,
                survey_title=survey_title
            )
            self._pending_buffer = {}
            self._enabled = True

    def end_session(self) -> None:
        """结束当前会话"""
        with self._data_lock:
            self._enabled = False
            self._pending_buffer = {}

    def start_round(self) -> None:
        """开始新的作答轮次（清空暂存缓冲区）"""
        with self._data_lock:
            self._pending_buffer = {}

    def commit_round(self) -> None:
        """提交成功：将暂存缓冲区的统计合并到主统计"""
        with self._data_lock:
            if not self._current_stats or not self._pending_buffer:
                return
            
            # 逐题应用缓冲区中的操作
            for q_num, actions in self._pending_buffer.items():
                for action in actions:
                    action_type = action[0]
                    if action_type == "single":
                        q = self._current_stats.get_or_create_question(q_num, "single")
                        q.record_selection(action[1])
                    elif action_type == "multiple":
                        q = self._current_stats.get_or_create_question(q_num, "multiple")
                        for idx in action[1]:
                            q.record_selection(idx)
                    elif action_type == "matrix":
                        q = self._current_stats.get_or_create_question(q_num, "matrix")
                        q.record_matrix_selection(action[1], action[2])
                    elif action_type == "scale":
                        q = self._current_stats.get_or_create_question(q_num, "scale")
                        q.record_selection(action[1])
                    elif action_type == "dropdown":
                        q = self._current_stats.get_or_create_question(q_num, "dropdown")
                        q.record_selection(action[1])
                    elif action_type == "slider":
                        q = self._current_stats.get_or_create_question(q_num, "slider")
                        q.record_selection(action[1])
                    elif action_type == "text":
                        q = self._current_stats.get_or_create_question(q_num, "text")
                        q.record_text_answer(action[1])
            
            # 记录提交成功
            self._current_stats.total_submissions += 1
            self._current_stats.updated_at = datetime.now().isoformat()
            
            # 清空缓冲区
            self._pending_buffer = {}

    def discard_round(self) -> None:
        """提交失败：丢弃暂存缓冲区"""
        with self._data_lock:
            self._pending_buffer = {}
            # 记录失败
            if self._current_stats:
                self._current_stats.failed_submissions += 1
                self._current_stats.updated_at = datetime.now().isoformat()

    # ── 题目作答记录（写入暂存缓冲区） ────────────────────────

    def record_single_choice(self, question_num: int, selected_index: int) -> None:
        """记录单选题选择（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("single", selected_index))

    def record_multiple_choice(self, question_num: int, selected_indices: List[int]) -> None:
        """记录多选题选择（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("multiple", tuple(selected_indices)))

    def record_matrix_choice(self, question_num: int, row_index: int, col_index: int) -> None:
        """记录矩阵题选择（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("matrix", row_index, col_index))

    def record_scale_choice(self, question_num: int, selected_index: int) -> None:
        """记录量表题选择（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("scale", selected_index))

    def record_dropdown_choice(self, question_num: int, selected_index: int) -> None:
        """记录下拉题选择（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("dropdown", selected_index))

    def record_slider_choice(self, question_num: int, selected_index: int) -> None:
        """记录滑块题选择（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("slider", selected_index))

    def record_text_answer(self, question_num: int, text: str) -> None:
        """记录填空题答案（暂存）"""
        with self._data_lock:
            if not self._enabled:
                return
            if question_num not in self._pending_buffer:
                self._pending_buffer[question_num] = []
            self._pending_buffer[question_num].append(("text", text))

    # ── 旧接口兼容（已废弃，请使用 commit_round/discard_round） ──

    def record_submission_success(self) -> None:
        """【已废弃】记录成功提交（请改用 commit_round）"""
        self.commit_round()

    def record_submission_failure(self) -> None:
        """【已废弃】记录提交失败（请改用 discard_round）"""
        self.discard_round()

    # ── 其他接口 ──────────────────────────────────────────────

    def get_current_stats(self) -> Optional[SurveyStats]:
        """获取当前统计数据（只读副本）"""
        with self._data_lock:
            if self._current_stats is None:
                return None
            # 返回深拷贝避免外部修改
            return copy.deepcopy(self._current_stats)

    def is_enabled(self) -> bool:
        """检查统计是否启用"""
        with self._data_lock:
            return self._enabled

    def reset(self) -> None:
        """重置统计数据"""
        with self._data_lock:
            self._current_stats = None
            self._pending_buffer = {}
            self._enabled = False


# 全局单例
stats_collector = StatsCollector()
