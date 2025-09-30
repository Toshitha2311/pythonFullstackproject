# src/db.py
import os
import uuid
from datetime import date, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------
# USERS
# -------------------------------
def ensure_demo_user():
    """Return an existing demo user or create one."""
    resp = supabase.table("users").select("*").limit(1).execute()
    if resp.data:
        return resp.data[0]["user_id"]
    # Insert a new user with auto-generated ID (via sequence)
    resp = supabase.table("users").insert({}).execute()
    return resp.data[0]["user_id"] if resp.data else None

# -------------------------------
# HABITS
# -------------------------------
def create_habit(user_id: str, name: str, description: str = None):
    payload = {"user_id": user_id, "name": name}
    if description:
        payload["description"] = description
    resp = supabase.table("habits").insert(payload).execute()
    if resp.data:
        habit_id = resp.data[0]["habit_id"]
        # Create today's log
        supabase.table("habit_logs").insert({
            "habit_id": habit_id,
            "user_id": user_id,
            "completed": False
        }).execute()
        # Update weekly performance
        update_weekly_performance(user_id)
        return habit_id
    return None

def get_habits(user_id: str):
    resp = supabase.table("habits").select("*").eq("user_id", user_id).execute()
    return resp.data if resp.data else []

def mark_habit_completed(habit_id: str):
    today = date.today().isoformat()
    logs = supabase.table("habit_logs").select("*").eq("habit_id", habit_id).eq("date", today).execute()
    if logs.data:
        log_id = logs.data[0]["log_id"]
        supabase.table("habit_logs").update({"completed": True}).eq("log_id", log_id).execute()
        # Update weekly performance
        user_id = logs.data[0]["user_id"]
        update_weekly_performance(user_id)
        return {"updated": True, "log_id": log_id}
    else:
        user_id = get_user_id_from_habit(habit_id)
        resp = supabase.table("habit_logs").insert({
            "habit_id": habit_id,
            "user_id": user_id,
            "completed": True
        }).execute()
        if resp.data:
            update_weekly_performance(user_id)
            return {"created": True, "log_id": resp.data[0]["log_id"]}
    return {"error": "Failed to mark completed."}

def delete_habit(habit_id: str):
    habit = supabase.table("habits").select("*").eq("habit_id", habit_id).execute()
    if habit.data:
        user_id = habit.data[0]["user_id"]
        supabase.table("habit_logs").delete().eq("habit_id", habit_id).execute()
        supabase.table("habits").delete().eq("habit_id", habit_id).execute()
        update_weekly_performance(user_id)
        return {"deleted": True, "habit_id": habit_id}
    return {"error": "Habit not found."}

def get_user_id_from_habit(habit_id: str):
    resp = supabase.table("habits").select("user_id").eq("habit_id", habit_id).execute()
    if resp.data:
        return resp.data[0]["user_id"]
    return None

# -------------------------------
# WEEKLY PERFORMANCE
# -------------------------------
def update_weekly_performance(user_id: str):
    supabase.rpc("update_weekly_performance_for_user", {"uid": user_id}).execute()

def get_weekly_performance(user_id: str):
    resp = supabase.table("weekly_performance").select("*").eq("user_id", user_id).execute()
    return resp.data[0] if resp.data else {"completion_pct": 0, "stars": 0}

# -------------------------------
# DAILY STATUS
# -------------------------------
def end_of_day_status(user_id: str):
    habits = get_habits(user_id)
    today = date.today().isoformat()
    status_list = []
    for h in habits:
        logs = supabase.table("habit_logs").select("*").eq("habit_id", h["habit_id"]).eq("date", today).execute()
        completed = logs.data[0]["completed"] if logs.data else False
        status_list.append({"habit_name": h["name"], "completed": completed})
    return {"date": today, "status": status_list}
