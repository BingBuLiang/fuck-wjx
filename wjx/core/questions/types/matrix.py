"""矩阵题处理"""
import logging
from typing import Any, List, Optional, Union

from wjx.network.browser import By, BrowserDriver
from wjx.core.questions.tendency import get_tendency_index
from wjx.core.persona.context import record_answer
from wjx.core.questions.consistency import apply_matrix_row_consistency


def matrix(
    driver: BrowserDriver,
    current: int,
    index: int,
    matrix_prob_config: List,
    dimension: Optional[str] = None,
    is_reverse: Union[bool, List[bool]] = False,
    psycho_plan: Optional[Any] = None,
    question_index: Optional[int] = None,
) -> int:
    """矩阵题处理主函数，返回更新后的索引。

    is_reverse 可以是：
    - bool：所有行统一翻转
    - List[bool]：每行独立控制，长度不足时末尾行回退到 False
    """
    rows_xpath = f'//*[@id="divRefTab{current}"]/tbody/tr'
    row_elements = driver.find_elements(By.XPATH, rows_xpath)
    matrix_row_count = sum(1 for row in row_elements if row.get_attribute("rowindex") is not None)

    columns_xpath = f'//*[@id="drv{current}_1"]/td'
    column_elements = driver.find_elements(By.XPATH, columns_xpath)
    if len(column_elements) <= 1:
        return index
    candidate_columns = list(range(2, len(column_elements) + 1))
    
    logging.info(f"矩阵题 Q{current}: 网页列数={len(column_elements)}, 候选列={len(candidate_columns)}")

    for row_index in range(1, matrix_row_count + 1):
        raw_probabilities = matrix_prob_config[index] if index < len(matrix_prob_config) else -1
        index += 1
        probabilities = raw_probabilities
        
        # 调试日志：记录原始概率配置
        logging.info(f"矩阵题 Q{current} 行{row_index}: 原始概率={raw_probabilities}, dimension={dimension}")

        # 取当前行的反向标记
        if isinstance(is_reverse, list):
            row_is_reverse = is_reverse[row_index - 1] if row_index - 1 < len(is_reverse) else False
        else:
            row_is_reverse = bool(is_reverse)

        if isinstance(probabilities, list):
            try:
                probs = [float(value) for value in probabilities]
            except Exception:
                probs = []
            logging.info(f"矩阵题 Q{current} 行{row_index}: 转换后概率长度={len(probs)}, 候选列长度={len(candidate_columns)}")
            if len(probs) != len(candidate_columns):
                logging.warning(f"矩阵题 Q{current} 行{row_index}: 概率长度不匹配！调整概率列表")
                # 长度不匹配时，智能调整概率列表
                if len(probs) > len(candidate_columns):
                    # 概率列表太长，需要截取
                    # 策略：去掉前面多余的元素（通常是0权重的选项）
                    excess = len(probs) - len(candidate_columns)
                    probs = probs[excess:]
                else:
                    # 概率列表太短，用 0 填充
                    probs = probs + [0.0] * (len(candidate_columns) - len(probs))
                logging.info(f"矩阵题 Q{current} 行{row_index}: 调整后概率={probs}")
            probs = apply_matrix_row_consistency(probs, current, row_index - 1)
            selected_column = candidate_columns[get_tendency_index(
                len(candidate_columns),
                probs,
                dimension=dimension,
                is_reverse=row_is_reverse,
                psycho_plan=psycho_plan,
                question_index=(question_index if question_index is not None else current),
                row_index=row_index - 1,
            )]
        else:
            uniform_probs = apply_matrix_row_consistency([1.0] * len(candidate_columns), current, row_index - 1)
            if any(p > 0 for p in uniform_probs):
                selected_column = candidate_columns[get_tendency_index(
                    len(candidate_columns),
                    uniform_probs,
                    dimension=dimension,
                    is_reverse=row_is_reverse,
                    psycho_plan=psycho_plan,
                    question_index=(question_index if question_index is not None else current),
                    row_index=row_index - 1,
                )]
            else:
                selected_column = candidate_columns[get_tendency_index(
                    len(candidate_columns),
                    -1,
                    dimension=dimension,
                    is_reverse=row_is_reverse,
                    psycho_plan=psycho_plan,
                    question_index=(question_index if question_index is not None else current),
                    row_index=row_index - 1,
                )]
        driver.find_element(
            By.CSS_SELECTOR, f"#drv{current}_{row_index} > td:nth-child({selected_column})"
        ).click()
        # 记录统计数据：行索引 (0-based)，列索引 (0-based，减去表头偏移)
        record_answer(current, "matrix", selected_indices=[selected_column - 2], row_index=row_index - 1)
    return index

