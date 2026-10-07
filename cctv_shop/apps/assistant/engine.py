"""
موتورهای LLM دستیار — زنجیرهٔ فالبک: موتور انتخاب‌شده در پنل، بعد بقیهٔ کلیددارها، آخر Qwen لوکال.
ask_llm رابط عمومی برای مصرف‌کننده‌های دیگر (مثل تولید محتوای اینستاگرام publisher) است.
"""

import logging
import os
import time

import requests

from .models import AssistantSettings

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://127.0.0.1:11434/api/chat"
MODEL = "qwen2.5:3b"
TIMEOUT = 140  # روی CPU نسل پاسخ کند است — باید زیر nginx/gunicorn (150s) بماند
CLOUD_TIMEOUT = 40  # سرویس‌های ابری (Gemini/z.ai/…) — رایگان‌ها گاهی تا ~۳۰ ثانیه طول می‌کشند


def _ask_ollama(messages: list, max_tokens: int = 170) -> str:
    resp = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": messages, "stream": False,
              "keep_alive": "30m",  # مدل در حافظه بماند — درخواست‌های بعدی سریع‌تر
              "options": {"num_predict": max_tokens, "temperature": 0.3}},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()["message"]["content"].strip()


def _ask_gemini(messages: list, api_key: str, model: str, proxy: str = "", max_tokens: int = 500) -> str:
    """فراخوانی Google Gemini (REST) — قالب چت OpenAI-like به فرمت Gemini تبدیل می‌شود.
    سرور ایران به گوگل دسترسی ندارد؛ مسیر پیش‌فرض از رله مینی‌پی‌سی است:
    GEMINI_BASE_URL (مثلاً http://127.0.0.1:3299 — تونل SSH به رله مینی‌پی‌سی چین)
    + GEMINI_RELAY_TOKEN (هدر X-Relay-Token). فیلد proxy همچنان forward-proxy است."""
    from decouple import config as env
    base = env("GEMINI_BASE_URL", default="https://generativelanguage.googleapis.com").rstrip("/")
    relay_token = env("GEMINI_RELAY_TOKEN", default="")
    headers = {"X-Relay-Token": relay_token} if relay_token else None
    system = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system += m["content"] + "\n"
        else:
            contents.append({
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            })
    resp = None
    for attempt in (1, 2):
        resp = requests.post(
            f"{base}/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            headers=headers,
            json={
                "system_instruction": {"parts": [{"text": system}]},
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": max_tokens, "temperature": 0.3,
                    # مدل thinking — بدون این استدلال داخلی بودجه/زمان را می‌بلعد
                    "thinkingConfig": {"thinkingBudget": 0},
                },
            },
            proxies={"http": proxy, "https": proxy} if proxy else None,
            timeout=CLOUD_TIMEOUT,
        )
        # ریت‌لیمیت لحظه‌ای گوگل — یک بار بعد از مکث کوتاه دوباره تلاش کن
        if resp.status_code not in (429, 500, 502, 503) or attempt == 2:
            break
        time.sleep(3)
    resp.raise_for_status()
    return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


# سرویس‌های ابری OpenAI-compatible — هر سه از ایران مستقیم در دسترس‌اند (بدون پروکسی)
OPENAI_COMPAT_PROVIDERS = {
    "modelscope": {"base_url": "https://api-inference.modelscope.cn/v1", "key_field": "ms_api_key", "model_field": "ms_model"},
    # حالت «فکر کردن» GLM پیش‌فرض روشن است و با کانتکست بزرگ فارسی تایم‌اوت می‌خورد — خاموشش می‌کنیم
    "zai":        {"base_url": "https://api.z.ai/api/paas/v4",           "key_field": "zai_api_key", "model_field": "zai_model",
                   "extra": {"thinking": {"type": "disabled"}},
                   "timeout": 20},  # ربات رایگان — اگر ۲۰ ثانیه جواب نداد سریع برو سراغ بعدی
    "deepseek":   {"base_url": "https://api.deepseek.com",               "key_field": "ds_api_key",  "model_field": "ds_model"},
}


def _ask_openai_compat(messages: list, base_url: str, api_key: str, model: str, extra: dict | None = None,
                       timeout: int = CLOUD_TIMEOUT, max_tokens: int = 500) -> str:
    """فراخوانی سرویس‌های OpenAI-compatible (ModelScope / z.ai / DeepSeek) — پیام‌ها همان قالب چت است."""
    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.3, **(extra or {})},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _engine_chain(st, max_tokens: int | None = None):
    """زنجیرهٔ موتورها به ترتیب اولویت: اول موتور انتخاب‌شده، بعد بقیهٔ کلیددارها، آخر Qwen لوکال.
    خروجی: لیست (نام موتور، تابع فراخوانی با ورودی messages).
    max_tokens=None یعنی پیش‌فرض هر موتور (رفتار قبلی چت‌بات)؛ با مقدار، به همه موتورها داده می‌شود."""
    kw = {"max_tokens": max_tokens} if max_tokens else {}
    chain = []
    gemini_key = st.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    gemini = ("gemini", lambda msgs: _ask_gemini(msgs, gemini_key, st.gemini_model, st.gemini_proxy, **kw))
    providers = {
        "gemini": gemini if (st.gemini_enabled and gemini_key) else None,
    }
    for name, cfg in OPENAI_COMPAT_PROVIDERS.items():
        key = getattr(st, cfg["key_field"])
        providers[name] = (
            (name, lambda msgs, c=cfg, k=key, m=getattr(st, cfg["model_field"]): _ask_openai_compat(msgs, c["base_url"], k, m, c.get("extra"), c.get("timeout", CLOUD_TIMEOUT), **kw))
            if key else None
        )
    ordered = [st.provider] + [p for p in ("gemini", "modelscope", "zai", "deepseek") if p != st.provider]
    for name in ordered:
        if providers.get(name):
            chain.append(providers[name])
    chain.append(("qwen", lambda msgs: _ask_ollama(msgs, **kw)))
    return chain


def ask_llm(messages: list, max_tokens: int = 2000) -> tuple[str, str]:
    """فراخوانی زنجیرهٔ موتورها با فالبک — خروجی: (متن پاسخ، نام موتور پاسخ‌دهنده).
    اگر همه موتورها خطا بدهند، آخرین استثنا بالا پرتاب می‌شود."""
    st = AssistantSettings.get_instance()
    last_exc = None
    for name, call in _engine_chain(st, max_tokens=max_tokens):
        try:
            return call(messages), name
        except Exception as exc:
            last_exc = exc
            logger.warning(f"[LLM] موتور {name} خطا داد — تلاش با موتور بعدی: {exc}")
    raise last_exc
