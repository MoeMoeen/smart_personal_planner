# app/cognitive/memory/semantic.py
"""
Semantic Memory Module for Smart Personal Planner

Provides versioned logging and pattern learning for user behavior and system operations.
Currently focuses on data collection and storage for future AI learning capabilities.

Current Features:
- Operation logging with versioning
- Pattern recognition for user preferences  
- Scheduling decision analysis
- Learning from user feedback and corrections

CURRENT LIMITATION: Data collection without active learning loop
- Memories are stored but not yet injected into AI prompts
- Pattern analysis exists but isn't used for decision improvement
- This is the foundation layer for future learning integration

NEXT VERSION: Active Learning Integration
- Memory context injection into LangGraph agent prompts
- Preference-based decision enhancement
- Feedback loop for continuous AI improvement
- Pattern-driven scheduling optimization
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import json

from sqlalchemy.orm import Session
from ..contracts.types import MemoryObject
from .storage import write_memory, retrieve_memory


class SemanticMemoryType(str, Enum):
    """Types of memories that can be stored"""
    OPERATION = "operation"          # System operations (add/remove task)
    USER_PREFERENCE = "preference"   # User stated preferences
    PATTERN = "pattern"              # Detected behavioral patterns
    FEEDBACK = "feedback"            # User feedback on suggestions
    DECISION = "decision"            # AI scheduling decisions
    CORRECTION = "correction"        # User corrections to AI suggestions


class MemoryPriority(str, Enum):
    """Priority levels for memory retention"""
    LOW = "low"          # Can be deleted after 30 days
    MEDIUM = "medium"    # Keep for 90 days
    HIGH = "high"        # Keep for 1 year
    CRITICAL = "critical" # Never delete


@dataclass
class MemoryEntry:
    """Individual memory entry with versioning"""
    id: str
    memory_type: SemanticMemoryType
    timestamp: datetime
    user_id: int
    priority: MemoryPriority
    version: int
    data: Dict[str, Any]
    tags: List[str]
    description: str
    related_entities: Optional[Dict[str, str]] = None  # task_id, plan_id, goal_id links
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class SemanticMemory:
    """
    Semantic memory system for data collection and future learning integration.
    
    CURRENT FUNCTIONALITY (Data Collection Layer):
    1. Log all operations with context
    2. Store user preferences and patterns
    3. Track AI performance and user satisfaction
    4. Persist memories to database for analysis
    
    MISSING INTEGRATION (Learning Loop Layer):
    5. Inject memory context into AI prompts (NOT IMPLEMENTED)
    6. Use patterns to enhance decision making (NOT IMPLEMENTED)
    7. Feedback-driven prompt improvement (NOT IMPLEMENTED)
    
    This module creates the foundation for AI learning but doesn't yet 
    connect memories back to the LangGraph agent for decision enhancement.
    """
    
    def __init__(self, user_id: int, db_session: Optional[Session] = None, logger: Optional[logging.Logger] = None):
        self.user_id = user_id
        self.db_session = db_session
        self.logger = logger or logging.getLogger(__name__)
        self._memory_store: List[MemoryEntry] = []  # In-memory cache for fast access
        self._version_counter = 0
        
        # Load existing memories from database on initialization
        if self.db_session:
            self._load_from_database()
    
    def _convert_to_memory_object(self, entry: MemoryEntry) -> MemoryObject:
        """Convert MemoryEntry to MemoryObject for database storage"""
        return MemoryObject(
            memory_id=entry.id,
            user_id=str(entry.user_id),
            goal_id=entry.related_entities.get("goal_id") if entry.related_entities else None,
            type="semantic",  # Map all semantic memory types to "semantic" for storage
            content={
                "memory_type": entry.memory_type.value,
                "data": entry.data,
                "tags": entry.tags,
                "description": entry.description,
                "related_entities": entry.related_entities or {}
            },
            timestamp=entry.timestamp,
            metadata={
                "priority": entry.priority.value,
                "version": entry.version
            }
        )
    
    def _convert_from_memory_object(self, memory_obj: MemoryObject) -> MemoryEntry:
        """Convert MemoryObject from database back to MemoryEntry"""
        content = memory_obj.content if isinstance(memory_obj.content, dict) else {}
        
        return MemoryEntry(
            id=memory_obj.memory_id or f"loaded_{self.user_id}_{len(self._memory_store)}",
            memory_type=SemanticMemoryType(content.get("memory_type", "operation")),
            timestamp=memory_obj.timestamp,
            user_id=self.user_id,
            priority=MemoryPriority(memory_obj.metadata.get("priority", "medium")) if memory_obj.metadata else MemoryPriority.MEDIUM,
            version=memory_obj.metadata.get("version", 1) if memory_obj.metadata else 1,
            data=content.get("data", {}),
            tags=content.get("tags", []),
            description=content.get("description", ""),
            related_entities=content.get("related_entities", {})
        )
    
    def _load_from_database(self) -> None:
        """Load existing memories from database on startup"""
        try:
            if self.db_session is not None:
                memory_context = retrieve_memory(
                    self.db_session,
                    user_id=str(self.user_id),
                    types=["semantic"]  # Load semantic memories
                )
                
                # Convert and populate memory store
                for memory_obj in memory_context.semantic:
                    entry = self._convert_from_memory_object(memory_obj)
                    self._memory_store.append(entry)
                    # Update version counter to avoid conflicts
                    if entry.version >= self._version_counter:
                        self._version_counter = entry.version + 1
                        
                self.logger.info(f"Loaded {len(memory_context.semantic)} memories from database for user {self.user_id}")
        except Exception as e:
            self.logger.error(f"Failed to load memories from database: {e}")
            # Continue without database memories
    
    def _persist_to_database(self, entry: MemoryEntry) -> bool:
        """Persist a memory entry to database"""
        if not self.db_session:
            return False
            
        try:
            memory_obj = self._convert_to_memory_object(entry)
            memory_id = write_memory(self.db_session, memory_obj)
            self.logger.debug(f"Persisted memory {entry.id} to database as {memory_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to persist memory {entry.id} to database: {e}")
            return False
        
    def log_operation(self, operation_type: str, details: Dict, priority: MemoryPriority = MemoryPriority.MEDIUM) -> str:
        """
        Log a system operation for future learning.
        
        Args:
            operation_type: Type of operation (add_task, remove_task, etc.)
            details: Operation details and context
            priority: Memory retention priority
            
        Returns:
            Memory entry ID
        """
        entry_id = f"op_{self.user_id}_{self._version_counter}"
        self._version_counter += 1
        
        memory = MemoryEntry(
            id=entry_id,
            memory_type=SemanticMemoryType.OPERATION,
            timestamp=datetime.now(),
            user_id=self.user_id,
            priority=priority,
            version=self._version_counter,
            data=details,
            tags=[operation_type, "system"],
            description=f"System operation: {operation_type}",
            related_entities=details.get("related_entities", {})
        )
        
        # Store in memory for fast access
        self._memory_store.append(memory)
        
        # Persist to database
        self._persist_to_database(memory)
        
        self.logger.debug(f"Logged operation: {operation_type} -> {entry_id}")
        return entry_id
    
    def log_user_preference(self, preference_type: str, preference_data: Dict, confidence: float = 1.0) -> str:
        """
        Log a detected or stated user preference.
        
        Args:
            preference_type: Type of preference (time_blocks, break_duration, etc.)
            preference_data: The preference details
            confidence: Confidence level (0.0-1.0) in this preference
            
        Returns:
            Memory entry ID
        """
        entry_id = f"pref_{self.user_id}_{self._version_counter}"
        self._version_counter += 1
        
        data = preference_data.copy()
        data["confidence"] = confidence
        data["learned_at"] = datetime.now().isoformat()
        
        memory = MemoryEntry(
            id=entry_id,
            memory_type=SemanticMemoryType.USER_PREFERENCE,
            timestamp=datetime.now(),
            user_id=self.user_id,
            priority=MemoryPriority.HIGH,  # User preferences are important
            version=self._version_counter,
            data=data,
            tags=[preference_type, "user", "preference"],
            description=f"User preference: {preference_type}",
            related_entities={}
        )
        
        # Store in memory for fast access
        self._memory_store.append(memory)
        
        # Persist to database
        self._persist_to_database(memory)
        
        self.logger.info(f"Logged user preference: {preference_type} -> {entry_id}")
        return entry_id
    
    def log_ai_decision(self, decision_context: Dict, reasoning: str, alternatives_considered: Optional[List[Dict]] = None) -> str:
        """
        Log an AI scheduling decision for future analysis.
        
        Args:
            decision_context: Context of the decision (task, available slots, constraints)
            reasoning: Why this decision was made
            alternatives_considered: Other options that were considered
            
        Returns:
            Memory entry ID
        """
        entry_id = f"decision_{self.user_id}_{self._version_counter}"
        self._version_counter += 1
        
        data = {
            "context": decision_context,
            "reasoning": reasoning,
            "alternatives": alternatives_considered or [],
            "decision_timestamp": datetime.now().isoformat()
        }
        
        memory = MemoryEntry(
            id=entry_id,
            memory_type=SemanticMemoryType.DECISION,
            timestamp=datetime.now(),
            user_id=self.user_id,
            priority=MemoryPriority.MEDIUM,
            version=self._version_counter,
            data=data,
            tags=["ai", "decision", "scheduling"],
            description=f"AI decision: {reasoning[:50]}...",
            related_entities=decision_context.get("related_entities", {})
        )
        
        # Store in memory for fast access
        self._memory_store.append(memory)
        
        # Persist to database
        self._persist_to_database(memory)
        
        self.logger.debug(f"Logged AI decision: {entry_id}")
        return entry_id
    
    def log_user_feedback(self, feedback_type: str, feedback_data: Dict, related_memory_id: Optional[str] = None) -> str:
        """
        Log user feedback on AI suggestions or decisions.
        
        Args:
            feedback_type: Type of feedback (approval, rejection, modification)
            feedback_data: Feedback content and sentiment
            related_memory_id: ID of the memory this feedback relates to
            
        Returns:
            Memory entry ID
        """
        entry_id = f"feedback_{self.user_id}_{self._version_counter}"
        self._version_counter += 1
        
        data = feedback_data.copy()
        data["related_memory"] = related_memory_id
        data["feedback_timestamp"] = datetime.now().isoformat()
        
        memory = MemoryEntry(
            id=entry_id,
            memory_type=SemanticMemoryType.FEEDBACK,
            timestamp=datetime.now(),
            user_id=self.user_id,
            priority=MemoryPriority.HIGH,  # Feedback is critical for learning
            version=self._version_counter,
            data=data,
            tags=[feedback_type, "user", "feedback"],
            description=f"User feedback: {feedback_type}",
            related_entities=feedback_data.get("related_entities", {})
        )
        
        # Store in memory for fast access
        self._memory_store.append(memory)
        
        # Persist to database
        self._persist_to_database(memory)
        
        self.logger.info(f"Logged user feedback: {feedback_type} -> {entry_id}")
        return entry_id
    
    def get_memories(self, memory_type: Optional[SemanticMemoryType] = None, limit: int = 100) -> List[MemoryEntry]:
        """
        Retrieve memories, optionally filtered by type.
        
        Args:
            memory_type: Filter by specific memory type
            limit: Maximum number of memories to return
            
        Returns:
            List of memory entries, most recent first
        """
        memories = self._memory_store
        
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        # Sort by timestamp, most recent first
        memories.sort(key=lambda m: m.timestamp, reverse=True)
        
        return memories[:limit]
    
    def get_user_preferences(self) -> Dict[str, Any]:
        """
        Get all current user preferences as a consolidated dictionary.
        
        Returns:
            Dictionary of preference_type -> preference_data
        """
        preferences = {}
        
        for memory in self.get_memories(SemanticMemoryType.USER_PREFERENCE):
            # Extract preference type from tags
            pref_types = [tag for tag in memory.tags if tag not in ["user", "preference"]]
            if pref_types:
                pref_type = pref_types[0]
                preferences[pref_type] = memory.data
        
        return preferences
    
    def analyze_patterns(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Analyze patterns in user behavior and AI decisions.
        
        Args:
            days_back: How many days of history to analyze
            
        Returns:
            Dictionary of detected patterns and insights
        """
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_memories = [m for m in self._memory_store if m.timestamp >= cutoff_date]
        
        patterns = {
            "operation_frequency": {},
            "preferred_times": [],
            "common_corrections": [],
            "feedback_sentiment": {"positive": 0, "negative": 0, "neutral": 0}
        }
        
        for memory in recent_memories:
            if memory.memory_type == SemanticMemoryType.OPERATION:
                op_type = memory.data.get("operation_type", "unknown")
                patterns["operation_frequency"][op_type] = patterns["operation_frequency"].get(op_type, 0) + 1
            
            elif memory.memory_type == SemanticMemoryType.FEEDBACK:
                sentiment = memory.data.get("sentiment", "neutral")
                patterns["feedback_sentiment"][sentiment] += 1
        
        self.logger.info(f"Analyzed patterns from {len(recent_memories)} memories over {days_back} days")
        return patterns
    
    def export_memories(self, filepath: str) -> None:
        """Export memories to JSON file for backup/analysis"""
        export_data = {
            "user_id": self.user_id,
            "export_timestamp": datetime.now().isoformat(),
            "memory_count": len(self._memory_store),
            "memories": [memory.to_dict() for memory in self._memory_store]
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.logger.info(f"Exported {len(self._memory_store)} memories to {filepath}")


# === INTEGRATION INTERFACE ===

def create_semantic_memory(user_id: int, db_session: Optional[Session] = None, logger: Optional[logging.Logger] = None) -> SemanticMemory:
    """
    Factory function to create a semantic memory instance.
    
    Args:
        user_id: User ID for this memory instance
        db_session: Database session for persistence (optional)
        logger: Optional logger for semantic memory operations
        
    Returns:
        Configured SemanticMemory instance
    """
    return SemanticMemory(user_id=user_id, db_session=db_session, logger=logger)


# === FUTURE ENHANCEMENTS ===

class PatternLearner:
    """
    Future enhancement: Advanced pattern learning from semantic memory.
    
    Would analyze memories to:
    - Detect scheduling preferences automatically
    - Predict optimal task placement
    - Learn from user corrections
    - Improve AI decision making over time
    """
    pass


class MemoryCompressor:
    """
    Future enhancement: Compress old memories to save space while preserving insights.
    
    Would:
    - Aggregate similar operations
    - Extract patterns into rules
    - Archive detailed logs while keeping summaries
    """
    pass


class LearningLoop:
    """
    CRITICAL MISSING COMPONENT: AI Learning Integration
    
    This class would implement the actual learning mechanism:
    
    1. Memory Context Injection:
       def inject_memory_context(self, agent_prompt: str, user_id: int) -> str:
           # Retrieve relevant memories
           # Format as context for AI prompt
           # Return enhanced prompt with memory insights
    
    2. Decision Enhancement:
       def enhance_decision_with_patterns(self, decision_context: Dict) -> Dict:
           # Analyze past similar decisions
           # Apply learned patterns
           # Return improved decision context
    
    3. Feedback Integration:
       def apply_feedback_to_future_decisions(self, feedback: Dict) -> None:
           # Learn from user corrections
           # Update decision patterns
           # Modify AI behavior based on feedback
    
    4. Prompt Engineering:
       def build_personalized_prompt(self, base_prompt: str, user_preferences: Dict) -> str:
           # Inject user preferences
           # Add relevant historical context
           # Return personalized AI prompt
    
    CURRENT STATUS: NOT IMPLEMENTED
    Your AI collects data but doesn't learn from it yet.
    """
    pass
