# app/cognitive/memory/episodic.py
"""
Episodic Memory Module for Smart Personal Planner

Stores specific events and experiences with rich temporal and contextual details.
Focus: "What happened, when, where, and under what circumstances?"

Examples:
- User canceled 2pm meeting on August 15th because they felt sick
- AI suggested 9am workout, user said 'too early' and moved to 10am  
- User completed task 30 minutes earlier than estimated
"""

import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime
from dataclasses import dataclass
from sqlalchemy.orm import Session

from ..contracts.types import MemoryObject
from .storage import write_memory, retrieve_memory


@dataclass
class EpisodicEvent:
    """Single episodic memory entry with rich context"""
    id: str
    timestamp: datetime
    user_id: int
    event_type: str  # e.g., "task_completion", "meeting_cancelled", "schedule_change"
    description: str
    context: Dict[str, Any]  # Rich contextual information
    location: Optional[str] = None
    mood: Optional[str] = None
    participants: Optional[List[str]] = None
    outcome: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EpisodicMemory:
    """
    Episodic memory system for recording specific events and experiences.
    
    This module captures the "what actually happened" dimension of user interactions,
    providing rich context for learning and pattern recognition.
    """
    
    def __init__(self, user_id: int, db_session: Optional[Session] = None, logger: Optional[logging.Logger] = None):
        self.user_id = user_id
        self.db_session = db_session
        self.logger = logger or logging.getLogger(__name__)
        self._event_counter = 0
    
    def record_event(
        self, 
        event_type: str,
        description: str,
        context: Dict[str, Any],
        location: Optional[str] = None,
        mood: Optional[str] = None,
        participants: Optional[List[str]] = None,
        outcome: Optional[str] = None
    ) -> str:
        """
        Record a specific episodic event.
        
        Args:
            event_type: Category of event (task_completion, meeting_cancelled, etc.)
            description: Human-readable description of what happened
            context: Rich contextual information
            location: Where the event occurred
            mood: User's mood/emotional state
            participants: Other people involved
            outcome: Result or consequence of the event
            
        Returns:
            Event ID for reference
        """
        event_id = f"episodic_{self.user_id}_{self._event_counter}"
        self._event_counter += 1
        
        event = EpisodicEvent(
            id=event_id,
            timestamp=datetime.now(),
            user_id=self.user_id,
            event_type=event_type,
            description=description,
            context=context,
            location=location,
            mood=mood,
            participants=participants or [],
            outcome=outcome,
            metadata={
                "confidence": 1.0,
                "source": "direct_observation"
            }
        )
        
        # Store in database if session available
        if self.db_session:
            self._persist_to_database(event)
        
        self.logger.info(f"Recorded episodic event: {event_type} - {description}")
        return event_id
    
    def record_task_completion(
        self, 
        task_id: str, 
        planned_duration: int, 
        actual_duration: int,
        completion_quality: Optional[str] = None,
        interruptions: Optional[List[str]] = None
    ) -> str:
        """Record task completion event with performance context"""
        return self.record_event(
            event_type="task_completion",
            description=f"Task {task_id} completed",
            context={
                "task_id": task_id,
                "planned_duration_minutes": planned_duration,
                "actual_duration_minutes": actual_duration,
                "efficiency": actual_duration / planned_duration if planned_duration > 0 else 1.0,
                "completion_quality": completion_quality,
                "interruptions": interruptions or []
            },
            outcome="completed"
        )
    
    def record_schedule_change(
        self,
        original_plan: Dict[str, Any],
        new_plan: Dict[str, Any], 
        reason: str,
        initiated_by: str  # "user" or "system"
    ) -> str:
        """Record when schedule changes occur"""
        return self.record_event(
            event_type="schedule_change",
            description=f"Schedule modified: {reason}",
            context={
                "original_plan": original_plan,
                "new_plan": new_plan,
                "reason": reason,
                "initiated_by": initiated_by,
                "change_magnitude": self._calculate_change_magnitude(original_plan, new_plan)
            }
        )
    
    def record_user_feedback(
        self,
        feedback_type: str,  # "rating", "complaint", "compliment", "suggestion"
        content: str,
        rating: Optional[int] = None,
        related_task_id: Optional[str] = None
    ) -> str:
        """Record user feedback events"""
        return self.record_event(
            event_type="user_feedback",
            description=f"User provided {feedback_type}: {content}",
            context={
                "feedback_type": feedback_type,
                "content": content,
                "rating": rating,
                "related_task_id": related_task_id
            },
            mood=self._infer_mood_from_feedback(feedback_type, content, rating)
        )
    
    def get_events_by_timeframe(
        self, 
        start_date: datetime, 
        end_date: datetime,
        event_types: Optional[List[str]] = None
    ) -> List[EpisodicEvent]:
        """Retrieve events within a specific timeframe"""
        if not self.db_session:
            self.logger.warning("No database session available for retrieving events")
            return []
        
        try:
            # Get all episodic memories for this user
            memory_context = retrieve_memory(
                db=self.db_session,
                user_id=str(self.user_id),
                types=["episodic"]
            )
            
            events = []
            for memory_obj in memory_context.episodic:
                # Filter by timeframe
                if start_date <= memory_obj.timestamp <= end_date:
                    # Filter by event type if specified
                    if event_types is None or self._get_event_type_from_content(memory_obj.content) in event_types:
                        event = self._memory_obj_to_episodic_event(memory_obj)
                        if event:
                            events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve events by timeframe: {e}")
            return []
    
    def get_events_by_context(
        self,
        context_filters: Dict[str, Any]
    ) -> List[EpisodicEvent]:
        """Retrieve events matching specific context criteria"""
        if not self.db_session:
            self.logger.warning("No database session available for retrieving events")
            return []
        
        try:
            # Get all episodic memories for this user
            memory_context = retrieve_memory(
                db=self.db_session,
                user_id=str(self.user_id),
                types=["episodic"]
            )
            
            events = []
            for memory_obj in memory_context.episodic:
                # Check if this memory matches the context filters
                if self._matches_context_filters(memory_obj.content, context_filters):
                    event = self._memory_obj_to_episodic_event(memory_obj)
                    if event:
                        events.append(event)
            
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve events by context: {e}")
            return []
    
    def _persist_to_database(self, event: EpisodicEvent) -> bool:
        """Persist episodic event to database"""
        try:
            if not self.db_session:
                return False
                
            memory_obj = MemoryObject(
                memory_id=event.id,
                user_id=str(event.user_id),
                goal_id=event.context.get("goal_id"),
                type="episodic",
                content={
                    "event_type": event.event_type,
                    "description": event.description,
                    "context": event.context,
                    "location": event.location,
                    "mood": event.mood,
                    "participants": event.participants,
                    "outcome": event.outcome
                },
                timestamp=event.timestamp,
                metadata=event.metadata
            )
            
            write_memory(self.db_session, memory_obj)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to persist episodic event {event.id}: {e}")
            return False
    
    def _calculate_change_magnitude(self, original: Dict, new: Dict) -> float:
        """Calculate how significant a schedule change is (0.0-1.0)"""
        # Simple implementation - could be more sophisticated
        changes = 0
        total_fields = 0
        
        all_keys = set(original.keys()) | set(new.keys())
        for key in all_keys:
            total_fields += 1
            if original.get(key) != new.get(key):
                changes += 1
        
        return changes / total_fields if total_fields > 0 else 0.0
    
    def _infer_mood_from_feedback(self, feedback_type: str, content: str, rating: Optional[int]) -> Optional[str]:
        """Infer user mood from feedback characteristics"""
        if rating:
            if rating >= 4:
                return "positive"
            elif rating <= 2:
                return "negative"
            else:
                return "neutral"
        
        if feedback_type in ["complaint"]:
            return "frustrated"
        elif feedback_type in ["compliment"]:
            return "satisfied"
        
        # Could use sentiment analysis on content here
        return None
    
    def _memory_obj_to_episodic_event(self, memory_obj: MemoryObject) -> Optional[EpisodicEvent]:
        """Convert MemoryObject back to EpisodicEvent"""
        try:
            content = memory_obj.content
            
            # Handle case where content might be a string instead of dict
            if isinstance(content, str):
                # If content is a string, create a basic event structure
                return EpisodicEvent(
                    id=memory_obj.memory_id or f"episodic_{self.user_id}_unknown",
                    timestamp=memory_obj.timestamp,
                    user_id=int(memory_obj.user_id),
                    event_type="unknown",
                    description=content,
                    context={},
                    metadata=memory_obj.metadata
                )
            
            # Handle dictionary content (expected case)
            if isinstance(content, dict):
                return EpisodicEvent(
                    id=memory_obj.memory_id or f"episodic_{self.user_id}_unknown",
                    timestamp=memory_obj.timestamp,
                    user_id=int(memory_obj.user_id),
                    event_type=content.get("event_type", "unknown"),
                    description=content.get("description", ""),
                    context=content.get("context", {}),
                    location=content.get("location"),
                    mood=content.get("mood"),
                    participants=content.get("participants", []),
                    outcome=content.get("outcome"),
                    metadata=memory_obj.metadata
                )
            
            # Fallback for unexpected content types
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to convert memory object to episodic event: {e}")
            return None
    
    def _matches_context_filters(self, content: Union[str, Dict[str, Any]], filters: Dict[str, Any]) -> bool:
        """Check if memory content matches the provided filters"""
        # If content is a string, we can only do basic text matching
        if isinstance(content, str):
            for filter_key, filter_value in filters.items():
                if filter_key == "description" and isinstance(filter_value, str):
                    if filter_value.lower() not in content.lower():
                        return False
                else:
                    # Can't match other filters with string content
                    return False
            return True
        
        # Handle dictionary content (expected case)
        if not isinstance(content, dict):
            return False
            
        for filter_key, filter_value in filters.items():
            if filter_key in content:
                # Direct match
                if content[filter_key] == filter_value:
                    continue
                # Check nested context
                elif filter_key == "context" and isinstance(content.get("context"), dict):
                    context = content["context"]
                    if isinstance(filter_value, dict):
                        # Check if all filter_value items are in context
                        if all(context.get(k) == v for k, v in filter_value.items()):
                            continue
                # List membership check
                elif isinstance(content[filter_key], list) and filter_value in content[filter_key]:
                    continue
                # String contains check
                elif isinstance(content[filter_key], str) and isinstance(filter_value, str):
                    if filter_value.lower() in content[filter_key].lower():
                        continue
                
                # If we reach here, this filter didn't match
                return False
            else:
                # Filter key not found in content
                return False
        
        return True  # All filters matched
    
    def _get_event_type_from_content(self, content: Union[str, Dict[str, Any]]) -> str:
        """Extract event type from content, handling both string and dict formats"""
        if isinstance(content, dict):
            return content.get("event_type", "unknown")
        return "unknown"  # String content doesn't have structured event type
