"""
多选题索引诊断工具

用途：在问卷开始前，检测可能导致多选题索引错位的问题
"""
import logging
from typing import List

from wjx.network.browser_driver import By, BrowserDriver, NoSuchElementException


def diagnose_multiple_choice_questions(driver: BrowserDriver, expected_count: int, question_nums: List[int]) -> None:
    """
    诊断多选题识别问题
    
    Args:
        driver: 浏览器驱动
        expected_count: 期望的多选题数量（从配置文件加载）
        question_nums: 配置中所有多选题的题号列表
    """
    if not question_nums:
        return
    
    logging.info(f"[诊断] 开始检查 {expected_count} 个多选题的识别情况")
    
    detected_multiple_questions = []
    missing_questions = []
    type_mismatches = []
    
    for qnum in question_nums:
        try:
            question_div = driver.find_element(By.CSS_SELECTOR, f"#div{qnum}")
            
            # 检查可见性
            if not question_div.is_displayed():
                missing_questions.append((qnum, "不可见"))
                logging.warning(f"[诊断] 第{qnum}题（多选题）在页面上不可见，可能导致索引错位")
                continue
            
            # 检查type属性
            question_type = question_div.get_attribute("type")
            if question_type != "4":
                type_mismatches.append((qnum, question_type))
                logging.warning(
                    f"[诊断] 第{qnum}题配置为多选题，但页面type='{question_type}'（不是'4'），"
                    f"会导致后续多选题索引错位"
                )
            else:
                detected_multiple_questions.append(qnum)
                
        except NoSuchElementException:
            missing_questions.append((qnum, "元素不存在"))
            logging.warning(f"[诊断] 第{qnum}题（多选题）在页面上找不到，可能导致索引错位")
        except Exception as e:
            logging.debug(f"[诊断] 检查第{qnum}题时出错: {e}")
    
    # 输出诊断摘要
    if type_mismatches or missing_questions:
        logging.warning(
            f"[诊断结果] 发现 {len(type_mismatches)} 个type不匹配，{len(missing_questions)} 个缺失/不可见题目。"
            f"这会导致后续多选题使用错误的配置索引！"
        )
        if type_mismatches:
            logging.warning(f"[诊断详情] type不匹配的题目: {type_mismatches}")
        if missing_questions:
            logging.warning(f"[诊断详情] 缺失/不可见的题目: {missing_questions}")
    else:
        logging.info(f"[诊断结果] 所有 {len(detected_multiple_questions)} 个多选题识别正常 ✓")


def get_multiple_choice_question_nums_from_config(question_entries) -> List[int]:
    """从配置中提取所有多选题的题号"""
    return [
        entry.question_num 
        for entry in question_entries 
        if entry.question_type == "multiple" and entry.question_num is not None
    ]
