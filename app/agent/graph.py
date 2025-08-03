# app/agent/graph.py

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from typing import TypedDict, List, Annotated, Optional
import operator
import logging
from datetime import date

from app.agent.tools import all_tools  # ✅ List of LangChain tools like save_generated_plan_tool

logger = logging.getLogger(__name__)

# Define the agent state with message accumulation
class AgentState(TypedDict):
    """LangGraph expects a dict-like object to store and pass state between nodes."""
    messages: Annotated[List[BaseMessage], operator.add]  # ✅ This will accumulate messages
    user_id: int  # ✅ Add user_id to state
    conversation_context: Optional[dict]  # ✅ Store conversation context and previous responses
    intent: Optional[str]  # ✅ Store the classified intent (plan_management, question, clarification, etc.)

# ✅ Define the specialized LLMs for different purposes
llm_classifier = ChatOpenAI(model="gpt-4", temperature=0)  # For intent classification
llm_conversational = ChatOpenAI(model="gpt-4", temperature=0.3)  # For conversations
llm_with_tools = ChatOpenAI(model="gpt-4", temperature=0.2).bind_tools(all_tools)  # For plan management

def get_domain_knowledge_prompt() -> str:
    """Return comprehensive domain knowledge about the personal planning system"""
    return f"""
You are an intelligent AI personal planner with deep knowledge of goal planning and productivity systems.

📊 **SYSTEM ARCHITECTURE KNOWLEDGE:**

**Goal Types:**
1. **Project Goals**: One-time objectives with specific end dates (e.g., "Learn Python", "Save $5000")
   - Have: title, description, start_date, end_date, tasks
   - Structure: Goal → Tasks (each with due_date, estimated_time)
   
2. **Habit Goals**: Recurring activities with cycles (e.g., "Exercise 3x/week", "Read daily")
   - Have: title, description, start_date, recurrence_cycle, goal_frequency_per_cycle
   - Structure: HabitGoal → HabitCycles → GoalOccurrences → Tasks
   - Cycles: monthly, weekly, daily patterns
   - Frequency: how many times per cycle (e.g., 3 times per week)

**Data Model Hierarchy:**
- **User** (has many goals, plans, tasks)
- **Goal** (base class)
  - **ProjectGoal** (end_date required)
    - **Tasks** (e.g., "Go to gym", "Pack gym bag")
  - **HabitGoal** (cycles, recurrence patterns)
    - **HabitCycle** (e.g., "July 2025", "Week 1")
      - **GoalOccurrence** (e.g., "1st workout this week")
        - **Tasks** (e.g., "Go to gym", "Pack gym bag")
- **Plan** (links goals to their generated structure, can be approved/refined)
- **Feedback** (user input for plan refinements)

**Key Planning Concepts:**
- **Tasks**: Atomic actions associated to each goal, with estimated_time, due_date
- **Cycles**: Time periods for habits (weekly, monthly, daily, quarterly, yearly, etc.)
- **Occurrences**: Individual instances within cycles (e.g., "1st workout this week")
- **Plans**: Generated structures that link goals to their tasks and timelines, can be approved or refined
- **Refinement**: Iterative improvement based on user feedback (feedback and refinement tools will be created later)

**Smart Features:**
- Plans can be refined based on user feedback (feedback and refinement tools will be created later)
- AI can generate detailed plans with realistic task breakdowns
- Tasks include preparation steps (travel, setup time)
- Progress tracking at all levels
- Timeline management with realistic scheduling

Today's date: {date.today().isoformat()}

When users ask questions, provide intelligent, contextual answers that demonstrate deep understanding of these concepts and relationships.
"""

