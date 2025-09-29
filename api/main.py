import sys, os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

import logic
import db

app = FastAPI()
security = HTTPBearer()

# -------------------------------
# JWT Middleware Helper using Supabase only
# -------------------------------
def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        user_resp = db.supabase.auth.get_user(token)
        if not user_resp.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_resp.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# -------------------------------
# MODELS
# -------------------------------
class HabitAddModel(BaseModel):
    name: str
    description: str | None = None

class HabitIDModel(BaseModel):
    habit_id: str

class RegisterModel(BaseModel):
    email: EmailStr
    password: str

class LoginModel(BaseModel):
    email: EmailStr
    password: str

# -------------------------------
# AUTH ROUTES
# -------------------------------
@app.post("/auth/register")
def register(user: RegisterModel):
    try:
        # Correct Supabase sign up
        res = db.supabase.auth.sign_up(email=user.email, password=user.password)
        if not res.user:
            raise HTTPException(status_code=400, detail="Registration failed")

        # Sign in immediately to get access token
        session_resp = db.supabase.auth.sign_in_with_password(email=user.email, password=user.password)
        access_token = session_resp.session.access_token if session_resp.session else None

        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": res.user.id,
            "access_token": access_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login")
def login(user: LoginModel):
    try:
        res = db.supabase.auth.sign_in_with_password(email=user.email, password=user.password)
        if not res.session:
            raise HTTPException(status_code=400, detail="Login failed")
        return {
            "success": True,
            "message": "Login successful",
            "user_id": res.user.id,
            "access_token": res.session.access_token
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -------------------------------
# HABIT ROUTES
# -------------------------------
@app.post("/habit/add")
def add_habit(habit: HabitAddModel, user_id: str = Depends(get_current_user_id)):
    res = logic.add_new_habit(user_id, habit.name, habit.description)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return {"success": True, "message": "Habit added successfully", "habit": res.data[0]}


@app.get("/habit/list")
def list_habits(user_id: str = Depends(get_current_user_id)):
    habits = logic.list_user_habits(user_id)
    return {"success": True, "habits": habits}


@app.post("/habit/complete")
def complete_habit(habit: HabitIDModel, user_id: str = Depends(get_current_user_id)):
    res = logic.complete_habit(habit.habit_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return {"success": True, "message": "Habit marked completed"}


@app.post("/habit/remove")
def remove_habit(habit: HabitIDModel, user_id: str = Depends(get_current_user_id)):
    res = logic.remove_habit(habit.habit_id)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
    return {"success": True, "message": "Habit removed"}


@app.get("/habit/status")
def habit_status(user_id: str = Depends(get_current_user_id)):
    status = logic.get_today_status(user_id)
    return {"success": True, "status": status}


# -------------------------------
# WEEKLY PERFORMANCE ROUTES
# -------------------------------
@app.get("/weekly/report")
def weekly_report(user_id: str = Depends(get_current_user_id)):
    report = logic.get_my_weekly_performance(user_id)
    return {"success": True, "weekly_report": report}


@app.post("/weekly/calculate")
def weekly_calculate(user_id: str = Depends(get_current_user_id)):
    res = logic.generate_weekly_performance(user_id)
    if "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return {"success": True, "message": "Weekly performance updated"}


# -------------------------------
# APScheduler: Auto weekly update
# -------------------------------
scheduler = BackgroundScheduler()

def weekly_task():
    users = db.supabase.table("habits").select("user_id").execute().data
    if not users:
        return
    unique_users = set(u["user_id"] for u in users if "user_id" in u)
    for uid in unique_users:
        db.create_weekly_performance_for_user(uid, datetime.today().date())

scheduler.add_job(weekly_task, 'cron', day_of_week='sun', hour=23, minute=59)
scheduler.start()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
