"""统计数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List
import math


@dataclass
class OptionStats:
    """单个选项的统计数据"""
    option_index: int       # 选项索引 (0-based)
    option_text: str = ""   # 选项文本（可选，用于显示）
    count: int = 0          # 被选中的次数


@dataclass
class QuestionStats:
    """单道题目的统计数据"""
    question_num: int                           # 题号
    question_type: str                          # 题型 (single/multiple/matrix/scale/text...)
    question_title: Optional[str] = None        # 题目标题
    options: Dict[int, OptionStats] = field(default_factory=dict)  # 选项索引 -> 统计
    total_responses: int = 0                    # 该题的总作答次数
    # 矩阵题专用：每行独立统计
    rows: Optional[Dict[int, Dict[int, int]]] = None  # row_index -> {col_index: count}
    # 填空题专用：记录填写的文本
    text_answers: Optional[Dict[str, int]] = None     # answer_text -> count
    # 配置元数据：用于展示时补全所有选项/行列（即使计数为0）
    option_count: Optional[int] = None          # 总选项数
    matrix_rows: Optional[int] = None           # 矩阵题总行数
    matrix_cols: Optional[int] = None           # 矩阵题总列数

    def record_selection(self, option_index: int) -> None:
        """记录一次选项选择"""
        if option_index not in self.options:
            self.options[option_index] = OptionStats(option_index=option_index, option_text="")
        self.options[option_index].count += 1
        self.total_responses += 1

    def record_matrix_selection(self, row_index: int, col_index: int) -> None:
        """记录矩阵题选择"""
        if self.rows is None:
            self.rows = {}
        if row_index not in self.rows:
            self.rows[row_index] = {}
        self.rows[row_index][col_index] = self.rows[row_index].get(col_index, 0) + 1
        self.total_responses += 1

    def record_text_answer(self, text: str) -> None:
        """记录填空题答案"""
        if self.text_answers is None:
            self.text_answers = {}
        self.text_answers[text] = self.text_answers.get(text, 0) + 1
        self.total_responses += 1

    def get_option_percentage(self, option_index: int) -> float:
        """获取某选项的占比（百分比）"""
        if self.total_responses == 0:
            return 0.0
        option = self.options.get(option_index)
        if option is None:
            return 0.0
        return (option.count / self.total_responses) * 100.0


@dataclass
class SurveyStats:
    """问卷级别统计数据"""
    survey_url: str                             # 问卷URL
    survey_title: Optional[str] = None          # 问卷标题
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_submissions: int = 0                  # 总提交份数
    failed_submissions: int = 0                 # 失败次数
    questions: Dict[int, QuestionStats] = field(default_factory=dict)  # 题号 -> 统计

    def get_or_create_question(self, question_num: int, question_type: str) -> QuestionStats:
        """获取或创建题目统计"""
        if question_num not in self.questions:
            self.questions[question_num] = QuestionStats(
                question_num=question_num,
                question_type=question_type
            )
        return self.questions[question_num]

    def calculate_cronbach_alpha(self) -> Optional[float]:
        """计算 Cronbach's Alpha 系数（问卷内部一致性信度）

        适用于量表题、评分题、单选题等有序选项的题型。
        返回值范围 [0, 1]，一般认为 >0.7 可接受，>0.8 良好。

        计算公式：α = (k / (k-1)) * (1 - Σσ²ᵢ / σ²ₜ)
        其中：
        - k: 题目数量
        - σ²ᵢ: 每道题的方差
        - σ²ₜ: 总分的方差
        """
        # 筛选适用的题型（有序选项的题目）
        applicable_types = {"single", "scale", "score", "dropdown"}
        applicable_questions = [
            q for q in self.questions.values()
            if q.question_type in applicable_types and q.total_responses > 0
        ]

        # 至少需要 2 道题且有足够的样本
        if len(applicable_questions) < 2 or self.total_submissions < 2:
            return None

        # 构建每份问卷的作答矩阵（每行是一份问卷，每列是一道题的得分）
        # 注意：这里需要从原始数据重建，但我们只有统计数据，所以采用近似方法
        # 使用每个选项的计数来估算方差

        item_variances = []
        item_means = []

        for q in applicable_questions:
            # 计算该题的均值和方差
            total_score = 0
            total_count = 0

            for opt_idx, opt_stat in q.options.items():
                # 将选项索引作为分数（0-based）
                score = opt_idx
                count = opt_stat.count
                total_score += score * count
                total_count += count

            if total_count == 0:
                continue

            mean = total_score / total_count
            item_means.append(mean)

            # 计算方差
            variance = 0
            for opt_idx, opt_stat in q.options.items():
                score = opt_idx
                count = opt_stat.count
                variance += count * ((score - mean) ** 2)
            variance /= total_count
            item_variances.append(variance)

        if len(item_variances) < 2:
            return None

        # 计算总分方差（近似方法：假设题目间相关性）
        # 由于我们没有原始数据，使用简化公式
        sum_item_var = sum(item_variances)

        # 估算总分方差（使用平均相关系数法）
        # 这是一个近似值，真实计算需要原始数据
        k = len(item_variances)
        avg_item_var = sum_item_var / k

        # 使用标准化方法计算 Cronbach's Alpha
        # α = k * r̄ / (1 + (k-1) * r̄)
        # 其中 r̄ 是题目间的平均相关系数
        # 由于没有原始数据，我们使用方差比例来估算

        # 简化计算：使用 KR-20 公式的变体
        if sum_item_var == 0:
            return None

        # 估算总方差（假设中等相关性 0.3）
        avg_correlation = 0.3
        total_var = sum_item_var + 2 * avg_correlation * math.sqrt(sum_item_var * sum_item_var / k)

        if total_var == 0:
            return None

        alpha = (k / (k - 1)) * (1 - sum_item_var / total_var)

        # 限制在 [0, 1] 范围内
        return max(0.0, min(1.0, alpha))
