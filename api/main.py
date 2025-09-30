# api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
import logic
import db

app = FastAPI(title="HabitHub API")

# -------------------------------
# MODELS
# -------------------------------
class HabitAddModel(BaseModel):
    name: str
    description: str | None = None

class HabitIDModel(BaseModel):
    habit_id: str

# -------------------------------
# HABIT ROUTES
# -------------------------------
@app.post("/habit/add")
def add_habit(habit: HabitAddModel):
    return logic.add_new_habit(None, habit.name, habit.description)

@app.get("/habit/list")
def list_habits():
    return {"habits": logic.list_user_habits(None)}

@app.post("/habit/complete")
def complete_habit(h: HabitIDModel):
    return logic.complete_habit(h.habit_id)

@app.post("/habit/remove")
def remove_habit(h: HabitIDModel):
    return logic.remove_habit(h.habit_id)

@app.get("/habit/status")
def habit_status():
    return logic.get_today_status(None)

@app.get("/weekly/report")
def weekly_report():
    return logic.get_my_weekly_performance(None)

# -------------------------------
# APScheduler Tasks
# -------------------------------
scheduler = BackgroundScheduler()

def daily_task():
    """
    Generate daily logs for all habits at the start of the day
    """
    users_resp = db.supabase.table("users").select("user_id").execute()
    if users_resp.data:
        for u in users_resp.data:
            user_id = u["user_id"]
            habits = logic.list_user_habits(user_id)
            today = date.today().isoformat()
            for h in habits:
                # Check if today's log exists
                logs = db.supabase.table("habit_logs").select("*").eq("habit_id", h["habit_id"]).eq("date", today).execute()
                if not logs.data:
                    db.supabase.table("habit_logs").insert({
                        "habit_id": h["habit_id"],
                        "user_id": user_id,
                        "completed": False
                    }).execute()

def weekly_task():
    """
    Calculate weekly performance for all users on Sunday
    """
    if datetime.today().weekday() == 6:  # Sunday
        users_resp = db.supabase.table("users").select("user_id").execute()
        if users_resp.data:
            for u in users_resp.data:
                logic.get_my_weekly_performance(u["user_id"])

# Schedule daily log generation at 00:01
scheduler.add_job(daily_task, 'cron', hour=0, minute=1)
# Schedule weekly performance calculation at Sunday 23:59
scheduler.add_job(weekly_task, 'cron', day_of_week='sun', hour=23, minute=59)
scheduler.start()
