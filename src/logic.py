# src/logic.py
import random
from src.db import (
    create_habit,
    get_habits,
    mark_habit_completed,
    delete_habit,
    get_weekly_performance,
    end_of_day_status
)

# -------------------------------
# CLASS: Habits
# -------------------------------
class Habits:
    """Class to manage habits table operations."""

    def __init__(self):
        """Constructor: placeholder for future (DB connection, etc.)."""
        pass

    def add(self, name: str, description: str = None):
        if not name or name.strip() == "":
            return {"success": False, "message": "Enter the habit name"}
        result = create_habit(name.strip(), description)
        if result.get("data"):
            return {"success": True, "message": f"Habit '{name}' added successfully."}
        else:
            return {"success": False, "message": f"Error: {result.get('error') or 'Unknown error'}"}

    def list(self):
        result = get_habits()
        if not result or not result.get("data"):
            return {"success": True, "habits": [], "message": "No habits found."}
        return {"success": True, "habits": result["data"]}

    def complete(self, name: str):
        if not name or name.strip() == "":
            return {"success": False, "message": "Habit name is required."}
        result = mark_habit_completed(name.strip())
        if result.get("data"):
            return {"success": True, "message": f"Habit '{name}' marked as completed today! ✅"}
        else:
            return {"success": False, "message": f"Error: {result.get('error') or 'Unknown error'}"}

    def remove(self, name: str):
        if not name or name.strip() == "":
            return {"success": False, "message": "Habit name is required."}
        result = delete_habit(name.strip())
        if result.get("data"):
            return {"success": True, "message": f"Habit '{name}' removed successfully."}
        else:
            return {"success": False, "message": f"Error: {result.get('error') or 'Unknown error'}"}


# -------------------------------
# CLASS: HabitLogs
# -------------------------------
class HabitLogs:
    """Class to manage habit_logs table operations."""

    def __init__(self):
        """Constructor for HabitLogs class."""
        self.habits = Habits()

    def complete(self, habit_name: str):
        """Mark habit completed today using habit name."""
        return self.habits.complete(habit_name)

    def status(self):
        """Return end-of-day status with funny motivational quotes."""
        result = end_of_day_status()
        if not result:
            return {"success": False, "message": "Could not fetch end-of-day status."}

        completed_count = result.get("completed_count", 0)
        total_habits = len(get_habits().get("data", []))

        QUOTES_COMPLETED = [
            "You crushed it today! 💪 Even your coffee is proud!",
            "Amazing! 🎉 Keep this streak alive, superstar!",
            "Well done! 🏆 Your habits fear you now!",
            "Keep shining! ✨ You're a habit hero!",
            "Woohoo! 🎊 Success tastes better than snacks!",
            "Legendary! 🦸‍♂️ Keep flexing those productivity muscles!",
            "Fantastic! 🌟 Today's you is better than yesterday's!",
        ]

        QUOTES_NOT_COMPLETED = [
            "Oops! 😅 No habits completed. Tomorrow’s a new adventure!",
            "Don't worry! 🐢 Slow progress is still progress!",
            "Hey! 🎈 Tomorrow is waiting for your comeback!",
            "No sweat! 🌞 Every master was once a beginner!",
            "Keep smiling 😁 The grind continues tomorrow!",
            "Oopsie! 🍩 Treat yourself and try again tomorrow!",
            "Remember: 🚀 Even astronauts had training days off!",
        ]

        if completed_count == 0:
            quote = random.choice(QUOTES_NOT_COMPLETED)
            status = "not_completed"
            message = f"{quote} (0/{total_habits} habits completed today)"
        else:
            quote = random.choice(QUOTES_COMPLETED)
            status = "completed"
            message = f"{quote} ({completed_count}/{total_habits} habits completed today)"

        return {
            "success": True,
            "status": status,
            "message": message,
            "completed_count": completed_count
        }


# -------------------------------
# CLASS: WeeklyPerformance
# -------------------------------
class WeeklyPerformance:
    """Class to manage weekly_performance table operations."""

    def __init__(self):
        """Constructor for WeeklyPerformance class."""
        pass

    def get_report(self):
        """Return weekly performance for the current user."""
        result = get_weekly_performance()
        if not result or not result.get("data"):
            return {"success": True, "weekly_report": [], "message": "No weekly performance found."}
        return {"success": True, "weekly_report": result["data"]}
