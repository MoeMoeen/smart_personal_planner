# app/agent/graph.py

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage
from typing import TypedDict, List, Annotated
import operator
import logging

from app.agent.tools import all_tools  # ✅ List of LangChain tools like save_generated_plan_tool

logger = logging.getLogger(__name__)

# Define the agent state with message accumulation
class AgentState(TypedDict):
    """LangGraph expects a dict-like object to store and pass state between nodes."""
    messages: Annotated[List[BaseMessage], operator.add]  # ✅ This will accumulate messages
    user_id: int  # ✅ Add user_id to state
    
# ✅ Define the LLM agent that can reason and call tools
llm_with_tools = ChatOpenAI(model="gpt-4", temperature=0.2).bind_tools(all_tools)

# ✅ This node runs the LLM and may call tools
def agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if last_message is not None:
        content = str(last_message.content) if last_message.content else "No content"
        message_preview = content[:100] + "..." if len(content) > 100 else content
        logger.info(f"\n🧠 [AGENT Node] Processing last message ({type(last_message).__name__}): {message_preview}\n")
    else:
        logger.info("\n🧠 [AGENT Node] No messages to process.\n")

    response = llm_with_tools.invoke(messages)

    tool_calls = getattr(response, 'tool_calls', None)
    if tool_calls:
        logger.info(f"\n🧠 [AGENT Node] Response has tool calls: {len(tool_calls)} tools\n")
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
        logger.info("\n🧠 [AGENT Node] No tool calls found in response.\n")

    # With operator.add, we just return the new messages to be added
    return {"messages": [response], "user_id": state["user_id"]}

# ✅ Define a function to determine if we should continue or end
def should_continue(state: AgentState) -> str:
    logger.info("🔀 DECISION NODE: Determining next step...")
    
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
    
    return result

# ✅ Define the LangGraph workflow
graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node_with_logging)  # Use our wrapper

graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
graph_builder.add_edge("tools", "agent")

graph = graph_builder.compile()

def run_graph_with_message(user_input: str, user_id: int = 1):
    from langchain_core.messages import HumanMessage, SystemMessage
    from app.ai.prompts import system_prompt
    """Run the LangGraph with a user input message."""
    logger.info("🚀 GRAPH EXECUTION: Starting LangGraph workflow")
    logger.info(f"📝 GRAPH INPUT: '{user_input}' for user_id={user_id}")

    logger.info("🔧 GRAPH SETUP: Creating initial state with system prompt and user message")
    messages = SystemMessage(content=system_prompt(user_input, user_id))
    state: AgentState = {"messages": [HumanMessage(content=user_input), messages], "user_id": user_id}
    
    logger.info(f"📊 GRAPH SETUP: Initial state has {len(state['messages'])} messages")

    logger.info("⚡ GRAPH EXECUTION: Invoking graph with recursion limit=10")
    # Set recursion limit to prevent infinite loops
    final_state = graph.invoke(state, {"recursion_limit": 10})

    logger.info("✅ GRAPH COMPLETE: LangGraph execution finished!")

    # Step counter to track how many steps were taken (excluding the initial system and user messages)
    step_count = len(final_state["messages"]) - 2  # Subtract initial user message and system message

    logger.info(f"📈 GRAPH SUMMARY: Total steps taken: {step_count}")
    logger.info(f"📊 GRAPH SUMMARY: Final state has {len(final_state['messages'])} total messages")

    return final_state

# If running this file directly, execute the graph with a sample input
if __name__ == "__main__":
    print("🧠 LangGraph is running locally...")
    example_input = "I want to become a CTO in a tech company in China. Can you create a plan for me?"
    final_state = run_graph_with_message(example_input)

    print("\n🧾 Final Messages:")
    for msg in final_state["messages"]:
        print(f"{msg.type.upper()}: {msg.content}\n")