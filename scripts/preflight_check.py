#!/usr/bin/env python3
"""
Pre-flight Check for Telegram Bot
=================================

This script checks that all required environment variables and dependencies 
are configured correctly before starting the Telegram bot.
"""

import os
import sys
from dotenv import load_dotenv

def check_environment():
    """Check environment configuration"""
    print("🔍 ENVIRONMENT CHECK")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Required variables
    required_vars = {
        "TELEGRAM_BOT_TOKEN": "Telegram bot token from @BotFather",
        "OPENAI_API_KEY": "OpenAI API key for GPT models"
    }
    
    missing_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "token" in var.lower() or "key" in var.lower():
                masked_value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"✅ {var}: {masked_value}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"❌ {var}: Missing - {description}")
            missing_vars.append(var)
    
    # Optional variables
    optional_vars = {
        "AGENT_TYPE": os.getenv("AGENT_TYPE", "complex"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO")
    }
    
    print("\n📋 OPTIONAL CONFIGURATION:")
    for var, value in optional_vars.items():
        print(f"🔧 {var}: {value}")
    
    return len(missing_vars) == 0

def check_dependencies():
    """Check Python dependencies"""
    print("\n🐍 DEPENDENCY CHECK")
    print("=" * 50)
    
    # Map package names to their import names
    required_packages = {
        "python-telegram-bot": "telegram",
        "langchain": "langchain", 
        "langchain-openai": "langchain_openai",
        "langgraph": "langgraph",
        "fastapi": "fastapi",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic"
    }
    
    missing_packages = []
    
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f"✅ {package_name}")
        except ImportError:
            print(f"❌ {package_name}: Not installed")
            missing_packages.append(package_name)
    
    return len(missing_packages) == 0

def check_agent_system():
    """Check agent system functionality"""
    print("\n🤖 AGENT SYSTEM CHECK")
    print("=" * 50)
    
    try:
        from app.agent.graph import run_graph_with_message
        print("✅ Complex agent system: Import successful")
        
        from app.agent.agent_factory import AgentFactory
        print("✅ Simple agent system: Import successful")
        
        print("✅ Centralized entry point: Available")
        return True
        
    except Exception as e:
        print(f"❌ Agent system error: {e}")
        return False

def main():
    """Run all pre-flight checks"""
    print("🚀 TELEGRAM BOT PRE-FLIGHT CHECK")
    print("=" * 60)
    
    env_ok = check_environment()
    deps_ok = check_dependencies() 
    agent_ok = check_agent_system()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY:")
    
    if env_ok and deps_ok and agent_ok:
        print("✅ All checks passed! Ready to start Telegram bot.")
        
        agent_type = os.getenv("AGENT_TYPE", "complex")
        print(f"\n🤖 Agent configured: {agent_type.upper()}")
        
        if agent_type == "complex":
            print("   • Using sophisticated LangGraph system")
            print("   • Advanced conversation memory")
            print("   • Multi-step reasoning")
        else:
            print("   • Using simple trust-based system")
            print("   • Direct tool integration") 
            print("   • Efficient processing")
            
        print(f"\n💡 To switch agents, set AGENT_TYPE=simple or AGENT_TYPE=complex")
        print("\n🚀 Run: python start_telegram_bot.py")
        return True
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        
        if not env_ok:
            print("\n🔧 To fix environment issues:")
            print("   1. Copy .env.example to .env")
            print("   2. Add your TELEGRAM_BOT_TOKEN and OPENAI_API_KEY")
            
        if not deps_ok:
            print("\n🔧 To fix dependency issues:")
            print("   pip install -r requirements.txt")
            
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
