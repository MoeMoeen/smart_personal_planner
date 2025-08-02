import logging
from app.agent.graph import run_graph_with_message

# Enhanced logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def trace_graph_execution():
    print("🔍 TRACING LANGGRAPH EXECUTION")
    print("="*60)
    
    # Test case 1: Simple goal
    test_input = "I want to read 12 books this year"
    
    print(f"📝 USER INPUT: {test_input}")
    print("⏳ Executing graph...")
    print("-" * 40)
    
    try:
        final_state = run_graph_with_message(test_input, user_id=1)  # Use existing user ID
        
        print("\n" + "="*60)
        print("✅ EXECUTION COMPLETE")
        print(f"📊 Total messages in state: {len(final_state['messages'])}")
        print("="*60)
        
        # Analyze each message in detail
        for i, message in enumerate(final_state['messages']):
            print(f"\n📨 Message {i}: {type(message).__name__}")
            print("-" * 30)
            
            # Check for tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                print(f"🔧 Tool calls: {len(message.tool_calls)}")
                for j, tool_call in enumerate(message.tool_calls):
                    tool_name = tool_call.get('name', 'unknown')
                    tool_args = tool_call.get('args', {})
                    print(f"   Tool {j}: {tool_name}")
                    print(f"   Args: {tool_args}")
            
            # Show content preview
            content_preview = message.content[:200] + "..." if len(message.content) > 200 else message.content
            print(f"💬 Content: {content_preview}")
            
            # Show additional attributes if available
            if hasattr(message, 'response_metadata'):
                print(f"📋 Metadata: {message.response_metadata}")
        
        print("\n" + "="*60)
        print("🎯 EXECUTION FLOW SUMMARY:")
        print("="*60)
        
        # Analyze the flow
        message_types = [type(msg).__name__ for msg in final_state['messages']]
        print(f"Message flow: {' → '.join(message_types)}")
        
        # Count tools used
        total_tool_calls = sum(
            len(getattr(msg, 'tool_calls', [])) 
            for msg in final_state['messages']
        )
        print(f"Total tool calls made: {total_tool_calls}")
        
        return final_state
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    trace_graph_execution()