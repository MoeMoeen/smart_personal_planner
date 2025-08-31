# app/nodes/base.py
from typing import Any, Dict, Optional, TypeVar, Generic

T = TypeVar("T")

class BaseNode(Generic[T]):
    def __init__(self, name: str):
        self.name = name

    # FlowCompiler expects a callable(state) -> Any
    def __call__(self, state: Dict[str, Any]) -> T:
        out = self.run(state, context=state)  # pass state as context by default
        self.after_run(out, context=state)
        return out

    # If you prefer, keep signature simple: run(state, context)
    def run(self, state: Dict[str, Any], context: Optional[Dict] = None) -> T:
        raise NotImplementedError

    def after_run(self, output_data: T, context: Optional[Dict] = None) -> None:
        pass
