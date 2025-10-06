from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, date
import sys, os
import hashlib
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
import logic
import db

app = FastAPI(title="HabitHub API")

# -------------------------------
# PASSWORD HELPER
# -------------------------------
def hash_password(password: str) -> str:
    """Simple password hashing"""
    return hashlib.sha256(password.encode()).hexdigest()

# -------------------------------
# MODELS
# -------------------------------
class UserRegisterModel(BaseModel):
    name: str
    email: str
    password: str

class UserLoginModel(BaseModel):
    email: str
    password: str

class HabitAddModel(BaseModel):
    name: str
    description: str | None = None
    user_id: str

class HabitIDModel(BaseModel):
    habit_id: str
    user_id: str

class UserIDModel(BaseModel):
    user_id: str

# -------------------------------
# AUTH ROUTES
# -------------------------------
@app.post("/auth/register")
def register_user(user: UserRegisterModel):
    try:
        # Check if user already exists
        existing = db.supabase.table("users").select("*").eq("email", user.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="User already exists with this email")
        
        # Create user with hashed password
        user_data = {
            "name": user.name,
            "email": user.email,
            "password": hash_password(user.password),
            "created_at": datetime.now().isoformat()
        }
        
        result = db.supabase.table("users").insert(user_data).execute()
        if result.data:
            return {
                "success": True, 
                "user_id": result.data[0]["user_id"], 
                "name": result.data[0]["name"],
                "message": "Registration successful"
            }
        else:
            raise HTTPException(status_code=500, detail="Registration failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration error: {str(e)}")

@app.post("/auth/login")
def login_user(user: UserLoginModel):
    try:
        hashed_password = hash_password(user.password)
        result = db.supabase.table("users").select("*").eq("email", user.email).eq("password", hashed_password).execute()
        
        if result.data:
            user_data = result.data[0]
            return {
                "success": True, 
                "user_id": user_data["user_id"], 
                "name": user_data["name"],
                "message": "Login successful"
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid email or password")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login error: {str(e)}")

