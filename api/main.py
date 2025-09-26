# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.logic import Habits, HabitLogs, WeeklyPerformance

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
    description: str | None = None

class HabitName(BaseModel):
    name: str

# ------------------------------ API Endpoints --------------------
@app.get("/")
def home():
    return {"success": True, "message": "HabitHub API is running"}

# --- Habits Endpoints ---
@app.get("/habits")
def get_habits():
    try:
        return habits_logic.list()
    except Exception as e:
        return {"success": False, "message": str(e), "habits": []}

@app.post("/habits")
def create_habit(habit: HabitCreate):
    try:
        result = habits_logic.add(habit.name, habit.description)
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/habits/complete")
def complete_habit(habit: HabitName):
    try:
        result = habits_logic.complete(habit.name)
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/habits")
def delete_habit(habit: HabitName):
    try:
        result = habits_logic.remove(habit.name)
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- Habit Logs Endpoints ---
@app.post("/habitlogs/complete")
def complete_habit_log(habit: HabitName):
    try:
        result = habitlogs_logic.complete(habit.name)
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/habitlogs/status")
def habitlogs_status():
    try:
        result = habitlogs_logic.status()
        # Ensure always returning success field
        if "success" not in result:
            result["success"] = True
        return result
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- Weekly Performance Endpoint ---
@app.get("/weeklyperformance")
def get_weekly_performance_endpoint():
    try:
        result = weekly_logic.get_report()
        if "success" not in result:
            result["success"] = True
        if "weekly_report" not in result:
            result["weekly_report"] = []
        return result
    except Exception as e:
        return {"success": False, "message": str(e), "weekly_report": []}

# ---------- Run ------------
if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
