# app/scripts/reset_db_data.py
# python -m app.scripts.reset_db_data

from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import (
    Task,
    GoalOccurrence,
    HabitCycle,
    Plan,
    Feedback,
    Goal,
    User,
    ProjectGoal,
    HabitGoal
)

def delete_all_data():
    db: Session = SessionLocal()
    try:
        print("Deleting all records in dependency order...")

        # Delete children first, then parents (bottom-up approach)
        db.query(Task).delete()
        db.query(GoalOccurrence).delete()
        db.query(HabitCycle).delete()
        
        db.query(Feedback).delete()
        db.query(Plan).delete()

        # subclasses of Goal must be deleted before Goal
        db.query(ProjectGoal).delete()
        db.query(HabitGoal).delete()
        db.query(Goal).delete()
        # db.query(User).delete()

        db.commit()
        print("✅ All records deleted successfully.")

    except Exception as e:
        db.rollback()
        print("❌ Error during deletion:", str(e))
    finally:
        db.close()

if __name__ == "__main__":
    delete_all_data()
    
