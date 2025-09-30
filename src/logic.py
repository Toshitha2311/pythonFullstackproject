# src/logic.py
import db
from datetime import date

def add_new_habit(user_id: str, name: str, description: str = None):
    if not user_id:
        user_id = db.ensure_demo_user()
    if not name.strip():
        return {"error": "Habit name cannot be empty."}
    habit_id = db.create_habit(user_id, name.strip(), description)
    if habit_id:
        return {"success": True, "habit_id": habit_id}
    return {"error": "Failed to create habit."}

def list_user_habits(user_id: str):
    if not user_id:
        user_id = db.ensure_demo_user()
    return db.get_habits(user_id)

def complete_habit(habit_id: str):
    return db.mark_habit_completed(habit_id)

def remove_habit(habit_id: str):
    return db.delete_habit(habit_id)

def get_today_status(user_id: str):
    if not user_id:
        user_id = db.ensure_demo_user()
    return db.end_of_day_status(user_id)

def get_my_weekly_performance(user_id: str):
    if not user_id:
        user_id = db.ensure_demo_user()
    return db.get_weekly_performance(user_id)
