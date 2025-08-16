# app/cognitive/memory/router.py
"""
Memory Router - Intelligent routing system for memory storage and retrieval

This module implements the context-aware memory routing logic that decides
which memory type(s) should be used for storing or retrieving information.

Current Implementation: Rule-based routing using keyword patterns and context analysis
Future Enhancement: LLM-powered semantic routing with learning capabilities

TODO for next version:
- Integrate LLM for semantic content understanding
- Add learning from routing success/failure patterns  
- Implement contextual embeddings for better routing decisions
- Add user preference learning for personalized routing
"""

import logging
from typing import List, Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass

# Memory type imports removed - they are not used in this module


class MemoryIntent(str, Enum):
    """Types of memory intents for routing decisions"""
    STORE_EVENT = "store_event"
    STORE_PATTERN = "store_pattern"
    STORE_RULE = "store_rule"
    QUERY_FACTS = "query_facts"
    QUERY_HISTORY = "query_history"
    QUERY_PROCEDURES = "query_procedures"
    LEARN_FROM_FEEDBACK = "learn_from_feedback"


@dataclass
class MemoryRoutingDecision:
    """Result of memory routing analysis"""
    primary_memory_types: List[str]  # Main memory type(s) to use
    secondary_memory_types: Optional[List[str]] = None  # Additional types for cross-storage
    confidence: float = 1.0
    reasoning: str = ""
    metadata: Optional[Dict[str, Any]] = None


