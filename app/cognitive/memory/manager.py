# app/cognitive/memory/manager.py
"""
Memory Manager - Central coordination for all memory types

This module provides a unified interface for memory operations across
episodic, semantic, and procedural memory systems with intelligent routing.
"""


import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.cognitive.contracts.types import MemoryContext

from .semantic import SemanticMemory
from .episodic import EpisodicMemory
from .procedural import ProceduralMemory
from .router import MemoryRouter, MemoryIntent, MemoryRoutingDecision


class UnifiedMemoryManager:
    def get_memory_context(
        self,
        query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        intent: Optional[MemoryIntent] = None,
        goal_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> MemoryContext:
        """
        Retrieve a MemoryContext object containing relevant episodic, semantic, and procedural memories
        for the given query/context/intent, filtered by user and goal as needed.
        This is designed for direct injection into LangGraph nodes.
        """
        from app.cognitive.contracts.types import MemoryContext
        # Route memory query to get relevant types
        routing_decision = self.router.route_query(query or "", context or {}, intent)
        from app.cognitive.contracts.types import MemoryObject
        episodic_memories = []
        semantic_memories = []
        procedural_memories = []
        # For each routed type, query and filter using the correct method
        for memory_type in routing_decision.primary_memory_types:
            if memory_type == "episodic":
                context_filters = context or {}
                if goal_id:
                    context_filters = dict(context_filters)
                    context_filters["goal_id"] = goal_id
                if user_id:
                    context_filters = dict(context_filters)
                    context_filters["user_id"] = user_id
                events = self.episodic.get_events_by_context(context_filters)[:limit]
                for event in events:
                    episodic_memories.append(MemoryObject(
                        memory_id=getattr(event, 'id', None),
                        user_id=str(getattr(event, 'user_id', user_id or self.user_id)),
                        goal_id=event.context.get('goal_id') if hasattr(event, 'context') else None,
                        type="episodic",
                        content={
                            "event_type": getattr(event, 'event_type', None),
                            "description": getattr(event, 'description', None),
                            "context": getattr(event, 'context', {}),
                            "timestamp": getattr(event, 'timestamp', None),
                            "location": getattr(event, 'location', None),
                            "mood": getattr(event, 'mood', None),
                            "participants": getattr(event, 'participants', []),
                            "outcome": getattr(event, 'outcome', None),
                            "metadata": getattr(event, 'metadata', {})
                        },
                        timestamp=getattr(event, 'timestamp', None) or datetime.now(timezone.utc)
                    ))
            elif memory_type == "semantic":
                memories = self.semantic.get_memories(limit=limit)
                for memory in memories:
                    semantic_memories.append(MemoryObject(
                        memory_id=getattr(memory, 'memory_id', None),
                        user_id=str(getattr(memory, 'user_id', user_id or self.user_id)),
                        goal_id=getattr(memory, 'goal_id', None),
                        type="semantic",
                        content=getattr(memory, 'data', {}),
                        timestamp=getattr(memory, 'timestamp', None) or datetime.now(timezone.utc)
                    ))
            elif memory_type == "procedural":
                rules = self.procedural.get_applicable_rules(context or {})[:limit]
                for rule in rules:
                    procedural_memories.append(MemoryObject(
                        memory_id=getattr(rule, 'id', None),
                        user_id=str(getattr(rule, 'user_id', user_id or self.user_id)),
                        goal_id=getattr(rule, 'goal_id', None),
                        type="procedural",
                        content={
                            "name": getattr(rule, 'name', None),
                            "description": getattr(rule, 'description', None),
                            "conditions": getattr(rule, 'conditions', []),
                            "actions": getattr(rule, 'actions', []),
                            "priority": getattr(rule, 'priority', None),
                            "confidence": getattr(rule, 'confidence', None),
                            "rule_type": getattr(rule, 'rule_type', None),
                            "success_rate": getattr(rule, 'success_rate', None)
                        },
                        timestamp=getattr(rule, 'created_at', None) or datetime.now(timezone.utc)
                    ))
            else:
                # Unsupported or future memory type: log and skip
                self.logger.warning(f"Memory type '{memory_type}' routed but not implemented in manager. Skipping.")
                continue
        # Always return all lists, even if some are empty
        # (Extensibility: Add new memory types here as needed)
        return MemoryContext(
            episodic=episodic_memories,
            semantic=semantic_memories,
            procedural=procedural_memories,
            user_id=user_id or str(self.user_id),
            timestamp=datetime.now(timezone.utc),
            source="UnifiedMemoryManager.get_memory_context"
        )
    """
    Central memory management system that coordinates between all memory types.
    
    Provides:
    - Intelligent routing of memory storage/retrieval
    - Multi-type memory operations
    - Unified interface for all memory systems
    - Cross-memory pattern recognition
    """
    
    def __init__(
        self, 
        user_id: int, 
        db_session: Optional[Session] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.user_id = user_id
        self.db_session = db_session
        self.logger = logger or logging.getLogger(__name__)
        
        # Initialize memory systems
        self.semantic = SemanticMemory(user_id, db_session, logger)
        self.episodic = EpisodicMemory(user_id, db_session, logger)
        self.procedural = ProceduralMemory(user_id, db_session, logger)
        
        # Initialize router
        self.router = MemoryRouter(logger)
        
        self.logger.info(f"Initialized unified memory system for user {user_id}")
    
    def store_memory(
        self,
        content: str,
        context: Dict[str, Any],
        intent: Optional[MemoryIntent] = None,
        force_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Store memory with intelligent routing to appropriate memory types.
        
        Args:
            content: The information to store
            context: Context metadata (source, timestamp, etc.)
            intent: Optional explicit intent
            force_types: Override routing and force specific memory types
            
        Returns:
            Storage results with memory IDs and routing decision
        """
        # Route memory storage
        if force_types:
            routing_decision = MemoryRoutingDecision(
                primary_memory_types=force_types,
                confidence=1.0,
                reasoning="Explicitly forced memory types"
            )
        else:
            routing_decision = self.router.route_storage(content, context, intent)
        
        results = {
            "routing_decision": routing_decision,
            "stored_memories": {},
            "errors": []
        }
        
        # Store in primary memory types
        for memory_type in routing_decision.primary_memory_types:
            try:
                memory_id = self._store_in_memory_type(memory_type, content, context)
                results["stored_memories"][memory_type] = memory_id
            except Exception as e:
                error_msg = f"Failed to store in {memory_type}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
        
        # Store in secondary memory types if specified
        for memory_type in routing_decision.secondary_memory_types or []:
            try:
                memory_id = self._store_in_memory_type(memory_type, content, context)
                results["stored_memories"][f"{memory_type}_secondary"] = memory_id
            except Exception as e:
                error_msg = f"Failed to store in secondary {memory_type}: {e}"
                results["errors"].append(error_msg)
                self.logger.warning(error_msg)
        
        self.logger.info(
            f"Stored memory in {len(results['stored_memories'])} locations: "
            f"{list(results['stored_memories'].keys())}"
        )
        
        return results
    
    def query_memory(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
        intent: Optional[MemoryIntent] = None,
        memory_types: Optional[List[str]] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Query memories with intelligent routing across memory types.
        
        Args:
            query: The query/question
            context: Query context
            intent: Optional explicit intent
            memory_types: Override routing and query specific types
            limit: Maximum results per memory type
            
        Returns:
            Query results from relevant memory types
        """
        context = context or {}
        
        # Route memory query
        if memory_types:
            routing_decision = MemoryRoutingDecision(
                primary_memory_types=memory_types,
                confidence=1.0,
                reasoning="Explicitly specified memory types"
            )
        else:
            routing_decision = self.router.route_query(query, context, intent)
        
        results = {
            "routing_decision": routing_decision,
            "memories": {},
            "total_results": 0,
            "errors": []
        }
        
        # Query from routed memory types
        for memory_type in routing_decision.primary_memory_types:
            try:
                memories = self._query_memory_type(memory_type, query, context, limit)
                results["memories"][memory_type] = memories
                results["total_results"] += len(memories)
            except Exception as e:
                error_msg = f"Failed to query {memory_type}: {e}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
        
        self.logger.info(
            f"Queried {len(results['memories'])} memory types, "
            f"found {results['total_results']} total results"
        )
        
        return results
    
    def record_event(
        self,
        event_type: str,
        description: str,
        context: Dict[str, Any],
        **kwargs
    ) -> str:
        """Convenience method to record episodic events"""
        return self.episodic.record_event(
            event_type=event_type,
            description=description,
            context=context,
            **kwargs
        )
    
    def add_rule(
        self,
        name: str,
        condition: Dict[str, Any],
        action: Dict[str, Any],
        priority: int = 5
    ) -> str:
        """Convenience method to add procedural rules"""
        return self.procedural.add_condition_action_rule(
            name=name,
            condition=condition,
            action=action,
            priority=priority
        )
    
    def learn_pattern(
        self,
        pattern_type: str,
        pattern_data: Dict[str, Any],
        confidence: float = 0.8
    ) -> str:
        """Convenience method to store semantic patterns"""
        return self.semantic.log_user_preference(
            preference_type=pattern_type,
            preference_data=pattern_data,
            confidence=confidence
        )
    
    def get_applicable_rules(
        self,
        context: Dict[str, Any]
    ) -> List[Any]:
        """Get procedural rules applicable to current context"""
        return self.procedural.get_applicable_rules(context)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory usage"""
        stats = {
            "user_id": self.user_id,
            "semantic_memories": len(self.semantic.get_memories()),
            "episodic_events": 0,  # Would need to implement in EpisodicMemory
            "procedural_rules": len(self.procedural._rules),
            "total_memories": 0
        }
        
        stats["total_memories"] = (
            stats["semantic_memories"] + 
            stats["episodic_events"] + 
            stats["procedural_rules"]
        )
        
        return stats
    
    def _store_in_memory_type(
        self,
        memory_type: str,
        content: str,
        context: Dict[str, Any]
    ) -> str:
        """Store content in specific memory type"""
        if memory_type == "semantic":
            # Determine semantic storage method based on context
            if context.get("type") == "user_preference":
                return self.semantic.log_user_preference(
                    preference_type=context.get("preference_type", "general"),
                    preference_data=context.get("preference_data", {"content": content})
                )
            elif context.get("type") == "ai_decision":
                return self.semantic.log_ai_decision(
                    decision_context=context.get("decision_context", {"content": content}),
                    reasoning=content
                )
            else:
                return self.semantic.log_operation(
                    operation_type=context.get("operation_type", "general"),
                    details=context.get("details", {"content": content})
                )
        
        elif memory_type == "episodic":
            return self.episodic.record_event(
                event_type=context.get("event_type", "general_event"),
                description=content,
                context=context
            )
        
        elif memory_type == "procedural":
            # Extract rule components from content/context
            condition = context.get("condition", {"content": content})
            action = context.get("action", {"response": "store_for_later"})
            return self.procedural.add_condition_action_rule(
                name=context.get("rule_name", f"Rule_{datetime.now().strftime('%H%M%S')}"),
                condition=condition,
                action=action
            )
        
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")
    
    def _query_memory_type(
        self,
        memory_type: str,
        query: str,
        context: Dict[str, Any],
        limit: int
    ) -> List[Any]:
        """Query specific memory type"""
        if memory_type == "semantic":
            memories = self.semantic.get_memories()
            # Simple keyword matching - could be enhanced with vector search
            matching_memories = []
            query_words = query.lower().split()
            
            for memory in memories:
                memory_text = str(memory).lower()
                if any(word in memory_text for word in query_words):
                    matching_memories.append(memory)
                    if len(matching_memories) >= limit:
                        break
            
            return matching_memories
        
        elif memory_type == "episodic":
            # Would implement similar query logic for episodic memories
            # For now, return empty list as placeholder
            return []
        
        elif memory_type == "procedural":
            # Query applicable rules based on context
            return self.procedural.get_applicable_rules(context)[:limit]
        
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")


# Convenience function for creating memory manager
def create_memory_manager(
    user_id: int,
    db_session: Optional[Session] = None
) -> UnifiedMemoryManager:
    """Create a unified memory manager instance"""
    return UnifiedMemoryManager(user_id, db_session)
