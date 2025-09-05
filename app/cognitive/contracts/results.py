# app/cognitive/contracts/results.py
"""Result models for outputs from various cognitive processing steps."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any, Optional


class IntentResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ✅ replaces orm_mode

    intent: str = Field(..., description="Recognized intent name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Extracted parameters")
    confidence: float = Field(default=0.0, description="Confidence score from LLM")
    notes: Optional[str] = Field(default=None, description="Extra notes or clarifications")
    llm_raw_response: Optional[str] = Field(default=None, description="Raw LLM output for debugging")
    token_usage: Dict[str, Any] = Field(default_factory=dict, description="Token usage info")
    llm_cost: float = Field(default=0.0, description="Approximate cost of LLM call")