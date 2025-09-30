# src/logic.py
import db
from datetime import date

# -------------------------------
# HABIT OPERATIONS
# -------------------------------
def add_new_habit(user_id: str = None, name: str = "", description: str = None):
    """Add a new habit for a user."""
    if not user_id:
        user_id = db.ensure_demo_user()
    if not name or not name.strip():
        return {"error": "Habit name cannot be empty."}
    
    habit_id = db.create_habit(user_id, name.strip(), description)
    if habit_id:
        return {
            "success": True,
            "habit_id": habit_id,
            "message": f"Habit '{name.strip()}' added successfully."
        }
    return {"error": "Failed to create habit."}


def list_user_habits(user_id: str = None):
    """List all habits for a user."""
    if not user_id:
        user_id = db.ensure_demo_user()
    habits = db.get_habits(user_id)
    return habits if habits else []


def complete_habit(habit_id: str):
    """Mark a habit as completed for today."""
    if not habit_id:
        return {"error": "Habit ID is required."}
    return db.mark_habit_completed(habit_id)


def remove_habit(habit_id: str):
    """Delete a habit."""
    if not habit_id:
        return {"error": "Habit ID is required."}
    return db.delete_habit(habit_id)


def get_today_status(user_id: str = None):
    """Return today's status of all habits for a user."""
    if not user_id:
        user_id = db.ensure_demo_user()
    status = db.end_of_day_status(user_id)
    
    # Prepare summary for pie chart
    if "status" in status:
        completed = sum(1 for s in status["status"] if s["completed"])
        total = len(status["status"])
        status["summary"] = {"completed": completed, "total": total}
    return status


def get_my_weekly_performance(user_id: str = None):
    """Return weekly performance for a user."""
    if not user_id:
        user_id = db.ensure_demo_user()
    performance = db.get_weekly_performance(user_id)
    
    # Ensure all keys exist for frontend display
    return {
        "completion_pct": performance.get("completion_pct", 0),
        "stars": performance.get("stars", 0),
        "week_start": str(performance.get("week_start", date.today()))
    }
