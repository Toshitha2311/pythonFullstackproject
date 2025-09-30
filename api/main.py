# api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
import logic

app = FastAPI()

class HabitAddModel(BaseModel):
    name: str
    description: str | None = None

class HabitIDModel(BaseModel):
    habit_id: str

@app.post("/habit/add")
def add_habit(habit: HabitAddModel):
    return logic.add_new_habit(None, habit.name, habit.description)

@app.get("/habit/list")
def list_habits():
    return {"habits": logic.list_user_habits(None)}

@app.post("/habit/complete")
def complete_habit(h: HabitIDModel):
    return logic.complete_habit(h.habit_id)

@app.post("/habit/remove")
def remove_habit(h: HabitIDModel):
    return logic.remove_habit(h.habit_id)

@app.get("/habit/status")
def habit_status():
    return logic.get_today_status(None)

@app.get("/weekly/report")
def weekly_report():
    return logic.get_my_weekly_performance(None)
