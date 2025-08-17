from pydantic import BaseModel
from typing import Dict, Any, Optional

class IntentResult(BaseModel):
    intent: str
    parameters: Dict[str, Any]
    confidence: float = 1.0
    llm_raw_response: str = ""
    token_usage: Optional[Dict[str, Any]] = None
    llm_cost: Optional[float] = None
