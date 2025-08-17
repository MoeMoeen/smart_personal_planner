# app/cognitive/utils/llm_backend.py
"""
Pluggable LLM backend abstraction for easy switching between OpenAI, Claude, local, etc.
Now supports returning token usage and cost info.
"""
import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from openai import OpenAI
# from anthropic import Anthropic  # Uncomment if using Claude
# from my_local_llm import LocalLLM  # Example for local LLM

@dataclass
class LLMResponse:
    content: str
    token_usage: Optional[Dict[str, Any]] = None
    cost: Optional[float] = None

class LLMBackend:
    def call(self, prompt: str) -> LLMResponse:
        raise NotImplementedError

class OpenAIBackend(LLMBackend):
    def call(self, prompt: str) -> LLMResponse:
        client = OpenAI()
        response = client.chat.completions.create(
            model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
            messages=[{"role": "system", "content": prompt}],
            max_tokens=256,
            temperature=0.0,
        )
        content = getattr(response.choices[0].message, 'content', None)
        usage = getattr(response, 'usage', None)
        # OpenAI usage: {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
        cost = None
        if usage:
            # Example cost calculation for gpt-3.5-turbo (adjust as needed)
            prompt_tokens = usage.get('prompt_tokens', 0)
            completion_tokens = usage.get('completion_tokens', 0)
            # $0.50 per 1M prompt tokens, $1.50 per 1M completion tokens (as of Aug 2025)
            cost = (prompt_tokens * 0.0005 + completion_tokens * 0.0015)
        return LLMResponse(
            content=content.strip() if content else "",
            token_usage=dict(usage) if usage else None,
            cost=cost
        )

# class ClaudeBackend(LLMBackend):
#     def call(self, prompt: str) -> LLMResponse:
#         ... # Implement for Anthropic Claude

# class LocalLLMBackend(LLMBackend):
#     def call(self, prompt: str) -> LLMResponse:
#         ... # Implement for local LLM

def get_llm_backend(name: Optional[str] = None) -> LLMBackend:
    backend = (name or os.environ.get("LLM_BACKEND", "openai")).lower()
    if backend == "openai":
        return OpenAIBackend()
#    elif backend == "claude":
#        return ClaudeBackend()
#    elif backend == "local":
#        return LocalLLMBackend()
    else:
        raise ValueError(f"Unknown LLM backend: {backend}")
