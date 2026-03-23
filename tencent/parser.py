"""腾讯问卷解析与标准化。"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Tuple

from software.core.survey.parser import _normalize_html_text
from software.core.providers.common import SURVEY_PROVIDER_QQ
from software.network.browser import create_playwright_driver

QQ_SUPPORTED_PROVIDER_TYPES = {
    "radio",
    "checkbox",
    "select",
    "text",
    "textarea",
    "nps",
    "matrix_radio",
    "matrix_star",
}
QQ_PROVIDER_TYPE_TO_INTERNAL = {
    "radio": "3",
    "checkbox": "4",
    "select": "7",
    "text": "1",
    "textarea": "1",
    "nps": "5",
    "matrix_radio": "6",
    "matrix_star": "6",
}
_QQ_TITLE_SUFFIX_RE = re.compile(r"(?:[-|｜]\s*)?腾讯问卷.*$", re.IGNORECASE)
_QQ_URL_RE = re.compile(r"/s\d+/(\d+)/([A-Za-z0-9_-]+)/?$", re.IGNORECASE)


def _extract_qq_identifiers(url: str) -> Tuple[str, str]:
    text = str(url or "").strip()
    match = _QQ_URL_RE.search(text)
    if not match:
        raise RuntimeError("腾讯问卷链接格式无效，请确认链接完整且公开可访问")
    return str(match.group(1) or "").strip(), str(match.group(2) or "").strip()


def _normalize_qq_title(raw_title: Any) -> str:
    title = _normalize_html_text(str(raw_title or ""))
    if not title:
        return ""
    title = _QQ_TITLE_SUFFIX_RE.sub("", title).strip(" -_|")
    return title or _normalize_html_text(str(raw_title or ""))


def _build_option_texts(question: Dict[str, Any], provider_type: str) -> List[str]:
    if provider_type == "nps":
        start = int(question.get("star_begin_num") or 0)
        count = max(0, int(question.get("star_num") or 0))
        return [str(start + idx) for idx in range(count)]
    if provider_type == "matrix_star":
        count = max(0, int(question.get("star_num") or 0))
        return [str(idx + 1) for idx in range(count)]
    raw_options = question.get("options")
    if not isinstance(raw_options, list):
        return []
    option_texts: List[str] = []
    for item in raw_options:
        text = _normalize_html_text(str((item or {}).get("text") or ""))
        option_texts.append(text)
    return option_texts


def _build_row_texts(question: Dict[str, Any]) -> List[str]:
    raw_sub_titles = question.get("sub_titles")
    if not isinstance(raw_sub_titles, list):
        return []
    row_texts: List[str] = []
    for item in raw_sub_titles:
        text = _normalize_html_text(str((item or {}).get("text") or ""))
        if text:
            row_texts.append(text)
    return row_texts


def _resolve_option_count(question: Dict[str, Any], provider_type: str, option_texts: List[str]) -> int:
    if provider_type == "nps":
        return max(len(option_texts), int(question.get("star_num") or 0))
    if provider_type == "matrix_star":
        return max(len(option_texts), int(question.get("star_num") or 0))
    if option_texts:
        return len(option_texts)
    raw_options = question.get("options")
    if isinstance(raw_options, list):
        return len(raw_options)
    return 0


def _build_page_number_map(questions: List[Dict[str, Any]]) -> Dict[Tuple[str, str], int]:
    page_map: Dict[Tuple[str, str], int] = {}
    next_page = 1
    for question in questions:
        page_id = str(question.get("page_id") or "").strip()
        page_raw = str(question.get("page") or "").strip()
        key = (page_id, page_raw)
        if key in page_map:
            continue
        page_map[key] = next_page
        next_page += 1
    return page_map


def _standardize_qq_questions(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    page_map = _build_page_number_map(questions)
    normalized: List[Dict[str, Any]] = []
    for idx, question in enumerate(questions, start=1):
        provider_type = str(question.get("type") or "").strip()
        title = _normalize_html_text(str(question.get("title") or ""))
        description = _normalize_html_text(str(question.get("description") or ""))
        page_id = str(question.get("page_id") or "").strip()
        page_raw = question.get("page")
        page = page_map.get((page_id, str(page_raw or "").strip()), 1)
        row_texts = _build_row_texts(question)
        option_texts = _build_option_texts(question, provider_type)
        option_count = _resolve_option_count(question, provider_type, option_texts)
        type_code = QQ_PROVIDER_TYPE_TO_INTERNAL.get(provider_type, "0")
        supported = provider_type in QQ_SUPPORTED_PROVIDER_TYPES
        unsupported_reason = "" if supported else f"暂不支持腾讯题型：{provider_type or 'unknown'}"
        is_text_like = provider_type in {"text", "textarea"}
        is_rating = provider_type == "nps"
        multi_min_limit = question.get("min_length") if provider_type == "checkbox" else None
        multi_max_limit = question.get("max_length") if provider_type == "checkbox" else None
        normalized.append({
            "num": idx,
            "title": title,
            "description": description,
            "type_code": type_code,
            "options": option_count,
            "rows": len(row_texts) if row_texts else 1,
            "row_texts": row_texts,
            "page": page,
            "option_texts": option_texts,
            "forced_option_index": None,
            "forced_option_text": "",
            "fillable_options": [],
            "attached_option_selects": [],
            "has_attached_option_select": False,
            "is_location": False,
            "is_rating": is_rating,
            "is_description": False,
            "rating_max": option_count if is_rating else 0,
            "text_inputs": 1 if is_text_like else 0,
            "text_input_labels": [],
            "is_multi_text": False,
            "is_text_like": is_text_like,
            "has_jump": False,
            "jump_rules": [],
            "slider_min": None,
            "slider_max": None,
            "slider_step": None,
            "multi_min_limit": multi_min_limit,
            "multi_max_limit": multi_max_limit,
            "provider": SURVEY_PROVIDER_QQ,
            "provider_question_id": str(question.get("id") or "").strip(),
            "provider_page_id": page_id,
            "provider_type": provider_type,
            "provider_page_raw": page_raw,
            "unsupported": not supported,
            "unsupported_reason": unsupported_reason,
            "required": bool(question.get("required", False)),
        })
    return normalized


def parse_qq_survey(url: str) -> Tuple[List[Dict[str, Any]], str]:
    survey_id, hash_value = _extract_qq_identifiers(url)
    driver = None
    try:
        driver, _ = create_playwright_driver(
            headless=True,
            user_agent=None,
            persistent_browser=False,
            transient_launch=True,
        )
        driver.get(url)
        page = getattr(driver, "page", None)
        if page is None:
            raise RuntimeError("当前浏览器驱动不支持腾讯问卷解析")
        try:
            page.wait_for_selector("main, .question-list, .page-control", state="visible", timeout=12000)
        except Exception:
            time.sleep(2.0)
        payload = page.evaluate(
            """async ({ surveyId, hashValue }) => {
                const requestUrl = `https://wj.qq.com/api/v2/respondent/surveys/${surveyId}/questions?_=${Date.now()}&hash=${encodeURIComponent(hashValue)}&locale=zhs`;
                const response = await fetch(requestUrl, { credentials: 'include' });
                const json = await response.json();
                return {
                    status: response.status,
                    ok: response.ok,
                    payload: json,
                    title: document.title || ''
                };
            }""",
            {"surveyId": survey_id, "hashValue": hash_value},
        ) or {}
        if not bool(payload.get("ok")):
            raise RuntimeError(f"腾讯问卷题目接口请求失败（HTTP {payload.get('status') or 'unknown'}）")
        outer_payload = payload.get("payload") or {}
        if str(outer_payload.get("code") or "").upper() not in {"OK", "0"}:
            raise RuntimeError(f"腾讯问卷接口返回异常：{outer_payload.get('code') or 'unknown'}")
        questions_payload = (outer_payload.get("data") or {}).get("questions")
        if not isinstance(questions_payload, list) or not questions_payload:
            raise RuntimeError("腾讯问卷题目接口未返回可解析的题目数据")
        title = _normalize_qq_title(payload.get("title") or driver.title or "")
        info = _standardize_qq_questions(questions_payload)
        if not info:
            raise RuntimeError("腾讯问卷解析结果为空，请确认链接有效且公开可访问")
        return info, title
    except Exception:
        logging.exception("解析腾讯问卷失败，url=%r", url)
        raise
    finally:
        try:
            if driver:
                driver.quit()
        except Exception:
            logging.info("关闭腾讯问卷解析浏览器失败", exc_info=True)


__all__ = [
    "QQ_SUPPORTED_PROVIDER_TYPES",
    "QQ_PROVIDER_TYPE_TO_INTERNAL",
    "parse_qq_survey",
]


