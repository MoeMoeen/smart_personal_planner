# Feature Flag Configuration for Enhanced Features
# Allows gradual rollout and easy rollback of new features

FEATURE_FLAGS = {
    # Enhanced Model Features
    "enhanced_models": {
        "enabled": True,
        "description": "Enhanced enum types for tasks and plans",
        "rollout_percentage": 100,
        "dependencies": [],
        "risk_level": "low"
    },
    
    # Logging and Observability
    "logging_hooks": {
        "enabled": True,
        "description": "Comprehensive operation logging in WorldUpdater",
        "rollout_percentage": 100,
        "dependencies": ["enhanced_models"],
        "risk_level": "low"
    },
    
    # Conflict Resolution
    "conflict_resolution": {
        "enabled": True,
        "description": "Suggest alternative time slots when conflicts occur",
        "rollout_percentage": 75,
        "dependencies": ["enhanced_models", "logging_hooks"],
        "risk_level": "medium"
    },
    
    # Undo Functionality
    "undo_stack": {
        "enabled": True,
        "description": "Undo stack for operation rollback",
        "rollout_percentage": 50,
        "dependencies": ["enhanced_models", "logging_hooks"],
        "risk_level": "medium"
    },
    
    # Semantic Memory
    "semantic_memory": {
        "enabled": True,
        "description": "Learning and pattern recognition system",
        "rollout_percentage": 25,
        "dependencies": ["enhanced_models", "logging_hooks"],
        "risk_level": "high"
    },
    
    # LangGraph Tools
    "langgraph_tools": {
        "enabled": False,  # Start disabled for gradual rollout
        "description": "AI agent tool wrappers with observability",
        "rollout_percentage": 10,
        "dependencies": ["enhanced_models", "semantic_memory"],
        "risk_level": "high"
    },
    
    # Performance Optimizations
    "performance_indexes": {
        "enabled": True,
        "description": "Database performance indexes",
        "rollout_percentage": 100,
        "dependencies": ["enhanced_models"],
        "risk_level": "low"
    }
}

# User segments for A/B testing
USER_SEGMENTS = {
    "beta_users": {
        "description": "Early adopters and beta testers",
        "user_ids": [],  # Add specific user IDs
        "percentage": 5,
        "features": ["semantic_memory", "langgraph_tools"]
    },
    
    "power_users": {
        "description": "Heavy users of the planning system",
        "user_ids": [],  # Add specific user IDs  
        "percentage": 15,
        "features": ["conflict_resolution", "undo_stack"]
    },
    
    "general_users": {
        "description": "Regular users",
        "user_ids": [],
        "percentage": 80,
        "features": ["enhanced_models", "logging_hooks", "performance_indexes"]
    }
}

# Feature rollout schedule
ROLLOUT_SCHEDULE = {
    "phase_1": {
        "start_date": "2025-08-15",
        "features": ["enhanced_models", "logging_hooks", "performance_indexes"],
        "target_users": "all"
    },
    
    "phase_2": {
        "start_date": "2025-08-16", 
        "features": ["conflict_resolution", "undo_stack"],
        "target_users": "power_users"
    },
    
    "phase_3": {
        "start_date": "2025-08-18",
        "features": ["semantic_memory"],
        "target_users": "beta_users"
    },
    
    "phase_4": {
        "start_date": "2025-08-20",
        "features": ["langgraph_tools"],
        "target_users": "beta_users"
    }
}
