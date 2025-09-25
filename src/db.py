# db_manager.py
import os
from datetime import date, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
import requests

load_dotenv()

# -------------------------------
# Initialize Supabase client
# -------------------------------
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# -------------------------------
# USER ID UTILITY
# -------------------------------
def get_current_user_id():
    """Returns the currently logged-in user's UUID from Supabase Auth."""
    session = supabase.auth.get_session()
    if session.user:
        return session.user.id
    return None

# -------------------------------
# HABITS FUNCTIONS
# -------------------------------
def create_habit(name: str, description: str = None):
    user_id = get_current_user_id()
    return supabase.table("habits").insert({
        "user_id": user_id,
        "name": name,
        "description": description
    }).execute()

def get_habits():
    user_id = get_current_user_id()
    return supabase.table("habits").select("*").eq("user_id", user_id).execute()

def mark_habit_completed(habit_id: str):
    """Marks a habit as completed for today."""
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
    """
    Deletes a habit and all its associated logs automatically (ON DELETE CASCADE).
    """
    return supabase.table("habits").delete().eq("habit_id", habit_id).execute()

# -------------------------------
# WEEKLY PERFORMANCE FUNCTIONS
# -------------------------------
def create_weekly_performance_for_user(user_id: str, week_start: date):
    """Calculates completion_pct automatically and inserts weekly performance."""
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

    # Insert weekly performance record; stars set by DB trigger
    return supabase.table("weekly_performance").insert({
        "user_id": user_id,
        "week_start": week_start.isoformat(),
        "completion_pct": completion_pct
    }).execute()

# -------------------------------
# AUTOMATIC WEEKLY REPORTS
# -------------------------------
def generate_weekly_reports_for_all_users():
    """
    Automatically generates weekly performance for all users.
    Should run every Sunday (via cron or Supabase Edge Function).
    """
    today = date.today()
    if today.weekday() != 6:  # Only run on Sunday
        return None

    week_start = today - timedelta(days=today.weekday())

    users_resp = supabase.table("auth.users").select("id").execute()
    if not users_resp.data:
        return None

    results = []
    for user in users_resp.data:
        user_id = user["id"]
        res = create_weekly_performance_for_user(user_id, week_start)
        results.append(res)
    
    return results

# -------------------------------
# EDGE FUNCTION CALL (Optional)
# -------------------------------
def trigger_weekly_report_edge_function():
    """
    Call the Supabase Edge Function to generate weekly reports.
    Useful if you want serverless automatic execution.
    """
    
    edge_function_url = os.getenv("SUPABASE_EDGE_WEEKLY_REPORT_URL")
    if not edge_function_url:
        return None
    response = requests.post(edge_function_url)
    return response.json()

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def get_weekly_performance():
    user_id = get_current_user_id()
    return supabase.table("weekly_performance").select("*").eq("user_id", user_id).execute()

def get_habits_with_logs():
    user_id = get_current_user_id()
    return supabase.table("habits").select("*, habit_logs(*)").eq("user_id", user_id).execute()
