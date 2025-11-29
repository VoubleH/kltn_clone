# llm_client.py
import os
from typing import List, Dict, Any
from openai import OpenAI

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8001/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "dummy")  # vLLM thường không check key, nhưng vẫn cần chuỗi
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-sale-lora")

client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)


def call_llm_chat(messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
    """
    Gọi LLM (Qwen finetune) kiểu chat completion đơn giản.
    messages: [{role: "system"/"user"/"assistant", content: "..."}]
    """
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=temperature,
    )
    return resp.choices[0].message.content
