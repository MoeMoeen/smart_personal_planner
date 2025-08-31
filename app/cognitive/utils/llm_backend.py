# app/cognitive/utils/llm_backend.py
import os
from typing import Optional, Dict, Any, List, TypedDict
from dataclasses import dataclass
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

class ChatMessage(TypedDict):
    role: str
    content: str

@dataclass
class LLMResponse:
    content: str
    token_usage: Optional[Dict[str, Any]] = None
    cost: Optional[float] = None
    raw: Optional[Any] = None

class LLMBackend:
    def chat(self, messages: List[ChatMessage], model: Optional[str] = None, **kwargs) -> LLMResponse:
        raise NotImplementedError

class OpenAIBackend(LLMBackend):
    def chat(self, messages: List[ChatMessage], model: Optional[str] = None, **kwargs) -> LLMResponse:
        client = OpenAI()
        # Ensure model is always a string and not None
        model_name = model or os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-3.5-turbo")
        # Convert messages to the expected OpenAI format (ChatCompletionMessageParam)
        openai_messages: List[ChatCompletionMessageParam] = [
            {"role": msg["role"], "content": msg["content"]}  # type: ignore
            for msg in messages
        ]
        resp = client.chat.completions.create(model=model_name, messages=openai_messages, **kwargs)
        content = getattr(resp.choices[0].message, "content", "") or ""
        usage = getattr(resp, "usage", None)

        # Cost calculation: inject via env or config; avoid hardcoding here.
        cost = None
        return LLMResponse(content=content.strip(), token_usage=dict(usage) if usage else None, cost=cost, raw=resp)

def get_llm_backend(name: Optional[str] = None) -> LLMBackend:
    backend = (name or os.environ.get("LLM_BACKEND", "openai")).lower()
    if backend == "openai":
        return OpenAIBackend()
    raise ValueError(f"Unknown LLM backend: {backend}")
