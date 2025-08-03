"""
Check the database for recent goals
"""
from app.db import get_db
from app.models import Goal
from app.models import HabitCycle

# Get database session
db_gen = get_db()
db = next(db_gen)

try:
    # Query all goals to see the current state
    all_goals = db.query(Goal).order_by(Goal.id.desc()).limit(10).all()
    
    print('Last 10 goals in database:')
    print('=' * 50)
    for goal in all_goals:
        print(f'Goal ID: {goal.id}')
        print(f'Title: {goal.title}')
        print(f'Type: {goal.goal_type}')
        print(f'User ID: {goal.user_id}')
        desc = getattr(goal, 'description', None)
        print(f'Description: {desc[:50] if desc else "No description"}...')
        print('-' * 30)
        
    print(f'\nTotal goals checked: {len(all_goals)}')
    
finally:
    db.close()
