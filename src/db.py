import os
from datetime import date, timedelta
from supabase import create_client
from dotenv import load_dotenv
import requests
import random

load_dotenv()

# -------------------------------
# Initialize Supabase client
# -------------------------------
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# -------------------------------
# USER UTILITY
# -------------------------------
def get_current_user_id():
    """Returns the currently logged-in user's UUID from Supabase Auth."""
    session = supabase.auth.get_session()
    if session.user:
        return session.user.id
    return None

# -------------------------------
# HABITS FUNCTIONS (NAME-BASED)
# -------------------------------
def create_habit(name: str, description: str = None):
    """Creates a habit for the current user."""
    user_id = get_current_user_id()
    if not user_id or not name or name.strip() == "":
        return {"data": [], "error": "Invalid habit name or user not logged in"}

    return supabase.table("habits").insert({
        "user_id": user_id,
        "name": name.strip(),
        "description": description
    }).execute()


def get_habits():
    """Fetch all habits for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return {"data": [], "error": "User not logged in"}
    return supabase.table("habits").select("*").eq("user_id", user_id).execute()


def get_habit_by_name(name: str):
    """Fetch habit by name for current user."""
    user_id = get_current_user_id()
    if not user_id or not name or name.strip() == "":
        return {"data": []}
    return supabase.table("habits").select("*") \
        .eq("user_id", user_id) \
        .eq("name", name.strip()) \
        .execute()


def mark_habit_completed(name: str):
    """Marks a habit as completed today using habit name."""
    habit_resp = get_habit_by_name(name)
    if not habit_resp or not habit_resp.data or len(habit_resp.data) == 0:
        return {"data": [], "error": "Habit not found"}

    habit_id = habit_resp.data[0]["habit_id"]
    today = date.today().isoformat()

    existing_log = supabase.table("habit_logs").select("*") \
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


def delete_habit(name: str):
    """Deletes a habit and its logs using habit name."""
    habit_resp = get_habit_by_name(name)
    if not habit_resp or not habit_resp.data or len(habit_resp.data) == 0:
        return {"data": [], "error": "Habit not found"}

    habit_id = habit_resp.data[0]["habit_id"]
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

    return supabase.table("weekly_performance").insert({
        "user_id": user_id,
        "week_start": week_start.isoformat(),
        "completion_pct": completion_pct
    }).execute()


def generate_weekly_reports_for_all_users():
    """Generates weekly performance for all users (run only on Sunday)."""
    today = date.today()
    if today.weekday() != 6:
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


def trigger_weekly_report_edge_function():
    """Call Supabase Edge Function for weekly report (optional)."""
    edge_function_url = os.getenv("SUPABASE_EDGE_WEEKLY_REPORT_URL")
    if not edge_function_url:
        return None
    response = requests.post(edge_function_url)
    return response.json()


# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def get_weekly_performance():
    """Fetch weekly performance for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return {"data": [], "error": "User not logged in"}
    return supabase.table("weekly_performance").select("*").eq("user_id", user_id).execute()


def get_habits_with_logs():
    """Fetch all habits along with their logs for current user."""
    user_id = get_current_user_id()
    if not user_id:
        return {"data": [], "error": "User not logged in"}
    return supabase.table("habits").select("*, habit_logs(*)").eq("user_id", user_id).execute()


def end_of_day_status():
    """Returns end-of-day status with funny motivational quotes and completed count."""
    habits_resp = get_habits_with_logs()
    if not habits_resp or not habits_resp.data:
        return {
            "status": "No habits",
            "message": "You have no habits today. 🤷‍♂️ Time to chill! 🍿",
            "completed_count": 0
        }

    completed = 0
    for habit in habits_resp.data:
        logs = habit.get("habit_logs", [])
        for log in logs:
            if log.get("completed"):
                completed += 1

    total = len(habits_resp.data)

    # Funny motivational quotes
    completed_quotes = [
    "Amazing! You crushed it today! 🎉💪",
    "Well done! Keep the streak alive! 🏆🔥",
    "You're unstoppable! 😎✨",
    "Cheers! Another day, another victory! 🍀🏅",
    "You did it! Go you! 🐱‍🏍🥳",
    "You crushed it today! 💪 Time to reward yourself with a cookie 🍪… or two.",
    "Wow! You’re basically a habit ninja 🥷 Keep slashing those goals!",
    "Congratulations! You did a thing! 🎉 Even small things count… like drinking water today 💧",
    "Look at you go! 🏎️ Faster than your morning coffee ☕",
    "You completed your habits! 🎯 The world is not ready for your awesomeness 😎",
    "High five! ✋ You’re officially the CEO of ‘Getting Stuff Done’ 🏆",
    "Amazing! 🌟 Even your pet thinks you’re impressive 🐶🐱"
    ]

    not_completed_quotes = [
    "Oops! Nobody’s perfect 😅🛌",
    "Tomorrow is another chance! 🌞💤",
    "Keep trying! Rome wasn’t built in a day! 🏛️😂",
    "No habits today? Well, enjoy the free time! 🍿😎",
    "Oops! Today was a plot twist 😅 Let’s try again tomorrow!",
    "Don’t worry, even superheroes have off days 🦸‍♂️ Rest up and come back stronger 💥",
    "Today didn’t go as planned… But hey, tomorrow is full of possibilities 🌈",
    "Nobody’s perfect! Even the best need a snooze button sometimes 😴",
    "Don’t cry because you didn’t complete your habits 😢 Laugh because you still have another chance tomorrow 😎",
    "You didn’t win today… but at least you survived! 🥳 Try again tomorrow!",
    "Failed habits? Pfft. You’re just collecting funny stories to tell later 😂"
    ]


    if completed == 0:
        message = f"You completed 0/{total} habits today. {random.choice(not_completed_quotes)}"
    else:
        message = f"You completed {completed}/{total} habits today! {random.choice(completed_quotes)}"

    return {
        "status": "done",
        "message": message,
        "completed_count": completed
    }
