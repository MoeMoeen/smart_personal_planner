# Agent Architecture Documentation

## Overview

The Smart Personal Planner now uses a **centralized agent system** that can switch between two different AI architectures:

### 🏗️ Architecture Types

#### 1. **Complex Agent (Default)** - LangGraph System
- **File**: `app/agent/graph.py`
- **Features**:
  - Multi-node reasoning workflow
  - Sophisticated conversation memory
  - Intent classification and routing
  - Advanced state management
  - Tool orchestration with feedback loops

#### 2. **Simple Agent (Alternative)** - Trust-Based System
- **File**: `app/agent/simple_agent_backup.py`
- **Features**:
  - Direct LLM-to-tool integration
  - Trust-based approach (assumes LLM makes good tool choices)
  - Minimal complexity
  - Fast execution
  - Same backend integration

## 🚀 Usage

### Centralized Entry Point
```python
from app.agent.graph import run_graph_with_message

# Default: Complex Agent
result = run_graph_with_message("I want to learn Python", user_id=1)

# Explicit agent selection
result = run_graph_with_message("I want to learn Python", user_id=1, agent_type="complex")
result = run_graph_with_message("I want to learn Python", user_id=1, agent_type="simple") 
```

### Environment Configuration
```bash
# Use complex agent (default)
export AGENT_TYPE=complex

# Use simple agent
export AGENT_TYPE=simple
```

### Factory Pattern (Alternative)
```python
from app.agent.agent_factory import AgentFactory

# Create specific agent
complex_agent = AgentFactory.create_agent("complex")
simple_agent = AgentFactory.create_agent("simple")

# Process messages
result = complex_agent.process_message("Hello", user_id=1)
```

## 🔧 Integration Points

### 1. Telegram Bot
- **File**: `app/routers/telegram.py`
- **Current**: Uses complex agent by default
- **Switching**: Set `AGENT_TYPE=simple` environment variable

### 2. FastAPI Endpoints
- **File**: `app/routers/planning.py`
- **Integration**: Can use either agent through centralized entry point

### 3. Testing & Development
- **Files**: `test_*.py`, `compare_agents.py`
- **Usage**: Can test both agents separately or in comparison

## 🛠️ Technical Details

### Response Formats

#### Complex Agent Response
```python
{
    "messages": [HumanMessage(...), AIMessage(...)],
    "user_id": 1,
    "conversation_context": {...},
    "intent": "plan_management"
}
```

#### Simple Agent Response
```python
{
    "response": "Plan created successfully...",
    "success": True,
    "agent_type": "simple_trust_based",
    "message": "Original user input",
    "user_id": 1
}
```

### Conversation Memory

#### Complex Agent
- Uses `conversation_manager` for persistent chat history
- Automatic context loading and saving
- Multi-turn conversation support

#### Simple Agent
- Currently stateless (can be enhanced with conversation history)
- Each request is independent

## 🎯 When to Use Which Agent

### Use **Complex Agent** when:
- Need sophisticated conversation memory
- Require multi-step reasoning
- Want advanced intent classification
- Building enterprise-grade features
- Need detailed state management

### Use **Simple Agent** when:
- Want fast, direct responses
- Building MVPs or prototypes
- Need predictable behavior
- Want to minimize complexity
- Testing core functionality

## 🚀 Deployment Strategies

### Production Recommendation
1. **Primary**: Complex Agent (default)
2. **Backup**: Simple Agent (failover)
3. **A/B Testing**: Use environment variables to split traffic

### Development Workflow
1. Test both agents during development
2. Use `compare_agents.py` for side-by-side validation
3. Telegram testing with both configurations

## 📊 Performance Characteristics

| Feature | Complex Agent | Simple Agent |
|---------|--------------|--------------|
| Response Time | Slower (multi-step) | Faster (direct) |
| Memory Usage | Higher (state mgmt) | Lower (stateless) |
| Conversation Context | Excellent | Basic |
| Error Handling | Advanced | Simple |
| Tool Orchestration | Sophisticated | Direct |
| Debugging | Detailed logs | Simple logs |

## 🔄 Migration Path

### From Simple to Complex
```python
# Before
from app.agent.simple_agent_backup import run_simple_agent
result = run_simple_agent(message, user_id)

# After
from app.agent.graph import run_graph_with_message
result = run_graph_with_message(message, user_id, agent_type="complex")
```

### From Complex to Simple
```python
# Before
from app.agent.graph import run_graph_with_message
result = run_graph_with_message(message, user_id)

# After  
from app.agent.graph import run_graph_with_message
result = run_graph_with_message(message, user_id, agent_type="simple")
```

## 🔍 Monitoring & Debugging

### Log Analysis
- Complex Agent: Detailed workflow logs with step-by-step execution
- Simple Agent: Simple execution logs with tool calls

### Error Handling
- Both agents have graceful error handling
- Complex agent has more sophisticated error recovery
- Simple agent fails fast with clear error messages

## 🚧 Future Enhancements

### Planned Features
1. **Hybrid Mode**: Use simple for quick tasks, complex for advanced planning
2. **Auto-Selection**: AI chooses the best agent based on request complexity
3. **Performance Monitoring**: Real-time metrics for both agents
4. **Enhanced Simple Agent**: Add conversation memory to simple agent

### Experimental Ideas
1. **Consensus Mode**: Run both agents, compare results
2. **Shadow Testing**: Run secondary agent in background for validation
3. **Smart Fallback**: Fall back to simple agent if complex agent fails

---

**Bottom Line**: The centralized system gives you the best of both worlds - sophisticated reasoning when needed, and fast execution when preferred. Perfect for testing, development, and production flexibility! 🎉
