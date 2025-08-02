from app.agent.graph import run_graph_with_message
import logging

# Set up detailed logging to see everything
logging.basicConfig(level=logging.INFO)

# Test the AI plan generation
test_prompt = "I want to learn Python programming in 6 months"
print("🧪 TESTING: AI Plan Generation Flow")
print(f"Input: {test_prompt}")
print("="*50)

final_state = run_graph_with_message(test_prompt)

print("\n📋 FINAL RESULT:")
for i, msg in enumerate(final_state["messages"]):
    print(f"Message {i}: {msg.__class__.__name__}")
    print(f"Content: {msg.content[:200]}...")
    print("-" * 30)