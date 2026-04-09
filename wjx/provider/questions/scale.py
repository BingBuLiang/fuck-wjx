"""量表题处理"""
import logging
from typing import Any, List, Optional

from software.network.browser import By, BrowserDriver
from software.core.persona.context import record_answer
from software.core.questions.distribution import (
    record_pending_distribution_choice,
    resolve_distribution_probabilities,
)
from software.core.questions.tendency import get_tendency_index
from software.core.questions.consistency import apply_single_like_consistency
from software.core.questions.utils import normalize_droplist_probs
from software.logging.log_utils import log_suppressed_exception


def _collect_scale_options(question_div) -> List:
    """收集量表选项，兼容带说明文案（qinsert）的十级量表 DOM。"""
    selectors = (
        ".scale-rating ul li",
        "ul[tp='d'] li",
        "ul[class*='modlen'] li",
        ".scale-div ul li",
    )
    for selector in selectors:
        try:
            options = question_div.find_elements(By.CSS_SELECTOR, selector)
        except Exception:
            options = []
        if options:
            return options
    return []


def scale(
    driver: BrowserDriver,
    current: int,
    index: int,
    scale_prob_config: List,
    dimension: Optional[str] = None,
    psycho_plan: Optional[Any] = None,
    question_index: Optional[int] = None,
    task_ctx: Optional[Any] = None,
) -> None:
    """量表题处理主函数"""
    try:
        question_div = driver.find_element(By.CSS_SELECTOR, f"#div{current}")
    except Exception:
        question_div = None
    if question_div is None:
        return

    scale_options = _collect_scale_options(question_div)
    if not scale_options:
        # 兼容旧问卷结构：当 CSS 方案都未命中时，再走历史 XPath。
        scale_items_xpath = f'//*[@id="div{current}"]/div[2]/div/ul/li'
        scale_options = driver.find_elements(By.XPATH, scale_items_xpath)

    probabilities = scale_prob_config[index] if index < len(scale_prob_config) else -1
    if not scale_options:
        return
    probs = normalize_droplist_probs(probabilities, len(scale_options))
    probs = apply_single_like_consistency(probs, current)
    resolved_question_index = question_index if question_index is not None else current
    probs = resolve_distribution_probabilities(
        probs,
        len(scale_options),
        task_ctx,
        resolved_question_index,
        psycho_plan=psycho_plan,
        priority_mode=getattr(task_ctx, "reliability_priority_mode", None),
    )
    
    selected_index = get_tendency_index(
        len(scale_options),
        probs,
        dimension=dimension,
        psycho_plan=psycho_plan,
        question_index=resolved_question_index,
        priority_mode=getattr(task_ctx, "reliability_priority_mode", None),
    )
    if selected_index >= len(scale_options):
        selected_index = max(0, len(scale_options) - 1)
    target = scale_options[selected_index]
    try:
        target.click()
    except Exception:
        try:
            driver.execute_script("arguments[0].click();", target)
        except Exception as exc:
            log_suppressed_exception("scale: driver.execute_script(\"arguments[0].click();\", target)", exc, level=logging.ERROR)
    record_pending_distribution_choice(
        task_ctx,
        resolved_question_index,
        selected_index,
        len(scale_options),
    )
    # 记录作答上下文
    record_answer(current, "scale", selected_indices=[selected_index])


    # if strict_ratio:
    #     probs = enforce_reference_rank_order(probs, normalize_droplist_probs(probabilities, len(scale_options)))
    #     selected_index = weighted_index(probs)
    # else:
    #     selected_index = get_tendency_index(
    #         len(scale_options),
    #         probs,
    #         dimension=dimension,
    #         psycho_plan=psycho_plan,
    #         question_index=resolved_question_index,
    #         reliability_priority_mode=task_ctx.reliability_priority_mode if task_ctx else "ratio_first",
    #     )
    
    # ── S3 新增：记录信效度答案到缓冲区 ──
    # 只有设置了维度才记录
    if task_ctx is not None and dimension:
        task_ctx.record_psycho_answer(dimension, (resolved_question_index, None), selected_index)
    
    # scale_options[selected_index].click()


