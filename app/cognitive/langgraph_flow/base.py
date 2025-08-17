# app/cognitive/langgraph_flow/base.py

"""
BaseNode: Abstract base class for all nodes in the cognitive graph.
"""
from typing import Any, Dict, Optional, TypeVar, Generic

T = TypeVar('T')

class BaseNode(Generic[T]):
    def __init__(self, name: str):
        self.name = name

    def run(self, input_data: Any, context: Optional[Dict] = None) -> T:
        raise NotImplementedError("Each node must implement the run method.")

    def after_run(self, output_data: T, context: Optional[Dict] = None):
        """
        TODO: Optional lifecycle hook for memory updates, feedback, etc. after node execution.
        Override in subclasses as needed.
        """
        pass
