"""
Check specific recent goals and their descriptions
"""
from app.db import get_db
from app.models import Goal

# Get database session
db_gen = get_db()
db = next(db_gen)

try:
    # Check the most recent goals (IDs 41, 42, 43)
    recent_goal_ids = [41, 42, 43]
    
    print('Checking recent goals created by our tests:')
    print('=' * 60)
    
    for goal_id in recent_goal_ids:
        goal = db.query(Goal).filter(Goal.id == goal_id).first()
        if goal:
            print(f'Goal ID: {goal.id}')
            print(f'Title: {goal.title}')
            print(f'Type: {goal.goal_type}')
            desc = getattr(goal, 'description', None)
            print(f'Description: "{desc}"')
            print(f'Description length: {len(desc) if desc else 0}')
            print(f'Description is None: {desc is None}')
            print(f'Description is empty string: {desc == ""}')
            print('-' * 40)
        else:
            print(f'Goal ID {goal_id}: Not found')
            print('-' * 40)
            
finally:
    db.close()
