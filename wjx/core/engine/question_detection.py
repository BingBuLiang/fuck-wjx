import threading
from typing import List, Optional

from wjx.core.engine.navigation import dismiss_resume_dialog_if_present, try_click_start_answer_button
from wjx.network.browser_driver import By, BrowserDriver


def detect(driver: BrowserDriver, stop_signal: Optional[threading.Event] = None) -> List[int]:
    dismiss_resume_dialog_if_present(driver, stop_signal=stop_signal)
    try_click_start_answer_button(driver, stop_signal=stop_signal)
    question_counts_per_page: List[int] = []
    total_pages = len(driver.find_elements(By.XPATH, '//*[@id="divQuestion"]/fieldset'))
    for page_index in range(1, total_pages + 1):
        page_questions = driver.find_elements(By.XPATH, f'//*[@id="fieldset{page_index}"]/div')
        valid_question_count = 0
        for question_element in page_questions:
            topic_attr = question_element.get_attribute("topic")
            if topic_attr and topic_attr.isdigit():
                valid_question_count += 1
        question_counts_per_page.append(valid_question_count)
    return question_counts_per_page
