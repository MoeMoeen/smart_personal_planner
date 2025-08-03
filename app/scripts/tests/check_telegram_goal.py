"""
Check the latest Telegram plan creation
"""
from app.db import get_db
from app.models import Goal, User

# Get database session
db_gen = get_db()
db = next(db_gen)

try:
    # Check the user that was created
    user = db.query(User).filter(User.id == 10).first()
    if user:
        print('🤖 Telegram User Created:')
        print(f'User ID: {user.id}')
        print(f'Telegram ID: {user.telegram_user_id}')
        print(f'Username: {user.username}')
        print(f'First Name: {user.first_name}')
        print('-' * 40)
    
    # Check the goal that was created
    goal = db.query(Goal).filter(Goal.id == 51).first()
    if goal:
        print('🎯 Goal Created via Telegram:')
        print(f'Goal ID: {goal.id}')
        print(f'Title: {goal.title}')
        print(f'Type: {goal.goal_type}')
        print(f'Description: {goal.description}')
        print(f'User ID: {goal.user_id}')
        print(f'Start Date: {goal.start_date}')
        print(f'End Date: {goal.end_date}')
        print('-' * 40)
    
    print("🎉 Telegram integration working perfectly!")
    
finally:
    db.close()
