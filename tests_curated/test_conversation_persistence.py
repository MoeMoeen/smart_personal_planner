#!/usr/bin/env python3
"""
Test conversation state persistence - verify context is maintained across multiple interactions
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def test_conversation_persistence():
    """Test that conversation context persists across multiple graph executions"""
    print("🔄 Testing Conversation State Persistence...")
    
    from app.agent.graph import run_graph_with_message
    from app.agent.conversation_manager import conversation_manager
    
    # Clear any existing conversation for clean test
    user_id = 999
    conversation_manager.clear_conversation(user_id)
    
    # Step 1: First interaction - create a plan
    print("\n1️⃣ First interaction: Creating a plan...")
    result1 = run_graph_with_message("I want to learn piano in 2 months", user_id=user_id)
    
    print(f"✅ Intent: {result1.get('intent', 'Unknown')}")
    print(f"📊 Messages: {len(result1['messages'])}")
    
    if result1["messages"]:
        final_message = result1["messages"][-1]
        print(f"🤖 Response preview: {str(final_message.content)[:150]}...")
    
    # Step 2: Second interaction - ask about the plan just created
    print("\n2️⃣ Second interaction: Asking about the plan created in step 1...")
    result2 = run_graph_with_message("Show me details of the plan you just created", user_id=user_id)
    
    print(f"✅ Intent: {result2.get('intent', 'Unknown')}")
    print(f"📊 Messages: {len(result2['messages'])}")
    
    if result2["messages"]:
        final_message = result2["messages"][-1]
        response = str(final_message.content)
        print(f"🤖 Response preview: {response[:150]}...")
        
        # Check if the response shows context awareness
        context_indicators = ["piano", "2 months", "plan", "just created", "details"]
        found_indicators = [word for word in context_indicators if word.lower() in response.lower()]
        
        print(f"🎯 Context indicators found: {found_indicators}")
        
        if len(found_indicators) >= 3:
            print("✅ SUCCESS: Agent demonstrates conversation persistence!")
        else:
            print("❌ FAILED: Agent lost conversation context")
    
    # Step 3: Third interaction - ask about refinement
    print("\n3️⃣ Third interaction: Asking for refinement...")
    result3 = run_graph_with_message("Can you make the piano plan less intensive?", user_id=user_id)
    
    print(f"✅ Intent: {result3.get('intent', 'Unknown')}")
    print(f"📊 Messages: {len(result3['messages'])}")
    
    if result3["messages"]:
        final_message = result3["messages"][-1]
        response = str(final_message.content)
        print(f"🤖 Response preview: {response[:150]}...")
        
        # Check for refinement context
        refinement_indicators = ["piano", "less intensive", "plan", "refine", "adjust"]
        found_refinement = [word for word in refinement_indicators if word.lower() in response.lower()]
        
        print(f"🎯 Refinement indicators found: {found_refinement}")
        
        if len(found_refinement) >= 2:
            print("✅ SUCCESS: Agent maintains context for refinement!")
        else:
            print("❌ FAILED: Agent lost refinement context")
    
    # Step 4: Check conversation manager state
    print("\n4️⃣ Checking conversation manager state...")
    conversation_history = conversation_manager.get_conversation_history(user_id)
    print(f"📚 Total conversation messages stored: {len(conversation_history)}")
    
    for i, msg in enumerate(conversation_history[-4:], 1):  # Show last 4 messages
        msg_type = msg.__class__.__name__
        content_preview = str(msg.content)[:50]
        print(f"   {i}. {msg_type}: {content_preview}...")

def test_multiple_users():
    """Test that different users have separate conversation contexts"""
    print("\n👥 Testing Multiple User Context Separation...")
    
    from app.agent.graph import run_graph_with_message
    from app.agent.conversation_manager import conversation_manager
    
    # Clear conversations for clean test
    user_a = 1001
    user_b = 1002
    conversation_manager.clear_conversation(user_a)
    conversation_manager.clear_conversation(user_b)
    
    # User A creates a guitar plan
    print("\n🧑 User A: Creating guitar plan...")
    result_a = run_graph_with_message("I want to learn guitar", user_id=user_a)
    print(f"   User A Intent: {result_a.get('intent', 'Unknown')}")
    
    # User B creates a cooking plan
    print("\n👩 User B: Creating cooking plan...")
    result_b = run_graph_with_message("I want to learn cooking", user_id=user_b)
    print(f"   User B Intent: {result_b.get('intent', 'Unknown')}")
    
    # User A asks about their plan
    print("\n🧑 User A: Asking about their plan...")
    result_a2 = run_graph_with_message("What's in my latest plan?", user_id=user_a)
    
    if result_a2["messages"]:
        response_a = str(result_a2["messages"][-1].content)
        has_guitar = "guitar" in response_a.lower()
        has_cooking = "cooking" in response_a.lower()
        print(f"   User A response mentions guitar: {has_guitar}")
        print(f"   User A response mentions cooking: {has_cooking}")
        
        if has_guitar and not has_cooking:
            print("✅ SUCCESS: User contexts are properly separated!")
        else:
            print("❌ FAILED: User contexts are mixed!")

if __name__ == "__main__":
    print("🚀 Starting conversation persistence testing...")
    
    # Test conversation persistence
    test_conversation_persistence()
    
    # Test multiple user separation
    test_multiple_users()
    
    print("\n🎉 Conversation persistence testing completed!")
