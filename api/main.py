# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys, os

# Add src folder to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.logic import Habits, HabitLogs, WeeklyPerformance

# ------------------------------ App Setup -------------------------
app = FastAPI(title="HabitHub API", version="1.0")

# Allow frontend to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# ------------------------------ Logic Instances -------------------
habits_logic = Habits()
habitlogs_logic = HabitLogs()
weekly_logic = WeeklyPerformance()

# ------------------------------ Data Models -----------------------
class HabitCreate(BaseModel):
    name: str
    description: str = None

class HabitName(BaseModel):
    name: str

# ------------------------------ API Endpoints --------------------
@app.get("/")
def home():
    """Check if API is running"""
    return {"message": "HabitHub API is running"}

# --- Habits Endpoints ---
@app.get("/habits")
def get_habits():
    return habits_logic.list()

@app.post("/habits")
def create_habit(habit: HabitCreate):
    result = habits_logic.add(habit.name, habit.description)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@app.put("/habits/complete")
def complete_habit(habit: HabitName):
    """
    Mark a habit as completed today.
    PUT used because it updates an existing resource (today's habit log).
    Date is automatically handled by DB.
    """
    result = habits_logic.complete(habit.name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@app.delete("/habits")
def delete_habit(habit: HabitName):
    result = habits_logic.remove(habit.name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

# --- Habit Logs Endpoints ---
@app.put("/habitlogs/complete")
def complete_habit_log(habit: HabitName):
    """
    Mark a habit as completed for today using HabitLogs class.
    Uses PUT because it's updating today's habit log.
    """
    result = habitlogs_logic.complete(habit.name)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

@app.get("/habitlogs/status")
def habitlogs_status():
    """End-of-day status with funny motivational quotes"""
    return habitlogs_logic.status()

# --- Weekly Performance Endpoint ---
@app.get("/weeklyperformance")
def get_weekly_performance_endpoint():
    """
    Fetch weekly performance for the current user automatically.
    Week start and user_id are handled internally (no input needed).
    """
    result = weekly_logic.get_report()
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    return result

#---------- Run Server ------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