# ✅ Intent classification node
def classify_intent_node(state: AgentState) -> AgentState:
    """Classify user intent to route to appropriate handling"""
    logger.info("🔍 INTENT CLASSIFIER: Analyzing user message...")
    
    messages = state["messages"]
    if not messages:
        return {
            "messages": [],
            "user_id": state["user_id"],
            "conversation_context": state.get("conversation_context"),
            "intent": "unclear"
        }
    
    last_human_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg
            break
    
    if not last_human_message:
        return {
            "messages": [],
            "user_id": state["user_id"],
            "conversation_context": state.get("conversation_context"),
            "intent": "unclear"
        }
    
    user_input = str(last_human_message.content).strip().lower()
    
    # Extract conversation context
    context = state.get("conversation_context", {})
    
    # Intent classification logic with conversation context
    classification_prompt = f"""
Analyze this user message and classify their intent. Consider the conversation context and previous messages.

Current user message: "{user_input}"
Previous context: {context}

CONVERSATION HISTORY:
{chr(10).join([f"{msg.__class__.__name__}: {str(msg.content)[:100]}..." for msg in messages[-5:]])}

Classify as one of:
1. "plan_management" - User wants to create, refine, view, or manage plans/goals (e.g., "I want to...", "Help me plan...", "Refine my plan...", "Show my goals...")
2. "clarification" - User asking about previous AI response (e.g., "what do you mean by...", "can you elaborate...")
3. "question" - General questions about planning, system, or concepts
4. "greeting" - Simple greetings or casual conversation
5. "status_check" - Asking about their existing goals/plans

Respond with just the classification word.
"""
    
    try:
        # ✅ SOLUTION: Pass conversation history to intent classifier
        classification_messages = messages[-3:] + [HumanMessage(content=classification_prompt)]  # Include recent context
        response = llm_classifier.invoke(classification_messages)
        intent = str(response.content).strip().lower()
        
        # Validate intent
        valid_intents = ["plan_management", "clarification", "question", "greeting", "status_check"]
        if intent not in valid_intents:
            intent = "question"  # Default fallback
            
        logger.info(f"🔍 INTENT CLASSIFIER: Classified as '{intent}'")
        
        return {
            "messages": [],
            "user_id": state["user_id"],
            "conversation_context": context,
            "intent": intent
        }
        
    except Exception as e:
        logger.error(f"🔍 INTENT CLASSIFIER: Error classifying intent: {e}")
        return {
            "messages": [],
            "user_id": state["user_id"],
            "conversation_context": state.get("conversation_context"),
            "intent": "question"
        }

# ✅ Conversational AI node for intelligent responses
def conversational_node(state: AgentState) -> AgentState:
    """Handle conversations, questions, clarifications with domain intelligence"""
    logger.info("💬 CONVERSATIONAL NODE: Generating intelligent response...")
    
    messages = state["messages"]
    context = state.get("conversation_context", {})
    intent = state.get("intent", "question")
    
    # Get the user's message
    last_human_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg
            break
    
    if not last_human_message:
        return {
            "messages": [AIMessage(content="I'm not sure what you're asking. Could you please clarify?")],
            "user_id": state["user_id"],
            "conversation_context": context,
            "intent": intent
        }
    
    user_input = str(last_human_message.content)
    
    # Build context-aware response prompt
    system_prompt = get_domain_knowledge_prompt()
    
    context_info = ""
    if context and "last_plan_details" in context:
        context_info = f"\n\n**CONVERSATION CONTEXT:**\nPrevious plan details: {context['last_plan_details']}"
    
    if intent == "clarification":
        conversation_prompt = f"""
{system_prompt}{context_info}

The user is asking for clarification about something mentioned previously. Provide a detailed, helpful explanation that demonstrates deep understanding of planning concepts.

User question: "{user_input}"

Provide a clear, intelligent response that:
1. Directly addresses their question
2. Shows understanding of planning terminology
3. Gives practical context and examples
4. Maintains a helpful, professional tone
"""
    elif intent == "greeting":
        conversation_prompt = f"""
{system_prompt}

The user sent a greeting. Respond naturally and offer to help with their planning needs.

User message: "{user_input}"

Respond warmly and invite them to share their goals or ask questions.
"""
    else:  # general questions
        conversation_prompt = f"""
{system_prompt}{context_info}

The user has a question about planning, productivity, or goal setting. Provide an intelligent, helpful response that demonstrates expertise.

User question: "{user_input}"

Provide a comprehensive response that:
1. Directly answers their question
2. Shows deep understanding of planning concepts
3. Offers practical insights and examples
4. Suggests next steps if relevant
"""
    
    try:
        # ✅ SOLUTION: Include conversation history for conversational responses
        conversation_messages = messages[-5:] + [HumanMessage(content=conversation_prompt)]  # Include recent context
        response = llm_conversational.invoke(conversation_messages)
        response_text = str(response.content)
        
        logger.info(f"💬 CONVERSATIONAL NODE: Generated {len(response_text)} character response")
        
        return {
            "messages": [AIMessage(content=response_text)],
            "user_id": state["user_id"],
            "conversation_context": context,
            "intent": intent
        }
        
    except Exception as e:
        logger.error(f"💬 CONVERSATIONAL NODE: Error generating response: {e}")
        return {
            "messages": [AIMessage(content="I apologize, but I'm having trouble generating a response right now. Please try asking again.")],
            "user_id": state["user_id"],
            "conversation_context": context,
            "intent": intent
        }

