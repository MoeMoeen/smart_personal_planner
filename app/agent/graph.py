# app/agent/graph.py

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, AIMessage
from typing import TypedDict, List, Annotated
import operator

from app.agent.tools import all_tools  # ✅ List of LangChain tools like save_generated_plan_tool

# Define the agent state with message accumulation
class AgentState(TypedDict):
    """LangGraph expects a dict-like object to store and pass state between nodes."""
    messages: Annotated[List[BaseMessage], operator.add]  # ✅ This will accumulate messages
    
# ✅ Define the LLM agent that can reason and call tools
llm_with_tools = ChatOpenAI(model="gpt-4", temperature=0.2).bind_tools(all_tools)

# ✅ This node runs the LLM and may call tools
def agent_node(state: AgentState) -> AgentState:
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    
    # With operator.add, we just return the new messages to be added
    return {"messages": [response]}

# ✅ Define a function to determine if we should continue or end
def should_continue(state: AgentState) -> str:
    messages = state["messages"]
    last_message = messages[-1]
    # If the last message is an AIMessage with tool_calls, continue to tools
    if isinstance(last_message, AIMessage) and hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        return "tools"
    # Otherwise, end the conversation
    return END

# ✅ Define the LangGraph workflow
graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", ToolNode(all_tools))  # Use ToolNode directly

graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
graph_builder.add_edge("tools", "agent")

graph = graph_builder.compile()

def run_graph_with_message(user_input: str):
    from langchain_core.messages import HumanMessage
    state: AgentState = {"messages": [HumanMessage(content=user_input)]}
    
    # Set recursion limit to prevent infinite loops
    final_state = graph.invoke(state, {"recursion_limit": 10})
    return final_state

# If running this file directly, execute the graph with a sample input
if __name__ == "__main__":
    print("🧠 LangGraph is running locally...")
    example_input = "I want to become a CTO in a tech company in China. Can you create a plan for me?"
    final_state = run_graph_with_message(example_input)

    print("\n🧾 Final Messages:")
    for msg in final_state["messages"]:
        print(f"{msg.type.upper()}: {msg.content}\n")