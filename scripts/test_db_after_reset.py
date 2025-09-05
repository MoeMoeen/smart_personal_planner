# scripts/test_db_after_reset.py

from sqlalchemy import text
from datetime import date, datetime, timedelta
from app.db.db import SessionLocal
from app import models

db = SessionLocal()

try:
    # 1. Check existing tables
    tables = db.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'")).fetchall()
    print("✅ Tables in DB:", [t[0] for t in tables])

    # 2. Insert a user if not exists
    user = db.query(models.User).filter_by(email="test@example.com").first()
    if not user:
        user = models.User(
            email="test@example.com",
            telegram_user_id=123456789,
            username="test_user",
            first_name="Test",
            last_name="User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    print("👤 User:", user)

    # 3. Create a project goal + plan + task
    goal = db.query(models.Goal).filter_by(title="Learn Python").first()
    if not goal:
        goal = models.Goal(
            title="Learn Python",
            description="Complete Python mastery in 6 months",
            user_id=user.id
        )
        db.add(goal)
        db.commit()
        db.refresh(goal)
    print("🎯 Goal:", goal)

    plan = db.query(models.Plan).filter_by(goal_id=goal.id).first()
    if not plan:
        plan = models.Plan(
            goal_id=goal.id,
            user_id=user.id,
            goal_type=models.GoalType.project,
            start_date=date(2025, 9, 1),
            end_date=date(2026, 3, 1),
            progress=0,
            progress_status=models.ProgressStatus.NOT_STARTED,
            source=models.PlanSource.AI_GENERATED
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)
    print("📝 Plan:", plan)

    task = db.query(models.Task).filter_by(plan_id=plan.id).first()
    if not task:
        task = models.Task(
            user_id=user.id,
            plan_id=plan.id,
            goal_id=goal.id,
            title="Finish Python basics",
            due_date=date(2025, 9, 30),
            status=models.TaskExecutionStatus.TODO,
            completed=False
        )
        db.add(task)
        db.commit()
        db.refresh(task)
    print("✅ Task:", task)

    # 4. Create a habit goal + plan + cycle + occurrence
    habit_goal = db.query(models.Goal).filter_by(title="Daily Meditation").first()
    if not habit_goal:
        habit_goal = models.Goal(
            title="Daily Meditation",
            description="Practice meditation 10 minutes daily",
            user_id=user.id
        )
        db.add(habit_goal)
        db.commit()
        db.refresh(habit_goal)
    print("🧘 Habit Goal:", habit_goal)

    habit_plan = db.query(models.Plan).filter_by(goal_id=habit_goal.id).first()
    if not habit_plan:
        habit_plan = models.Plan(
            goal_id=habit_goal.id,
            user_id=user.id,
            goal_type=models.GoalType.habit,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 31),
            progress=0,
            progress_status=models.ProgressStatus.NOT_STARTED,
            recurrence_cycle=models.RecurrenceCycle.DAILY,
            goal_frequency_per_cycle=1,
            goal_recurrence_count=30,
            source=models.PlanSource.MANUAL_CREATED
        )
        db.add(habit_plan)
        db.commit()
        db.refresh(habit_plan)
    print("📆 Habit Plan:", habit_plan)

    cycle = db.query(models.HabitCycle).filter_by(plan_id=habit_plan.id).first()
    if not cycle:
        cycle = models.HabitCycle(
            goal_id=habit_goal.id,
            user_id=user.id,
            plan_id=habit_plan.id,
            cycle_label="2025-09",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 9, 30),
            progress=0
        )
        db.add(cycle)
        db.commit()
        db.refresh(cycle)
    print("🔄 Cycle:", cycle)

    occurrence = db.query(models.GoalOccurrence).filter_by(cycle_id=cycle.id).first()
    if not occurrence:
        occurrence = models.GoalOccurrence(
            user_id=user.id,
            cycle_id=cycle.id,
            plan_id=habit_plan.id,
            occurrence_order=1,
            completed=False
        )
        db.add(occurrence)
        db.commit()
        db.refresh(occurrence)
    print("📍 Occurrence:", occurrence)

    # 5. Create a scheduled task (execution layer)
    scheduled = db.query(models.ScheduledTask).filter_by(task_id=task.id).first()
    if not scheduled:
        scheduled = models.ScheduledTask(
            user_id=user.id,
            goal_id=goal.id,
            plan_id=plan.id,
            task_id=task.id,
            start_datetime=datetime.utcnow(),
            end_datetime=datetime.utcnow() + timedelta(hours=1),
            estimated_minutes=60,
            title="Finish Python basics (scheduled)",
            priority=1,
            tags=["python", "study"],
            notes="Dummy scheduled task for validation",
            status=models.ScheduledTaskStatus.SCHEDULED
        )
        db.add(scheduled)
        db.commit()
        db.refresh(scheduled)
    print("📅 ScheduledTask:", scheduled)

    # 5b. Create a dedicated task for the habit occurrence
    habit_task = (
        db.query(models.Task)
        .filter_by(plan_id=habit_plan.id, title="Meditate 10 minutes")
        .first()
    )
    if not habit_task:
        habit_task = models.Task(
            user_id=user.id,
            plan_id=habit_plan.id,
            title="Meditate 10 minutes",
            due_date=date(2025, 9, 1),
            status=models.TaskExecutionStatus.TODO,
            completed=False,
            goal_id=habit_goal.id,
            cycle_id=cycle.id,
            occurrence_id=occurrence.id
        )
        db.add(habit_task)
        db.commit()
        db.refresh(habit_task)
    print("✅ Habit Task:", habit_task)

    # 6. Scheduled task for the habit occurrence (execution layer)
    habit_scheduled = (
        db.query(models.ScheduledTask)
        .filter_by(plan_id=habit_plan.id, occurrence_id=occurrence.id)
        .first()
    )
    if not habit_scheduled:
        habit_scheduled = models.ScheduledTask(
            user_id=user.id,
            goal_id=habit_goal.id,
            plan_id=habit_plan.id,
            task_id=habit_task.id,  # 👈 now linked to habit-specific task
            cycle_id=cycle.id,
            occurrence_id=occurrence.id,
            start_datetime=datetime(2025, 9, 1, 7, 0),   # 7 AM meditation
            end_datetime=datetime(2025, 9, 1, 7, 10),    # 10 minutes later
            estimated_minutes=10,
            title="Meditate for 10 minutes",
            priority=2,
            tags=["meditation", "habit"],
            notes="Scheduled occurrence for daily meditation",
            status=models.ScheduledTaskStatus.SCHEDULED
        )
        db.add(habit_scheduled)
        db.commit()
        db.refresh(habit_scheduled)
    print("🕊️ Habit ScheduledTask:", habit_scheduled)

    # 7. Print full summary
    print("📌 User goals:", user.goals)
    print("📌 Goal plans:", goal.plans)
    print("📌 Habit plans:", habit_goal.plans)
    print("📌 Habit cycles:", habit_plan.cycles)
    print("📌 Cycle occurrences:", cycle.occurrences)
    print("📌 Project scheduled tasks:", plan.scheduled_tasks)
    print("📌 Habit scheduled tasks:", habit_plan.scheduled_tasks)
    

finally:
    db.close()