# ✅ This node handles all plan management operations (create, refine, view, sync, etc.)
def plan_management_agent_node(state: AgentState) -> AgentState:
    from app.ai.prompts import system_prompt
    
    messages = state["messages"]
    user_id = state["user_id"]
    
    # Check if we already have successful tool results for the same goal
    last_human_message = None
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            last_human_message = msg
            break
    
    if last_human_message:
        user_input = str(last_human_message.content)
        
        # Check if we've already successfully processed this exact goal
        successful_tool_for_this_goal = False
        for msg in messages:
            if (hasattr(msg, 'type') and msg.type == "tool" and 
                hasattr(msg, 'content') and "successfully created and saved" in str(msg.content).lower()):
                successful_tool_for_this_goal = True
                break
        
        if successful_tool_for_this_goal:
            # We already successfully processed this goal, provide summary
            logger.info("🧠 [PLAN MANAGEMENT Node] Plan already processed, providing summary...")
            summary_response = AIMessage(content="Perfect! I've successfully created and saved your plan. Your structured plan is now ready and includes detailed tasks, timelines, and actionable steps. You can start working on your goal right away!")
            return {
                "messages": [summary_response], 
                "user_id": user_id,
                "conversation_context": state.get("conversation_context"),
                "intent": state.get("intent")
            }
    
    if not last_human_message:
        logger.error("🧠 [PLAN MANAGEMENT Node] No human message found")
        return {
            "messages": [AIMessage(content="I couldn't find your request. Please tell me what you'd like to achieve or how I can help with your plans.")],
            "user_id": user_id,
            "conversation_context": state.get("conversation_context"),
            "intent": state.get("intent")
        }
    
    user_input = str(last_human_message.content)
    
    # Add system prompt for plan management with conversation history
    system_msg = SystemMessage(content=system_prompt())
    plan_management_messages = messages + [system_msg]  # Include full history for context
    
    logger.info(f"\n🧠 [PLAN MANAGEMENT Node] Processing plan management for: {user_input[:100]}...\n")

    response = llm_with_tools.invoke(plan_management_messages)

    tool_calls = getattr(response, 'tool_calls', None)
    if tool_calls:
        logger.info(f"\n🧠 [PLAN MANAGEMENT Node] Response has tool calls: {len(tool_calls)} tools\n")
        for i, tool_call in enumerate(tool_calls):
            try:
                # Try different possible attribute structures
                if hasattr(tool_call, 'name'):
                    tool_name = tool_call.name
                    tool_args = getattr(tool_call, 'args', {})
                elif hasattr(tool_call, 'function'):
                    tool_name = tool_call.function.get('name', 'unknown')
                    tool_args = tool_call.function.get('arguments', {})
                else:
                    tool_name = f"tool_{i}"
                    tool_args = str(tool_call)
                
                logger.info(f"   Tool Call {i+1}: {tool_name} with args: {tool_args}")
            except Exception as e:
                logger.info(f"   Tool Call {i+1}: [Error accessing tool details: {e}]")
    else:
        logger.info("\n🧠 [PLAN MANAGEMENT Node] No tool calls found in response.\n")

    # With operator.add, we just return the new messages to be added
    return {
        "messages": [response], 
        "user_id": state["user_id"],
        "conversation_context": state.get("conversation_context"),
        "intent": state.get("intent")
    }

# ✅ Define a function to determine if we should continue or end (Decision Node / Edge)
def should_continue_plan_management(state: AgentState) -> str:
    logger.info("🔀 DECISION NODE: Determining next step for plan management...")
    
    messages = state["messages"]
    last_message = messages[-1]
    
    logger.info(f"🔍 DECISION NODE: Last message type: {type(last_message).__name__}")
    
    # If the last message is an AIMessage with tool_calls, continue to tools
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"➡️  DECISION NODE: Found {len(last_message.tool_calls)} tool calls → Going to TOOLS node")
        return "tools"
    # Otherwise, end the conversation
    logger.info("🏁 DECISION NODE: No tool calls found → ENDING conversation")
    return END

# ✅ Router node to determine which path to take
def route_intent(state: AgentState) -> str:
    """Route based on classified intent"""
    intent = state.get("intent", "question")
    
    logger.info(f"🚦 ROUTER: Intent is '{intent}' → Routing to appropriate handler")
    
    if intent == "plan_management":
        return "plan_management"
    else:
        return "conversation"

# ✅ Wrapper for ToolNode to add logging
def tool_node_with_logging(state: AgentState) -> AgentState:
    logger.info("🔧 TOOL NODE: Starting tool execution")
    
    messages = state["messages"]
    last_message = messages[-1]
    
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"🔧 TOOL NODE: Executing {len(last_message.tool_calls)} tool(s)")
        for i, tool_call in enumerate(last_message.tool_calls):
            tool_name = tool_call.get('name', 'unknown')
            logger.info(f"   Executing Tool {i}: {tool_name}")
    
    # Execute the actual tools
    tool_node = ToolNode(all_tools)
    result = tool_node.invoke(state)
    
    logger.info("✅ TOOL NODE: Tool execution completed")
    logger.info(f"📊 TOOL NODE: Returning {len(result['messages'])} new messages")
    
    # Store plan details in conversation context for future reference
    context = state.get("conversation_context", {})
    if context is None:
        context = {}
    
    # Try to extract plan details from tool results
    for msg in result["messages"]:
        if hasattr(msg, 'content'):
            try:
                import json
                content_str = str(msg.content)
                if content_str.startswith("{") and "plan_title" in content_str:
                    plan_data = json.loads(content_str)
                    context["last_plan_details"] = plan_data
                    break
            except:
                pass
    
    return {
        "messages": result["messages"],
        "user_id": state["user_id"],
        "conversation_context": context,
        "intent": state.get("intent")
    }

