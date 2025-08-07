# app/agent/agent_factory.py
"""
Agent Factory - Clean Interface for Agent Selection
==================================================

This factory provides a clean interface to switch between different agent
architectures without changing the calling code.

Usage:
    from app.agent.agent_factory import AgentFactory
    
    # Use complex agent (default)
    agent = AgentFactory.create_agent("complex")
    result = agent.process_message("I want to read books", user_id=1)
    
    # Use simple agent
    agent = AgentFactory.create_agent("simple")  
    result = agent.process_message("I want to read books", user_id=1)
"""

import os
from typing import Dict, Any, Literal
from abc import ABC, abstractmethod

AgentType = Literal["complex", "simple"]

class BaseAgent(ABC):
    """Abstract base class for all agent implementations"""
    
    @abstractmethod
    def process_message(self, message: str, user_id: int) -> Dict[str, Any]:
        """Process a user message and return a response"""
        pass

class ComplexAgent(BaseAgent):
    """Wrapper for the complex LangGraph agent"""
    
    def process_message(self, message: str, user_id: int) -> Dict[str, Any]:
        from app.agent.graph import run_graph_with_message
        
        try:
            result = run_graph_with_message(message, user_id=user_id)
            
            # Extract the final response
            final_message = ""
            if result.get("messages"):
                final_message = result["messages"][-1].content
            
            return {
                "response": final_message,
                "success": True,
                "agent_type": "complex_langgraph",
                "intent": result.get("intent", "unknown"),
                "message_count": len(result.get("messages", [])),
                "raw_result": result
            }
            
        except Exception as e:
            return {
                "response": f"Complex agent error: {str(e)}",
                "success": False,
                "agent_type": "complex_langgraph",
                "error": str(e)
            }

class SimpleAgent(BaseAgent):
    """Wrapper for the simple trust-based agent"""
    
    def process_message(self, message: str, user_id: int) -> Dict[str, Any]:
        from app.agent.simple_agent import SimplePlanningAgent
        import asyncio
        
        try:
            agent = SimplePlanningAgent()
            
            # Handle async chat method
            response = asyncio.run(agent.chat(user_id, message))
            
            return {
                "response": response,
                "success": True,
                "agent_type": "simple_trust_based",
                "message": "Simple agent processed successfully"
            }
            
        except Exception as e:
            return {
                "response": f"Simple agent error: {str(e)}",
                "success": False,
                "agent_type": "simple_trust_based",
                "error": str(e)
            }

class AgentFactory:
    """Factory class for creating different agent types"""
    
    @staticmethod
    def create_agent(agent_type: AgentType = "complex") -> BaseAgent:
        """
        Create an agent of the specified type.
        
        Args:
            agent_type: Either "complex" or "simple"
            
        Returns:
            BaseAgent instance
        """
        if agent_type == "complex":
            return ComplexAgent()
        elif agent_type == "simple":
            return SimpleAgent()
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")
    
    @staticmethod
    def get_default_agent() -> BaseAgent:
        """Get the default agent (complex)"""
        return AgentFactory.create_agent("complex")
    
    @staticmethod
    def from_env() -> BaseAgent:
        """Create agent based on environment variable AGENT_TYPE"""
        agent_type = os.getenv("AGENT_TYPE", "complex").lower()
        if agent_type not in ["complex", "simple"]:
            agent_type = "complex" 
        return AgentFactory.create_agent(agent_type)  # type: ignore

# Convenience function for direct usage
def process_user_message(message: str, user_id: int, agent_type: AgentType = "complex") -> Dict[str, Any]:
    """
    Process a user message with the specified agent type.
    
    This is a convenience function that combines agent creation and message processing.
    """
    agent = AgentFactory.create_agent(agent_type)
    return agent.process_message(message, user_id)

# Example usage
if __name__ == "__main__":
    # Test both agents with the same message
    test_message = "I want to read 2 books per month"
    test_user_id = 1
    
    print("🤖 COMPLEX AGENT:")
    print("-" * 50)
    complex_result = process_user_message(test_message, test_user_id, "complex")
    print(f"Success: {complex_result['success']}")
    print(f"Response: {complex_result['response'][:200]}...")
    
    print("\n🧠 SIMPLE AGENT:")
    print("-" * 50)
    simple_result = process_user_message(test_message, test_user_id, "simple")
    print(f"Success: {simple_result['success']}")
    print(f"Response: {simple_result['response'][:200]}...")