class MemoryRouter:
    """
    Memory routing system for intelligent memory type selection.
    
    Currently uses rule-based routing that decides which memory type(s) to use based on:
    1. Context metadata (source, intent, etc.)
    2. Content analysis (keyword pattern matching)
    3. Multi-type storage decisions
    
    FUTURE ENHANCEMENT: LLM-powered routing intelligence
    - LLMs currently only trigger the routing chain through agents
    - Next version will integrate LLMs directly into routing decisions
    - Planned features: semantic content analysis, contextual understanding, 
      pattern learning from past routing success/failure
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        
        # Rule-based routing patterns
        self._source_routing = {
            "WorldUpdater": ["episodic"],
            "PatternLearner": ["semantic"], 
            "RuleEngine": ["procedural"],
            "UserFeedback": ["episodic", "semantic"],  # Multi-type
            "TaskCompletion": ["episodic", "procedural"],  # Multi-type
            "ScheduleChange": ["episodic", "semantic"],  # Multi-type
        }
        
        # Content-based routing keywords
        self._content_patterns = {
            # Episodic indicators
            "episodic_keywords": [
                "happened", "occurred", "completed", "cancelled", "interrupted",
                "at 2pm", "yesterday", "on monday", "during", "while", "when",
                "user said", "user did", "user felt", "user rated"
            ],
            
            # Procedural indicators  
            "procedural_keywords": [
                "if", "then", "when", "always", "never", "should", "must",
                "workflow", "process", "step", "procedure", "rule", "constraint",
                "how to", "in order to", "to handle"
            ],
            
            # Semantic indicators
            "semantic_keywords": [
                "usually", "typically", "prefers", "pattern", "tends to",
                "generally", "often", "rarely", "learned", "knows",
                "characteristic", "behavior", "preference", "style"
            ]
        }
    
    def route_storage(
        self,
        content: str,
        context: Dict[str, Any],
        intent: Optional[MemoryIntent] = None
    ) -> MemoryRoutingDecision:
        """
        Determine where to store memory content.
        
        Args:
            content: The content to be stored
            context: Context metadata (source, timestamp, etc.)
            intent: Explicit intent if known
            
        Returns:
            Routing decision with memory type(s) and reasoning
        """
        # Start with rule-based routing
        primary_types = []
        secondary_types = []
        reasoning_parts = []
        
        # 1. Check source-based routing
        source = context.get("source", "").strip()
        if source in self._source_routing:
            primary_types.extend(self._source_routing[source])
            reasoning_parts.append(f"Source '{source}' indicates {primary_types}")
        
        # 2. Check explicit intent
        if intent:
            intent_types = self._get_types_for_intent(intent)
            if intent_types:
                if not primary_types:
                    primary_types = intent_types
                else:
                    secondary_types.extend(intent_types)
                reasoning_parts.append(f"Intent '{intent.value}' suggests {intent_types}")
        
        # 3. Content analysis (rule-based pattern matching)
        # FUTURE: Replace with LLM-powered semantic analysis
        content_types = self._analyze_content_for_types(content.lower())
        if content_types:
            # Merge with existing types
            for ctype in content_types:
                if ctype not in primary_types:
                    secondary_types.append(ctype)
            reasoning_parts.append(f"Content analysis suggests {content_types}")
        
        # 4. Apply multi-type storage logic
        final_primary, final_secondary = self._apply_multi_type_logic(
            content, context, primary_types, secondary_types
        )
        
        # 5. Fallback to semantic if nothing determined
        if not final_primary:
            final_primary = ["semantic"]
            reasoning_parts.append("Defaulting to semantic memory")
        
        return MemoryRoutingDecision(
            primary_memory_types=final_primary,
            secondary_memory_types=final_secondary or [],
            confidence=self._calculate_confidence(reasoning_parts),
            reasoning="; ".join(reasoning_parts),
            metadata={"analysis_method": "rule_based"}
        )
    
    def route_query(
        self,
        query: str,
        context: Dict[str, Any],
        intent: Optional[MemoryIntent] = None
    ) -> MemoryRoutingDecision:
        """
        Determine which memory types to query.
        
        Args:
            query: The query/question being asked
            context: Query context
            intent: Explicit query intent
            
        Returns:
            Routing decision for memory retrieval
        """
        query_lower = query.lower()
        memory_types = []
        reasoning_parts = []
        
        # Intent-based routing
        if intent:
            intent_types = self._get_types_for_intent(intent)
            memory_types.extend(intent_types)
            reasoning_parts.append(f"Intent '{intent.value}' → {intent_types}")
        
        # Query pattern analysis
        if any(word in query_lower for word in ["what happened", "when did", "last time", "history"]):
            if "episodic" not in memory_types:
                memory_types.append("episodic")
            reasoning_parts.append("Historical query → episodic")
        
        if any(word in query_lower for word in ["how to", "what should", "procedure", "workflow"]):
            if "procedural" not in memory_types:
                memory_types.append("procedural")
            reasoning_parts.append("Procedural query → procedural")
        
        if any(word in query_lower for word in ["usually", "typically", "prefers", "pattern"]):
            if "semantic" not in memory_types:
                memory_types.append("semantic")
            reasoning_parts.append("Pattern query → semantic")
        
        # Default to all types if unclear
        if not memory_types:
            memory_types = ["semantic", "episodic", "procedural"]
            reasoning_parts.append("Ambiguous query → search all types")
        
        return MemoryRoutingDecision(
            primary_memory_types=memory_types,
            confidence=0.8 if len(memory_types) == 1 else 0.6,
            reasoning="; ".join(reasoning_parts)
        )
    
    def _get_types_for_intent(self, intent: MemoryIntent) -> List[str]:
        """Map intent to memory types"""
        intent_mapping = {
            MemoryIntent.STORE_EVENT: ["episodic"],
            MemoryIntent.STORE_PATTERN: ["semantic"],
            MemoryIntent.STORE_RULE: ["procedural"],
            MemoryIntent.QUERY_FACTS: ["semantic"],
            MemoryIntent.QUERY_HISTORY: ["episodic"],
            MemoryIntent.QUERY_PROCEDURES: ["procedural"],
            MemoryIntent.LEARN_FROM_FEEDBACK: ["episodic", "semantic"]
        }
        return intent_mapping.get(intent, [])
    
    def _analyze_content_for_types(self, content: str) -> List[str]:
        """Analyze content to determine likely memory types"""
        suggested_types = []
        
        # Check for episodic indicators
        episodic_matches = sum(1 for keyword in self._content_patterns["episodic_keywords"] 
                             if keyword in content)
        
        # Check for procedural indicators
        procedural_matches = sum(1 for keyword in self._content_patterns["procedural_keywords"] 
                               if keyword in content)
        
        # Check for semantic indicators
        semantic_matches = sum(1 for keyword in self._content_patterns["semantic_keywords"] 
                             if keyword in content)
        
        # Determine types based on matches (threshold = 1)
        if episodic_matches >= 1:
            suggested_types.append("episodic")
        if procedural_matches >= 1:
            suggested_types.append("procedural")
        if semantic_matches >= 1:
            suggested_types.append("semantic")
        
        return suggested_types
    
    def _apply_multi_type_logic(
        self,
        content: str,
        context: Dict[str, Any],
        primary_types: List[str],
        secondary_types: List[str]
    ) -> tuple[List[str], List[str]]:
        """Apply multi-type storage logic based on content patterns and context"""
        content_lower = content.lower()
        
        # Events that should be stored in multiple types
        multi_type_patterns = {
            # Task completion events
            ("completed", "task"): ["episodic", "semantic"],
            ("finished", "work"): ["episodic", "semantic"],
            
            # Cancellation events  
            ("cancelled", "meeting"): ["episodic", "semantic", "procedural"],
            ("cancelled", "task"): ["episodic", "semantic"],
            
            # Schedule changes
            ("rescheduled", "moved"): ["episodic", "semantic"],
            ("changed", "schedule"): ["episodic", "semantic"],
            
            # User feedback
            ("user said", "feedback"): ["episodic", "semantic"],
            ("user rated", "rating"): ["episodic", "semantic"],
            
            # Performance events
            ("early", "late", "delayed"): ["episodic", "semantic"],
        }
        
        # Check for multi-type patterns
        additional_types = set()
        for pattern_words, pattern_types in multi_type_patterns.items():
            if any(word in content_lower for word in pattern_words):
                additional_types.update(pattern_types)
        
        # Use context to enhance multi-type decisions
        source = context.get("source", "")
        if source == "UserFeedback" and "procedural" not in additional_types:
            # User feedback often creates new rules
            additional_types.add("procedural")
        
        # Context-based priority adjustments
        if context.get("priority") == "high" or context.get("user_initiated", False):
            # High priority or user-initiated events should be in episodic
            additional_types.add("episodic")
        
        # Time-sensitive context
        if context.get("schedule_related", False):
            additional_types.update(["episodic", "semantic"])
        
        # Merge additional types
        all_types = set(primary_types + secondary_types)
        all_types.update(additional_types)
        
        # Separate back into primary and secondary
        if additional_types:
            # Keep original primary, add new ones to secondary
            final_primary = list(set(primary_types))
            final_secondary = list(additional_types - set(primary_types))
        else:
            final_primary = primary_types
            final_secondary = secondary_types
        
        return final_primary, final_secondary
    
    def _calculate_confidence(self, reasoning_parts: List[str]) -> float:
        """Calculate confidence based on routing reasoning"""
        if not reasoning_parts:
            return 0.3
        
        # More reasoning = higher confidence
        base_confidence = 0.6
        reasoning_boost = min(0.3, len(reasoning_parts) * 0.1)
        
        # Penalty for fallback/default reasoning
        if any("defaulting" in part.lower() for part in reasoning_parts):
            return base_confidence * 0.5
        
        return min(1.0, base_confidence + reasoning_boost)


# Convenience function for easy routing
def route_memory_storage(
    content: str,
    context: Dict[str, Any],
    intent: Optional[MemoryIntent] = None,
    router: Optional[MemoryRouter] = None
) -> MemoryRoutingDecision:
    """
    Convenient function to route memory storage.
    
    Args:
        content: Content to store
        context: Context information
        intent: Optional explicit intent
        router: Optional custom router instance
        
    Returns:
        Routing decision
    """
    if router is None:
        router = MemoryRouter()
    
    return router.route_storage(content, context, intent)
