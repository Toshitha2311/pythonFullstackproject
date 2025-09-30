# src/db.py
import os
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
    try:
        resp = supabase.table("users").select("*").limit(1).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]["user_id"]
        # Insert a new user with auto-generated ID
        resp = supabase.table("users").insert({}).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]["user_id"]
    except Exception as e:
        print("Error in ensure_demo_user:", e)
    raise Exception("Failed to create or get demo user")

# -------------------------------
# HABITS
# -------------------------------
def create_habit(user_id: str, name: str, description: str = None):
    try:
        if not user_id:
            user_id = ensure_demo_user()
        payload = {"user_id": user_id, "name": name}
        if description:
            payload["description"] = description

        resp = supabase.table("habits").insert(payload).execute()
        if not resp.data or "habit_id" not in resp.data[0]:
            raise Exception("Failed to insert habit")
        
        habit_id = resp.data[0]["habit_id"]

        # Create today's log
        supabase.table("habit_logs").insert({
            "habit_id": habit_id,
            "user_id": user_id,
            "completed": False
        }).execute()

        # Update weekly performance only on Sunday
        today = date.today()
        if today.weekday() == 6:  # Sunday
            update_weekly_performance(user_id)

        return habit_id
    except Exception as e:
        print("Error in create_habit:", e)
        return None

def get_habits(user_id: str):
    try:
        resp = supabase.table("habits").select("*").eq("user_id", user_id).execute()
        return resp.data if resp.data else []
    except Exception as e:
        print("Error in get_habits:", e)
        return []

def mark_habit_completed(habit_id: str):
    today = date.today().isoformat()
    try:
        logs = supabase.table("habit_logs").select("*").eq("habit_id", habit_id).eq("date", today).execute()
        user_id = get_user_id_from_habit(habit_id)
        if logs.data and len(logs.data) > 0:
            log_id = logs.data[0]["log_id"]
            supabase.table("habit_logs").update({"completed": True}).eq("log_id", log_id).execute()
        else:
            resp = supabase.table("habit_logs").insert({
                "habit_id": habit_id,
                "user_id": user_id,
                "completed": True
            }).execute()
            log_id = resp.data[0]["log_id"] if resp.data else None

        # Update weekly performance only on Sunday
        today_obj = date.today()
        if today_obj.weekday() == 6 and user_id:
            update_weekly_performance(user_id)

        return {"habit_id": habit_id, "log_id": log_id}
    except Exception as e:
        print("Error in mark_habit_completed:", e)
        return {"error": "Failed to mark completed."}

def delete_habit(habit_id: str):
    try:
        habit = supabase.table("habits").select("*").eq("habit_id", habit_id).execute()
        if habit.data and len(habit.data) > 0:
            user_id = habit.data[0]["user_id"]
            supabase.table("habit_logs").delete().eq("habit_id", habit_id).execute()
            supabase.table("habits").delete().eq("habit_id", habit_id).execute()

            # Update weekly performance only on Sunday
            if date.today().weekday() == 6:
                update_weekly_performance(user_id)

            return {"deleted": True, "habit_id": habit_id}
        return {"error": "Habit not found."}
    except Exception as e:
        print("Error in delete_habit:", e)
        return {"error": "Failed to delete habit."}

def get_user_id_from_habit(habit_id: str):
    try:
        resp = supabase.table("habits").select("user_id").eq("habit_id", habit_id).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0]["user_id"]
    except Exception as e:
        print("Error in get_user_id_from_habit:", e)
    return None

# -------------------------------
# WEEKLY PERFORMANCE
# -------------------------------
def update_weekly_performance(user_id: str):
    try:
        supabase.rpc("update_weekly_performance_for_user", {"uid": user_id}).execute()
    except Exception as e:
        print("Error in update_weekly_performance:", e)

def get_weekly_performance(user_id: str):
    try:
        resp = supabase.table("weekly_performance").select("*").eq("user_id", user_id).execute()
        return resp.data[0] if resp.data else {"completion_pct": 0, "stars": 0, "week_start": str(date.today())}
    except Exception as e:
        print("Error in get_weekly_performance:", e)
        return {"completion_pct": 0, "stars": 0, "week_start": str(date.today())}

# -------------------------------
# DAILY STATUS
# -------------------------------
def end_of_day_status(user_id: str):
    try:
        habits = get_habits(user_id)
        today = date.today().isoformat()
        status_list = []
        for h in habits:
            logs = supabase.table("habit_logs").select("*").eq("habit_id", h["habit_id"]).eq("date", today).execute()
            completed = logs.data[0]["completed"] if logs.data else False
            status_list.append({"habit_name": h["name"], "completed": completed})
        return {"date": today, "status": status_list}
    except Exception as e:
        print("Error in end_of_day_status:", e)
        return {"error": "Failed to fetch today's status"}
