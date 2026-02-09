"""答题倾向模块 - 保证同一份问卷内量表类题目的前后一致性

问题：原来每道量表题完全独立随机，可能出现前面给5分后面给1分的情况，
导致 Cronbach's Alpha 信效度极低，一看就是假数据。

方案：每次填写问卷时，先生成一个"基准偏好"（倾向于选高分/中分/低分），
之后所有量表类题目都围绕这个基准 ±1 波动，模拟真人的答题一致性。
"""
import random
import threading
from typing import List, Optional, Union

from wjx.core.questions.utils import weighted_index

# 线程局部存储：每个浏览器线程有自己独立的答题倾向
_thread_local = threading.local()

# 波动范围（基准 ±1）
_FLUCTUATION = 1


def reset_tendency() -> None:
    """在每份问卷开始填写前调用，清除上一份的答题倾向。

    这样每份问卷会重新生成倾向，不同问卷之间仍然是随机的。
    """
    _thread_local.base_index = None


def _generate_base_index(option_count: int, probabilities: Union[List[float], int, None]) -> int:
    """根据概率配置生成本份问卷的基准偏好索引。

    如果有概率配置，按概率选择基准；否则完全随机。
    """
    if probabilities == -1 or probabilities is None:
        return random.randrange(option_count)
    if isinstance(probabilities, list) and probabilities:
        return weighted_index(probabilities)
    return random.randrange(option_count)


def get_tendency_index(option_count: int, probabilities: Union[List[float], int, None]) -> int:
    """获取带有一致性倾向的选项索引。

    第一次调用时会生成基准偏好，之后每次调用都在基准附近 ±1 波动。
    这样同一份问卷内的量表类答案会保持逻辑一致性。

    Args:
        option_count: 该题的选项数量（比如5分量表就是5）
        probabilities: 概率配置列表，或 -1 表示随机

    Returns:
        选中的选项索引（0-based）
    """
    if option_count <= 0:
        return 0

    base = getattr(_thread_local, 'base_index', None)

    if base is None:
        # 首次调用：生成基准偏好
        base = _generate_base_index(option_count, probabilities)
        _thread_local.base_index = base

    # 当前题目选项数可能与生成 base 时不同，需要夹到合法范围
    effective_base = min(base, option_count - 1)

    # 在基准附近 ±1 波动
    low = max(0, effective_base - _FLUCTUATION)
    high = min(option_count - 1, effective_base + _FLUCTUATION)

    # 在 [low, high] 范围内随机选一个，但偏向基准值
    candidates = list(range(low, high + 1))
    # 给基准值更高的权重（2倍），让结果更集中
    weights = []
    for c in candidates:
        if c == effective_base:
            weights.append(2.0)
        else:
            weights.append(1.0)

    # 加权随机选择
    total = sum(weights)
    pivot = random.random() * total
    running = 0.0
    for i, w in enumerate(weights):
        running += w
        if pivot <= running:
            return candidates[i]
    return candidates[-1]
