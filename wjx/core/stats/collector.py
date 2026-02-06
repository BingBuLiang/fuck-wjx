"""线程安全的统计数据收集器（单例模式）"""

import copy
import threading
from datetime import datetime
from typing import List, Optional

from wjx.core.stats.models import SurveyStats


class StatsCollector:
    """线程安全的统计数据收集器（单例模式）"""

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
        self._enabled = False
        self._initialized = True

    def start_session(self, survey_url: str, survey_title: Optional[str] = None) -> None:
        """开始新的统计会话"""
        with self._data_lock:
            self._current_stats = SurveyStats(
                survey_url=survey_url,
                survey_title=survey_title
            )
            self._enabled = True

    def end_session(self) -> None:
        """结束当前会话"""
        with self._data_lock:
            self._enabled = False

    def record_single_choice(self, question_num: int, selected_index: int) -> None:
        """记录单选题选择"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "single")
            q.record_selection(selected_index)

    def record_multiple_choice(self, question_num: int, selected_indices: List[int]) -> None:
        """记录多选题选择"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "multiple")
            for idx in selected_indices:
                q.record_selection(idx)

    def record_matrix_choice(self, question_num: int, row_index: int, col_index: int) -> None:
        """记录矩阵题选择"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "matrix")
            q.record_matrix_selection(row_index, col_index)

    def record_scale_choice(self, question_num: int, selected_index: int) -> None:
        """记录量表题选择"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "scale")
            q.record_selection(selected_index)

    def record_dropdown_choice(self, question_num: int, selected_index: int) -> None:
        """记录下拉题选择"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "dropdown")
            q.record_selection(selected_index)

    def record_slider_choice(self, question_num: int, selected_index: int) -> None:
        """记录滑块题选择"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "slider")
            q.record_selection(selected_index)

    def record_text_answer(self, question_num: int, text: str) -> None:
        """记录填空题答案"""
        with self._data_lock:
            if not self._enabled or self._current_stats is None:
                return
            q = self._current_stats.get_or_create_question(question_num, "text")
            q.record_text_answer(text)

    def record_submission_success(self) -> None:
        """记录成功提交"""
        with self._data_lock:
            if self._current_stats:
                self._current_stats.total_submissions += 1
                self._current_stats.updated_at = datetime.now().isoformat()

    def record_submission_failure(self) -> None:
        """记录提交失败"""
        with self._data_lock:
            if self._current_stats:
                self._current_stats.failed_submissions += 1
                self._current_stats.updated_at = datetime.now().isoformat()

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
            self._enabled = False


# 全局单例
stats_collector = StatsCollector()