# ✅ Define the LangGraph workflow
graph_builder = StateGraph(AgentState)

# Add all nodes
graph_builder.add_node("classify_intent", classify_intent_node)
graph_builder.add_node("conversation", conversational_node)
graph_builder.add_node("plan_management", plan_management_agent_node)
graph_builder.add_node("tools", tool_node_with_logging)

# Set entry point
graph_builder.set_entry_point("classify_intent")

# Add routing edges
graph_builder.add_conditional_edges(
    "classify_intent",
    route_intent,
    {"plan_management": "plan_management", "conversation": "conversation"}
)

# Plan management path
graph_builder.add_conditional_edges(
    "plan_management",
    should_continue_plan_management,
    {"tools": "tools", END: END}
)
graph_builder.add_edge("tools", "plan_management")

# Conversation path goes directly to end
graph_builder.add_edge("conversation", END)

graph = graph_builder.compile()

def run_graph_with_message(user_input: str, user_id: int = 1, conversation_history: Optional[List[BaseMessage]] = None):
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.ai.prompts import system_prompt
    from app.agent.conversation_manager import conversation_manager
    """Run the LangGraph with a user input message and persistent conversation history."""
    logger.info("🚀 GRAPH EXECUTION: Starting intelligent LangGraph workflow")
    logger.info(f"📝 GRAPH INPUT: '{user_input}' for user_id={user_id}")

    logger.info("🔧 GRAPH SETUP: Creating initial state with user message")
    
    # ✅ SOLUTION: Load conversation history from persistent store
    initial_messages = []
    
    # Load previous conversation history from manager
    if conversation_history is None:  # Auto-load from manager if not provided
        conversation_history = conversation_manager.get_conversation_history(user_id, max_recent_messages=8)
    
    if conversation_history:
        initial_messages.extend(conversation_history)
        logger.info(f"🧠 CONTEXT: Loaded {len(conversation_history)} previous messages for context continuity")
    
    # Add the new user message
    new_user_message = HumanMessage(content=user_input)
    initial_messages.append(new_user_message)
    
    # Create initial state with all required fields
    state: AgentState = {
        "messages": initial_messages,  # ✅ NOW includes conversation history!
        "user_id": user_id,
        "conversation_context": {},
        "intent": None
    }
    
    logger.info(f"📊 GRAPH SETUP: Initial state has {len(state['messages'])} messages (including history)")

    logger.info("⚡ GRAPH EXECUTION: Invoking intelligent graph with recursion limit=10")
    # Set recursion limit to prevent infinite loops
    final_state = graph.invoke(state, {"recursion_limit": 10})

    logger.info("✅ GRAPH COMPLETE: Intelligent LangGraph execution finished!")

    # ✅ SOLUTION: Save the conversation to persistent store
    # Save all new messages (user input + AI responses) to conversation history
    new_messages: List[BaseMessage] = [new_user_message]  # Start with the user's message
    
    # Add AI responses from this interaction
    for msg in final_state["messages"][len(initial_messages):]:  # Only new messages
        if isinstance(msg, (AIMessage, HumanMessage)):  # Skip system messages
            new_messages.append(msg)
    
    # Save to conversation manager
    conversation_manager.add_messages(user_id, new_messages)

    # Step counter to track how many steps were taken
    step_count = len(final_state["messages"]) - len(initial_messages)  # Subtract initial messages

    logger.info(f"📈 GRAPH SUMMARY: Total steps taken: {step_count}")
    logger.info(f"📊 GRAPH SUMMARY: Final state has {len(final_state['messages'])} total messages")
    logger.info(f"🎯 GRAPH SUMMARY: Final intent: {final_state.get('intent', 'Unknown')}")
    logger.info(f"💾 GRAPH SUMMARY: Saved {len(new_messages)} messages to conversation history")

    return final_state

# If running this file directly, execute the graph with a sample input
if __name__ == "__main__":
    print("🧠 LangGraph is running locally...")
    example_input = "I want to become a CTO in a tech company in China. Can you create a plan for me?"
    final_state = run_graph_with_message(example_input)

    print("\n🧾 Final Messages:")
    for msg in final_state["messages"]:
        print(f"{msg.type.upper()}: {msg.content}\n")