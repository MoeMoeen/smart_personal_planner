# app/cognitive/memory/procedural.py
"""
Procedural Memory Module for Smart Personal Planner

Stores workflows, rules, and step-by-step processes for decision making.
Focus: "How to do things?" and "What should happen when...?"

Examples:
- When scheduling exercise, check if user has eaten in last 2 hours
- If user misses morning routine, compress lunch break by 15 minutes
- To handle conflicting priorities: 1) Check deadlines, 2) Ask user, 3) Suggest alternatives
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session

from ..contracts.types import MemoryObject
from .storage import write_memory


class RuleType(str, Enum):
    """Types of procedural rules"""
    CONDITION_ACTION = "condition_action"  # If X then Y
    WORKFLOW = "workflow"  # Step-by-step process
    CONSTRAINT = "constraint"  # Must/must not rules
    PREFERENCE = "preference"  # Preferred ways of doing things


@dataclass
class ProceduralRule:
    """Single procedural memory entry"""
    id: str
    rule_type: RuleType
    name: str
    description: str
    conditions: List[Dict[str, Any]]  # When to apply this rule
    actions: List[Dict[str, Any]]    # What to do
    priority: int  # Higher = more important
    confidence: float  # How reliable is this rule (0.0-1.0)
    usage_count: int  # How often has this been used
    success_rate: float  # How often does this work well
    created_at: datetime
    updated_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ProceduralMemory:
    """
    Procedural memory system for storing workflows and decision rules.
    
    This module captures "how to do things" knowledge that guides AI behavior,
    enabling consistent and learned responses to common situations.
    """
    
    def __init__(self, user_id: int, db_session: Optional[Session] = None, logger: Optional[logging.Logger] = None):
        self.user_id = user_id
        self.db_session = db_session
        self.logger = logger or logging.getLogger(__name__)
        self._rule_counter = 0
        self._rules: Dict[str, ProceduralRule] = {}
    
    def add_condition_action_rule(
        self,
        name: str,
        condition: Dict[str, Any],
        action: Dict[str, Any],
        priority: int = 5,
        confidence: float = 0.8
    ) -> str:
        """
        Add a simple if-then rule.
        
        Args:
            name: Human-readable name for the rule
            condition: When to trigger (e.g., {"user_mood": "stressed"})
            action: What to do (e.g., {"suggest": "take_break", "duration": 15})
            priority: Rule priority (1-10, higher = more important)
            confidence: How reliable this rule is
            
        Returns:
            Rule ID
        """
        return self._add_rule(
            rule_type=RuleType.CONDITION_ACTION,
            name=name,
            description=f"If {condition}, then {action}",
            conditions=[condition],
            actions=[action],
            priority=priority,
            confidence=confidence
        )
    
    def add_workflow(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        triggers: List[Dict[str, Any]],
        priority: int = 5
    ) -> str:
        """
        Add a multi-step workflow.
        
        Args:
            name: Workflow name
            description: What this workflow accomplishes
            steps: Ordered list of steps to execute
            triggers: Conditions that start this workflow
            priority: Workflow priority
            
        Returns:
            Rule ID
        """
        return self._add_rule(
            rule_type=RuleType.WORKFLOW,
            name=name,
            description=description,
            conditions=triggers,
            actions=steps,
            priority=priority,
            confidence=0.9
        )
    
    def add_constraint(
        self,
        name: str,
        constraint_type: str,  # "must", "must_not", "prefer", "avoid"
        condition: Dict[str, Any],
        priority: int = 8
    ) -> str:
        """
        Add a constraint rule.
        
        Args:
            name: Constraint name  
            constraint_type: Type of constraint
            condition: What to constrain
            priority: Constraint priority (usually high)
            
        Returns:
            Rule ID
        """
        action = {
            "type": "constraint",
            "constraint_type": constraint_type,
            "enforce": True
        }
        
        return self._add_rule(
            rule_type=RuleType.CONSTRAINT,
            name=name,
            description=f"{constraint_type.title()}: {condition}",
            conditions=[condition],
            actions=[action],
            priority=priority,
            confidence=0.95
        )
    
    def get_applicable_rules(
        self,
        context: Dict[str, Any],
        rule_types: Optional[List[RuleType]] = None
    ) -> List[ProceduralRule]:
        """
        Get rules that apply to the current context.
        
        Args:
            context: Current situation/context
            rule_types: Filter by rule types (optional)
            
        Returns:
            List of applicable rules, sorted by priority
        """
        applicable = []
        
        for rule in self._rules.values():
            # Filter by rule type if specified
            if rule_types and rule.rule_type not in rule_types:
                continue
            
            # Check if rule conditions match context
            if self._rule_matches_context(rule, context):
                applicable.append(rule)
        
        # Sort by priority (higher first), then by success rate
        applicable.sort(key=lambda r: (r.priority, r.success_rate), reverse=True)
        return applicable
    
    def execute_rule(
        self,
        rule_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific rule and return the result.
        
        Args:
            rule_id: ID of rule to execute
            context: Current context
            
        Returns:
            Execution result
        """
        if rule_id not in self._rules:
            raise ValueError(f"Rule {rule_id} not found")
        
        rule = self._rules[rule_id]
        
        # Update usage statistics
        rule.usage_count += 1
        
        # Execute based on rule type
        if rule.rule_type == RuleType.CONDITION_ACTION:
            return self._execute_condition_action(rule, context)
        elif rule.rule_type == RuleType.WORKFLOW:
            return self._execute_workflow(rule, context)
        elif rule.rule_type == RuleType.CONSTRAINT:
            return self._execute_constraint(rule, context)
        else:
            return {"error": f"Unknown rule type: {rule.rule_type}"}
    
    def update_rule_success(self, rule_id: str, success: bool) -> None:
        """Update rule success rate based on feedback"""
        if rule_id in self._rules:
            rule = self._rules[rule_id]
            # Simple running average update
            total_attempts = rule.usage_count
            current_successes = rule.success_rate * (total_attempts - 1)
            new_successes = current_successes + (1 if success else 0)
            rule.success_rate = new_successes / total_attempts
            rule.updated_at = datetime.now()
    
    def get_rules_by_type(self, rule_type: RuleType) -> List[ProceduralRule]:
        """Get all rules of a specific type"""
        return [rule for rule in self._rules.values() if rule.rule_type == rule_type]
    
    def _add_rule(
        self,
        rule_type: RuleType,
        name: str,
        description: str,
        conditions: List[Dict[str, Any]],
        actions: List[Dict[str, Any]],
        priority: int,
        confidence: float
    ) -> str:
        """Internal method to add a rule"""
        rule_id = f"procedural_{self.user_id}_{self._rule_counter}"
        self._rule_counter += 1
        
        rule = ProceduralRule(
            id=rule_id,
            rule_type=rule_type,
            name=name,
            description=description,
            conditions=conditions,
            actions=actions,
            priority=priority,
            confidence=confidence,
            usage_count=0,
            success_rate=0.5,  # Start with neutral success rate
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self._rules[rule_id] = rule
        
        # Persist to database if available
        if self.db_session:
            self._persist_to_database(rule)
        
        self.logger.info(f"Added {rule_type.value} rule: {name}")
        return rule_id
    
    def _rule_matches_context(self, rule: ProceduralRule, context: Dict[str, Any]) -> bool:
        """Check if rule conditions match current context"""
        for condition in rule.conditions:
            if not self._condition_matches(condition, context):
                return False
        return True
    
    def _condition_matches(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Check if a single condition matches context"""
        for key, expected_value in condition.items():
            if key not in context:
                return False
            
            context_value = context[key]
            
            # Handle different comparison types
            if isinstance(expected_value, dict):
                # Handle complex conditions like {"greater_than": 5}
                if "equals" in expected_value:
                    return context_value == expected_value["equals"]
                elif "greater_than" in expected_value:
                    return context_value > expected_value["greater_than"]
                elif "contains" in expected_value:
                    return expected_value["contains"] in str(context_value)
            else:
                # Simple equality check
                if context_value != expected_value:
                    return False
        
        return True
    
    def _execute_condition_action(self, rule: ProceduralRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a condition-action rule"""
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "actions": rule.actions,
            "confidence": rule.confidence
        }
    
    def _execute_workflow(self, rule: ProceduralRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow rule"""
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "workflow_steps": rule.actions,
            "context": context
        }
    
    def _execute_constraint(self, rule: ProceduralRule, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a constraint rule"""
        return {
            "rule_id": rule.id,
            "rule_name": rule.name,
            "constraint": rule.actions[0] if rule.actions else {},
            "priority": rule.priority
        }
    
    def _persist_to_database(self, rule: ProceduralRule) -> bool:
        """Persist procedural rule to database"""
        try:
            if not self.db_session:
                return False
                
            memory_obj = MemoryObject(
                memory_id=rule.id,
                user_id=str(self.user_id),
                goal_id=None,  # Rules are generally goal-independent
                type="procedural",
                content={
                    "rule_type": rule.rule_type.value,
                    "name": rule.name,
                    "description": rule.description,
                    "conditions": rule.conditions,
                    "actions": rule.actions,
                    "priority": rule.priority,
                    "confidence": rule.confidence,
                    "usage_count": rule.usage_count,
                    "success_rate": rule.success_rate
                },
                timestamp=rule.created_at,
                metadata=rule.metadata or {}
            )
            
            write_memory(self.db_session, memory_obj)
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to persist procedural rule {rule.id}: {e}")
            return False
