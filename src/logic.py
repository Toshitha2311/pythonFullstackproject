# logic.py
import db
from datetime import date

def add_new_habit(user_id: str, name: str, description: str = None):
    if not name or not name.strip():
        return {"error": "Habit name cannot be empty"}
    return db.create_habit(user_id, name.strip(), description)


def list_user_habits(user_id: str):
    resp = db.get_habits(user_id)
    return resp.data if resp and resp.data else []


def complete_habit(habit_id: str):
    if not habit_id:
        return {"error": "Habit ID is required"}
    return db.mark_habit_completed(habit_id)


def remove_habit(habit_id: str):
    if not habit_id:
        return {"error": "Habit ID is required"}
    return db.delete_habit(habit_id)


def get_today_status(user_id: str):
    return db.end_of_day_status(user_id)


def get_my_weekly_performance(user_id: str):
    resp = db.get_weekly_performance(user_id)
    return resp.data if resp and resp.data else []


def generate_weekly_performance(user_id: str):
    today = date.today()
    if today.weekday() != 6:
        return {"error": "Weekly performance can only be generated on Sundays."}
    return db.create_weekly_performance_for_user(user_id, today)
