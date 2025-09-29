import os
from datetime import date, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# -------------------------------
# Initialize Supabase client
# -------------------------------
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)


# -------------------------------
# HABITS FUNCTIONS
# -------------------------------
def create_habit(user_id: str, name: str, description: str = None):
    return supabase.table("habits").insert({
        "user_id": user_id,
        "name": name,
        "description": description
    }).execute()


def get_habits(user_id: str):
    return supabase.table("habits").select("*").eq("user_id", user_id).execute()


def mark_habit_completed(habit_id: str):
    today = date.today().isoformat()
    existing_log = supabase.table("habit_logs") \
        .select("*") \
        .eq("habit_id", habit_id) \
        .eq("date", today) \
        .execute()

    if existing_log.data and len(existing_log.data) > 0:
        log_id = existing_log.data[0]["id"]
        return supabase.table("habit_logs").update({"completed": True}).eq("id", log_id).execute()
    else:
        return supabase.table("habit_logs").insert({
            "habit_id": habit_id,
            "completed": True
        }).execute()


def delete_habit(habit_id: str):
    return supabase.table("habits").delete().eq("habit_id", habit_id).execute()


# -------------------------------
# WEEKLY PERFORMANCE FUNCTIONS
# -------------------------------
def create_weekly_performance_for_user(user_id: str, week_start: date):
    week_end = week_start + timedelta(days=6)

    habits_resp = supabase.table("habits").select("habit_id").eq("user_id", user_id).execute()
    if not habits_resp.data:
        completion_pct = 0
    else:
        habit_ids = [h["habit_id"] for h in habits_resp.data]
        total_expected = len(habit_ids) * 7

        logs_resp = supabase.table("habit_logs").select("*") \
            .in_("habit_id", habit_ids) \
            .gte("date", week_start.isoformat()) \
            .lte("date", week_end.isoformat()) \
            .eq("completed", True) \
            .execute()

        completed_count = len(logs_resp.data) if logs_resp.data else 0
        completion_pct = (completed_count / total_expected) * 100 if total_expected > 0 else 0

    return supabase.table("weekly_performance").insert({
        "user_id": user_id,
        "week_start": week_start.isoformat(),
        "completion_pct": completion_pct
    }).execute()


def get_weekly_performance(user_id: str):
    return supabase.table("weekly_performance").select("*").eq("user_id", user_id).execute()


# -------------------------------
# DAILY STATUS
# -------------------------------
def end_of_day_status(user_id: str):
    today = date.today().isoformat()
    habits_resp = supabase.table("habits").select("*").eq("user_id", user_id).execute()
    if not habits_resp.data:
        return {"message": "No habits found."}

    status_list = []
    for habit in habits_resp.data:
        habit_id = habit["habit_id"]
        logs_resp = supabase.table("habit_logs").select("*") \
            .eq("habit_id", habit_id) \
            .eq("date", today) \
            .execute()
        completed = logs_resp.data[0]["completed"] if logs_resp.data else False
        status_list.append({
            "habit_name": habit["name"],
            "completed": completed
        })
    return {"date": today, "status": status_list}
