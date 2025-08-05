#!/usr/bin/env python3
"""
Test Centralized Agent System
=============================

This script tests the new centralized agent architecture to ensure
both complex and simple agents work correctly through the unified entry point.
"""

import os
import sys

# Add the project root directory to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

def test_centralized_system():
    """Test both agents through the centralized entry point"""
    print("🧪 TESTING CENTRALIZED AGENT SYSTEM")
    print("=" * 50)
    
    try:
        from app.agent.graph import run_graph_with_message
        
        test_message = "I want to exercise 3 times per week"
        test_user_id = 999
        
        print("🤖 TESTING COMPLEX AGENT:")
        print("-" * 30)
        
        try:
            result_complex = run_graph_with_message(
                test_message, 
                user_id=test_user_id, 
                agent_type="complex"
            )
            
            if isinstance(result_complex, dict) and "messages" in result_complex:
                print("✅ Complex agent working correctly")
                print(f"📊 Messages: {len(result_complex['messages'])}")
                print(f"🎯 Intent: {result_complex.get('intent', 'Unknown')}")
                
                # Show final response
                if result_complex["messages"]:
                    final_msg = result_complex["messages"][-1]
                    print(f"📝 Response preview: {str(final_msg.content)[:100]}...")
            else:
                print("❌ Complex agent returned unexpected format")
                print(f"Result type: {type(result_complex)}")
                
        except Exception as e:
            print(f"❌ Complex agent failed: {e}")
        
        print("\n🧠 TESTING SIMPLE AGENT:")
        print("-" * 30)
        
        try:
            result_simple = run_graph_with_message(
                test_message, 
                user_id=test_user_id, 
                agent_type="simple"
            )
            
            if isinstance(result_simple, dict) and "response" in result_simple:
                print("✅ Simple agent working correctly")
                print(f"🤖 Agent type: {result_simple.get('agent_type', 'Unknown')}")
                print(f"✅ Success: {result_simple.get('success', False)}")
                print(f"📝 Response preview: {result_simple.get('response', '')[:100]}...")
            else:
                print("❌ Simple agent returned unexpected format")
                print(f"Result type: {type(result_simple)}")
                
        except Exception as e:
            print(f"❌ Simple agent failed: {e}")
        
        print("\n🎯 TESTING ENVIRONMENT VARIABLE:")
        print("-" * 40)
        
        # Test environment variable override
        os.environ["AGENT_TYPE"] = "simple"
        try:
            result_env = run_graph_with_message(
                "Quick test with env var", 
                user_id=test_user_id
            )
            
            if isinstance(result_env, dict) and "response" in result_env:
                print("✅ Environment variable working correctly")
                print(f"🔧 Used agent: {result_env.get('agent_type', 'Unknown')}")
            else:
                print("❌ Environment variable test failed")
                
        except Exception as e:
            print(f"❌ Environment variable test failed: {e}")
        finally:
            # Reset environment
            if "AGENT_TYPE" in os.environ:
                del os.environ["AGENT_TYPE"]
        
        print("\n🎉 CENTRALIZED SYSTEM TEST COMPLETE!")
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("Make sure all dependencies are installed")
    except Exception as e:
        print(f"❌ Test failed: {e}")

if __name__ == "__main__":
    test_centralized_system()