# -------------------------------
# HABIT ROUTES
# -------------------------------
@app.post("/habit/add")
def add_habit(habit: HabitAddModel):
    try:
        habit_data = {
            "name": habit.name,
            "description": habit.description,
            "user_id": habit.user_id,
            "created_at": datetime.now().isoformat()
        }
        
        result = db.supabase.table("habits").insert(habit_data).execute()
        
        if result.data:
            # Create today's log for the new habit
            today = date.today().isoformat()
            log_data = {
                "habit_id": result.data[0]["habit_id"],
                "user_id": habit.user_id,
                "date": today,
                "completed": False
            }
            db.supabase.table("habit_logs").insert(log_data).execute()
            
            return {
                "success": True,
                "habit_id": result.data[0]["habit_id"],
                "message": "Habit added successfully"
            }
        else:
            return {"success": False, "error": "Failed to add habit"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/habit/list")
def list_habits(user: UserIDModel):
    try:
        result = db.supabase.table("habits").select("*").eq("user_id", user.user_id).execute()
        return {"success": True, "habits": result.data}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/habit/complete")
def complete_habit(h: HabitIDModel):
    try:
        # Update habit log for today
        today = date.today().isoformat()
        result = db.supabase.table("habit_logs")\
            .update({"completed": True})\
            .eq("habit_id", h.habit_id)\
            .eq("user_id", h.user_id)\
            .eq("date", today)\
            .execute()
        
        return {"success": True, "message": "Habit completed successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/habit/remove")
def remove_habit(h: HabitIDModel):
    try:
        # Remove habit and its logs
        db.supabase.table("habit_logs").delete().eq("habit_id", h.habit_id).execute()
        db.supabase.table("habits").delete().eq("habit_id", h.habit_id).execute()
        
        return {"success": True, "message": "Habit removed successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/habit/today-status")
def today_status(user: UserIDModel):
    try:
        user_id = user.user_id
        today = date.today().isoformat()
        
        # Get today's habits with completion status
        result = db.supabase.table("habit_logs")\
            .select("*, habits(name, description)")\
            .eq("user_id", user_id)\
            .eq("date", today)\
            .execute()
        
        habits = []
        total_habits = 0
        completed_habits = 0
        
        for log in result.data:
            total_habits += 1
            completed = log.get('completed', False)
            if completed:
                completed_habits += 1
            
            habits.append({
                "habit_id": log["habit_id"],
                "name": log["habits"]["name"],
                "description": log["habits"].get("description"),
                "completed": completed
            })
        
        return {
            "success": True,
            "total_habits": total_habits,
            "completed_habits": completed_habits,
            "habits": habits
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/weekly/report")
def weekly_report(user: UserIDModel):
    try:
        # Calculate weekly performance (simplified version)
        today = date.today()
        start_of_week = today  # Simplified - in real app, calculate week start
        
        result = db.supabase.table("habit_logs")\
            .select("completed")\
            .eq("user_id", user.user_id)\
            .gte("date", start_of_week.isoformat())\
            .execute()
        
        total_logs = len(result.data)
        completed_logs = sum(1 for log in result.data if log.get('completed', False))
        
        completion_pct = (completed_logs / total_logs * 100) if total_logs > 0 else 0
        stars = min(5, int(completion_pct / 20))  # 5 stars for 100%
        
        return {
            "success": True,
            "completion_pct": round(completion_pct, 1),
            "stars": stars,
            "total_habits": total_logs,
            "completed_habits": completed_logs
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# -------------------------------
# APScheduler Tasks
# -------------------------------
scheduler = BackgroundScheduler()

def daily_task():
    """
    Generate daily logs for all habits at the start of the day
    """
    try:
        users_resp = db.supabase.table("users").select("user_id").execute()
        if users_resp.data:
            for u in users_resp.data:
                user_id = u["user_id"]
                habits_resp = db.supabase.table("habits").select("habit_id").eq("user_id", user_id).execute()
                habits = habits_resp.data
                today = date.today().isoformat()
                for h in habits:
                    # Check if today's log exists
                    logs = db.supabase.table("habit_logs").select("*").eq("habit_id", h["habit_id"]).eq("date", today).execute()
                    if not logs.data:
                        db.supabase.table("habit_logs").insert({
                            "habit_id": h["habit_id"],
                            "user_id": user_id,
                            "date": today,
                            "completed": False
                        }).execute()
    except Exception as e:
        print(f"Daily task error: {e}")


def weekly_task():
    """
    Calculate weekly performance for all users on Sunday
    """
    try:
        if datetime.today().weekday() == 6:  # Sunday
            users_resp = db.supabase.table("users").select("user_id").execute()
            if users_resp.data:
                for u in users_resp.data:
                    # Calculate weekly performance
                    user_id = u['user_id']
                    weekly_performance = calculate_weekly_performance(user_id)
                    
                    # Store weekly report
                    store_weekly_report(user_id, weekly_performance)
                    print(f"Weekly performance calculated for user {user_id}: {weekly_performance}")
    except Exception as e:
        print(f"Weekly task error: {e}")

def calculate_weekly_performance(user_id):
    """Calculate weekly performance for a user"""
    try:
        # Get habits from last 7 days
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        weekly_habits = []
        total_habits = 0
        completed_habits = 0
        
        # Load habit history from JSON files
        current_date = start_date
        while current_date <= end_date:
            history_file = f"habit_history_{current_date.strftime('%Y%m%d')}.json"
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    day_data = json.load(f)
                    user_day_habits = day_data.get(user_id, [])
                    for habit in user_day_habits:
                        total_habits += 1
                        if habit.get('completed', False):
                            completed_habits += 1
                    weekly_habits.extend(user_day_habits)
            current_date += timedelta(days=1)
        
        # Calculate completion percentage
        completion_pct = (completed_habits / total_habits * 100) if total_habits > 0 else 0
        
        return {
            "total_habits": total_habits,
            "completed_habits": completed_habits,
            "completion_pct": completion_pct,
            "week_start": start_date.strftime('%Y-%m-%d'),
            "week_end": end_date.strftime('%Y-%m-%d')
        }
    except Exception as e:
        print(f"Error calculating weekly performance: {e}")
        return {"total_habits": 0, "completed_habits": 0, "completion_pct": 0}

def store_weekly_report(user_id, performance_data):
    """Store weekly report in database"""
    try:
        db.supabase.table("weekly_reports").insert({
            "user_id": user_id,
            "week_start": performance_data["week_start"],
            "week_end": performance_data["week_end"],
            "total_habits": performance_data["total_habits"],
            "completed_habits": performance_data["completed_habits"],
            "completion_percentage": performance_data["completion_pct"],
            "created_at": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        print(f"Error storing weekly report: {e}")

# Schedule tasks
scheduler.add_job(daily_task, 'cron', hour=0, minute=1)
scheduler.add_job(weekly_task, 'cron', day_of_week='sun', hour=23, minute=59)
scheduler.start()
@app.get("/")
def root():
    return {"message": "HabitHub API is running", "status": "healthy"}

# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)