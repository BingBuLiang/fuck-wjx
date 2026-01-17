# -*- coding: utf-8 -*-
"""AI 服务模块 - 支持多种 AI API 调用"""
import json
import requests
from typing import Optional, Dict, Any
from PySide6.QtCore import QSettings

# AI 服务提供商配置
AI_PROVIDERS = {
    "openai": {
        "label": "ChatGPT",
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
    },
    "gemini": {
        "label": "Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "models": ["gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b"],
        "default_model": "gemini-2.0-flash-exp",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
    },
    "qwen": {
        "label": "通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen3-max", "qwen-flash", "qwen-plus", "qwen-turbo", "qwen-turbo-latest"],
        "default_model": "qwen-flash",
    },
    "custom": {
        "label": "自定义 (OpenAI 兼容)",
        "base_url": "",
        "models": [],
        "default_model": "",
    },
}

DEFAULT_SYSTEM_PROMPT = "你是一个问卷填写助手。请根据问题简短回答，答案要自然、合理，不要太长。"


def get_ai_settings() -> Dict[str, Any]:
    """获取 AI 配置"""
    settings = QSettings("FuckWjx", "Settings")
    return {
        "enabled": settings.value("ai_enabled", False, type=bool),
        "provider": settings.value("ai_provider", "openai", type=str),
        "api_key": settings.value("ai_api_key", "", type=str),
        "base_url": settings.value("ai_base_url", "", type=str),
        "model": settings.value("ai_model", "", type=str),
        "system_prompt": settings.value("ai_system_prompt", DEFAULT_SYSTEM_PROMPT, type=str),
    }


def save_ai_settings(
    enabled: Optional[bool] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
):
    """保存 AI 配置"""
    settings = QSettings("FuckWjx", "Settings")
    if enabled is not None:
        settings.setValue("ai_enabled", enabled)
    if provider is not None:
        settings.setValue("ai_provider", provider)
    if api_key is not None:
        settings.setValue("ai_api_key", api_key)
    if base_url is not None:
        settings.setValue("ai_base_url", base_url)
    if model is not None:
        settings.setValue("ai_model", model)
    if system_prompt is not None:
        settings.setValue("ai_system_prompt", system_prompt)


def _call_openai_compatible(
    base_url: str,
    api_key: str,
    model: str,
    question: str,
    system_prompt: str,
    timeout: int = 30,
) -> Optional[str]:
    """调用 OpenAI 兼容接口"""
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请简短回答这个问卷问题：{question}"},
        ],
        "max_tokens": 200,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        raise RuntimeError(f"API 调用失败: {e}")


def _call_gemini(
    api_key: str,
    model: str,
    question: str,
    system_prompt: str,
    timeout: int = 30,
) -> Optional[str]:
    """调用 Google Gemini API"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\n\n请简短回答这个问卷问题：{question}"}
                ]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 200,
            "temperature": 0.7,
        },
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        raise RuntimeError(f"Gemini API 调用失败: {e}")


def generate_answer(question_title: str) -> str:
    """根据问题标题生成答案"""
    config = get_ai_settings()
    if not config["enabled"]:
        raise RuntimeError("AI 功能未启用")
    if not config["api_key"]:
        raise RuntimeError("请先配置 API Key")

    provider = config["provider"]
    api_key = config["api_key"]
    system_prompt = config["system_prompt"] or DEFAULT_SYSTEM_PROMPT

    # 确定 base_url 和 model
    if provider == "custom":
        base_url = config["base_url"]
        model = config["model"]
        if not base_url:
            raise RuntimeError("自定义模式需要配置 Base URL")
        if not model:
            raise RuntimeError("自定义模式需要配置模型名称")
    elif provider == "gemini":
        model = config["model"] or AI_PROVIDERS["gemini"]["default_model"]
        return _call_gemini(api_key, model, question_title, system_prompt)
    else:
        provider_config = AI_PROVIDERS.get(provider, AI_PROVIDERS["openai"])
        base_url = provider_config["base_url"]
        model = config["model"] or provider_config["default_model"]

    return _call_openai_compatible(base_url, api_key, model, question_title, system_prompt)


def test_connection() -> str:
    """测试 AI 连接"""
    try:
        result = generate_answer("这是一个测试问题，请回复'连接成功'")
        return f"连接成功！AI 回复: {result[:50]}..."
    except Exception as e:
        return f"连接失败: {e}"
