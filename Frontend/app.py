import streamlit as st
import requests
import json
from datetime import datetime, timedelta, time
import time
import matplotlib.pyplot as plt
import pandas as pd
import os
import base64
import numpy as np
import math
import threading
import pygame
import calendar
import sqlite3
import pickle
import random

API_URL = "http://127.0.0.1:8000"

# ---------- File Paths ----------
ALARM_FILE = "alarm_settings.json"
HABITS_FILE = "habit_data.json"
WEEKLY_REPORT_FILE = "weekly_reports.json"

# ---------- Motivational Messages ----------
MOTIVATIONAL_QUOTES = [
    "🌞 Rise and shine! Let's make today count!",
    "💪 Time to chase your goals and crush them!",
    "✨ Stay consistent — small steps create big changes!",
    "🔥 Another day, another chance to improve yourself!",
    "🌿 Focus on progress, not perfection!",
    "🚀 You're stronger than your excuses — let's go!",
    "🕒 Don't wish for it. Work for it!",
    "🌈 Start your day with positivity and purpose!"
]

# Initialize pygame mixer
try:
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except:
    PYGAME_AVAILABLE = False

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="HabitHub", 
    layout="wide", 
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# -------------------------------
# PERSISTENT ALARM STORAGE
# -------------------------------
def init_alarm_database():
    """Initialize SQLite database for persistent alarm storage"""
    conn = sqlite3.connect('alarms.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS alarms
        (user_id TEXT, habit_name TEXT, alarm_data BLOB, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)
    ''')
    conn.commit()
    conn.close()

def save_alarms_to_db(user_id, alarms):
    """Save alarms to persistent database"""
    try:
        conn = sqlite3.connect('alarms.db')
        c = conn.cursor()
        
        # Delete existing alarms for this user
        c.execute("DELETE FROM alarms WHERE user_id = ?", (user_id,))
        
        # Save new alarms
        for habit_name, alarm_data in alarms.items():
            # Convert datetime objects to strings for serialization
            serializable_alarm = {
                'habit_name': alarm_data['habit_name'],
                'alarm_time': alarm_data['alarm_time'].strftime('%H:%M:%S'),
                'triggered': alarm_data.get('triggered', False),
                'recurring': alarm_data.get('recurring', True),
                'days': alarm_data.get('days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            }
            c.execute("INSERT INTO alarms (user_id, habit_name, alarm_data) VALUES (?, ?, ?)",
                     (user_id, habit_name, pickle.dumps(serializable_alarm)))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving alarms to DB: {e}")
        return False

def load_alarms_from_db(user_id):
    """Load alarms from persistent database"""
    try:
        conn = sqlite3.connect('alarms.db')
        c = conn.cursor()
        c.execute("SELECT habit_name, alarm_data FROM alarms WHERE user_id = ?", (user_id,))
        rows = c.fetchall()
        conn.close()
        
        alarms = {}
        for habit_name, alarm_blob in rows:
            alarm_data = pickle.loads(alarm_blob)
            # Convert string time back to time object
            alarm_time = datetime.strptime(alarm_data['alarm_time'], '%H:%M:%S').time()
            
            alarms[habit_name] = {
                'habit_name': alarm_data['habit_name'],
                'alarm_time': alarm_time,
                'triggered': alarm_data.get('triggered', False),
                'recurring': alarm_data.get('recurring', True),
                'days': alarm_data.get('days', ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            }
        
        return alarms
    except Exception as e:
        print(f"Error loading alarms from DB: {e}")
        return {}

# Initialize database on startup
init_alarm_database()

# -------------------------------
# SESSION STATE INIT
# -------------------------------
if "page" not in st.session_state:
    st.session_state.page = "auth"
if "user" not in st.session_state:
    st.session_state.user = None
if "completed_habits" not in st.session_state:
    st.session_state.completed_habits = set()
if "deleted_habits" not in st.session_state:
    st.session_state.deleted_habits = set()
if "show_success" not in st.session_state:
    st.session_state.show_success = False
if "today_habits" not in st.session_state:
    st.session_state.today_habits = []
if "active_timers" not in st.session_state:
    st.session_state.active_timers = {}
if "timer_history" not in st.session_state:
    st.session_state.timer_history = []
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False
if "habit_targets" not in st.session_state:
    st.session_state.habit_targets = {}
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"
if "alarms" not in st.session_state:
    st.session_state.alarms = {}
if "alarm_history" not in st.session_state:
    st.session_state.alarm_history = []
if "user_habits_data" not in st.session_state:
    st.session_state.user_habits_data = []
if "user_monthly_data" not in st.session_state:
    st.session_state.user_monthly_data = []
if "last_reset_date" not in st.session_state:
    st.session_state.last_reset_date = None
if "alarm_check_interval" not in st.session_state:
    st.session_state.alarm_check_interval = 0
if "weekly_stars" not in st.session_state:
    st.session_state.weekly_stars = 0
if "last_alarm_check" not in st.session_state:
    st.session_state.last_alarm_check = None
if "user_alarms" not in st.session_state:
    st.session_state.user_alarms = {}
if "alarm_threads" not in st.session_state:
    st.session_state.alarm_threads = {}
if "alarms_initialized" not in st.session_state:
    st.session_state.alarms_initialized = False
if "last_alarm_trigger" not in st.session_state:
    st.session_state.last_alarm_trigger = {}
if "alarm_thread_started" not in st.session_state:
    st.session_state.alarm_thread_started = False
if "last_alarm_check_time" not in st.session_state:
    st.session_state.last_alarm_check_time = None
if "alarm_sound_playing" not in st.session_state:
    st.session_state.alarm_sound_playing = False
if "weekly_report_generated" not in st.session_state:
    st.session_state.weekly_report_generated = False
if "current_week_number" not in st.session_state:
    st.session_state.current_week_number = datetime.now().isocalendar()[1]
if "show_alarm_popup" not in st.session_state:
    st.session_state.show_alarm_popup = False
if "alarm_popup_message" not in st.session_state:
    st.session_state.alarm_popup_message = ""
if "alarm_popup_type" not in st.session_state:
    st.session_state.alarm_popup_type = ""
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"
if "daily_habits_loaded" not in st.session_state:
    st.session_state.daily_habits_loaded = False
if "alarm_notification" not in st.session_state:
    st.session_state.alarm_notification = None
if "active_alarm_sound" not in st.session_state:
    st.session_state.active_alarm_sound = None

# -------------------------------
# ENHANCED DAILY RESET & JSON STORAGE
# -------------------------------
def save_daily_habits_to_json():
    """Save today's habits to JSON file for historical data"""
    if not st.session_state.user or not st.session_state.today_habits:
        return
    
    try:
        today_str = datetime.now().strftime('%Y%m%d')
        user_id = st.session_state.user["user_id"]
        
        # Load existing data for today
        history_file = f"habit_history_{today_str}.json"
        day_data = {}
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                day_data = json.load(f)
        
        # Update with current user's habits
        day_data[user_id] = st.session_state.today_habits
        
        # Save back to file
        with open(history_file, 'w') as f:
            json.dump(day_data, f, indent=2, default=str)
            
    except Exception as e:
        print(f"Error saving habits to JSON: {e}")

def load_previous_habits_from_json(user_id, date):
    """Load habits for a specific date from JSON"""
    try:
        date_str = date.strftime('%Y%m%d')
        history_file = f"habit_history_{date_str}.json"
        
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                day_data = json.load(f)
                return day_data.get(user_id, [])
        return []
    except Exception as e:
        print(f"Error loading previous habits: {e}")
        return []

def cleanup_old_habit_files():
    """Delete habit files older than 30 days"""
    try:
        today = datetime.now().date()
        cutoff_date = today - timedelta(days=30)
        
        for filename in os.listdir('.'):
            if filename.startswith('habit_history_') and filename.endswith('.json'):
                # Extract date from filename
                date_str = filename.replace('habit_history_', '').replace('.json', '')
                try:
                    file_date = datetime.strptime(date_str, '%Y%m%d').date()
                    if file_date < cutoff_date:
                        os.remove(filename)
                        print(f"Deleted old habit file: {filename}")
                except ValueError:
                    continue
    except Exception as e:
        print(f"Error cleaning up old files: {e}")

def initialize_daily_habits():
    """Enhanced daily reset with JSON storage - COMPLETELY FRESH START EVERY DAY"""
    if not st.session_state.user:
        return
    
    today = datetime.now().date()
    current_week = datetime.now().isocalendar()[1]

    # Check if week has changed
    if st.session_state.current_week_number != current_week:
        st.session_state.current_week_number = current_week
        st.session_state.weekly_report_generated = False

    # Check if it's a new day - COMPLETELY RESET HABITS
    if ("last_reset_date" not in st.session_state or 
        st.session_state.last_reset_date != today or
        not st.session_state.daily_habits_loaded):
        
        # If we have previous data, save it to JSON before resetting
        if (hasattr(st.session_state, 'last_reset_date') and 
            st.session_state.last_reset_date and 
            st.session_state.today_habits):
            save_daily_habits_to_json()
        
        # COMPLETE RESET for new day - NO HABITS CARRIED OVER
        st.session_state.last_reset_date = today
        st.session_state.today_habits = []  # EMPTY LIST - FRESH START
        st.session_state.deleted_habits = set()
        st.session_state.completed_habits = set()
        st.session_state.active_timers = {}
        st.session_state.daily_habits_loaded = True
        
        # Clean up old files (runs occasionally)
        if today.day % 7 == 0:  # Run cleanup once a week
            cleanup_old_habit_files()
        
        st.rerun()

def load_fresh_habits():
    """Load fresh habits for today - previous habits don't carry over"""
    if st.session_state.user:
        # Get today's habits from API - this should only return current user's habits
        today_data = today_status_api(st.session_state.user["user_id"])
        if today_data.get("success"):
            # Filter habits to ensure only current user's habits are shown
            user_habits = [habit for habit in today_data["habits"]]
            st.session_state.today_habits = user_habits
            
            # Update completed habits in session state
            st.session_state.completed_habits = set()
            for habit in st.session_state.today_habits:
                if habit.get("completed"):
                    st.session_state.completed_habits.add(habit["habit_id"])

# -------------------------------
# GLOBAL ALARM POPUP SYSTEM
# -------------------------------
def show_alarm_popup(message, alarm_type="info"):
    """Show alarm popup on any page"""
    st.session_state.show_alarm_popup = True
    st.session_state.alarm_popup_message = message
    st.session_state.alarm_popup_type = alarm_type

def render_alarm_popup():
    """Render alarm popup if triggered"""
    if st.session_state.show_alarm_popup:
        # Use Streamlit's native modal or create a custom one
        if st.session_state.alarm_popup_type == "warning":
            st.warning(st.session_state.alarm_popup_message)
        elif st.session_state.alarm_popup_type == "error":
            st.error(st.session_state.alarm_popup_message)
        elif st.session_state.alarm_popup_type == "success":
            st.success(st.session_state.alarm_popup_message)
        else:
            st.info(st.session_state.alarm_popup_message)
        
        # Add a close button with unique key based on current page
        current_page = st.session_state.get('current_page', 'unknown')
        close_key = f"close_alarm_popup_{current_page}"
        
        if st.button("Close Notification", key=close_key):
            st.session_state.show_alarm_popup = False
            st.rerun()

def show_alarm_notification(message):
    """Show alarm notification that appears automatically"""
    st.session_state.alarm_notification = message
    # Use JavaScript to show a browser notification
    js_code = f"""
    <script>
    if ("Notification" in window) {{
        Notification.requestPermission().then(function(permission) {{
            if (permission === "granted") {{
                new Notification("HabitHub Alarm", {{
                    body: "{message}",
                    icon: "https://cdn-icons-png.flaticon.com/512/2091/2091471.png"
                }});
            }}
        }});
    }}
    </script>
    """
    st.components.v1.html(js_code, height=0)
    
    # Also show in Streamlit
    st.toast(f"🔔 {message}", icon="⏰")

# -------------------------------
# CARTOON STYLING WITH ORANGE/VIOLET/WHITE THEME
# -------------------------------
def apply_cartoon_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp {
        background: radial-gradient(1200px 600px at 10% 20%, rgba(255, 124, 170, 0.20), transparent 60%),
                    radial-gradient(1000px 500px at 90% 15%, rgba(148, 118, 255, 0.22), transparent 60%),
                    radial-gradient(900px 600px at 30% 85%, rgba(255, 190, 120, 0.18), transparent 60%),
                    linear-gradient(160deg, #070a1f 0%, #0b0f2b 60%, #0a0e27 100%) !important;
        font-family: 'Poppins', 'Inter', 'Segoe UI', Roboto, system-ui, -apple-system, sans-serif !important;
    }
    
    .main-header {
        font-family: 'Poppins', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        font-size: 2.5rem !important;
        color: #ffffff !important;
        text-align: center;
        margin-top: 0.5rem !important;
        margin-bottom: 0.75rem !important;
        letter-spacing: 0.3px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3) !important;
    }
    
    .fade-in {
        animation: fadeIn 1s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .cartoon-card {
        background: rgba(255, 255, 255, 0.08) !important;
        border-radius: 18px !important;
        border: 1px solid rgba(255, 255, 255, 0.20) !important;
        padding: 1.25rem !important;
        margin: 0.5rem 0 1rem 0 !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255,255,255,0.12) !important;
        backdrop-filter: blur(12px) saturate(120%) !important;
        -webkit-backdrop-filter: blur(12px) saturate(120%) !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        animation: fadeIn 0.8s ease-in;
        color: #ffffff !important;
    }
    
    .habit-bubble {
        background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06)) !important;
        border-radius: 14px !important;
        padding: 0.75rem 0.9rem !important;
        margin: 0.75rem 0 !important;
        border: 1px solid rgba(255,255,255,0.18) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.25) !important;
        transition: transform 0.25s ease, box-shadow 0.25s ease !important;
        animation: fadeIn 0.6s ease-out;
        color: #ffffff !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .habit-completed {
        background: linear-gradient(180deg, rgba(76, 175, 80, 0.20), rgba(139, 195, 74, 0.12)) !important;
        border: 1px solid rgba(182, 255, 182, 0.30) !important;
        animation: pulse 2s infinite;
        color: #E9FFEA !important;
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .stButton > button {
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        background: linear-gradient(180deg, rgba(147, 124, 255, 0.30), rgba(147, 124, 255, 0.18)) !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        padding: 0.65rem 1.25rem !important;
        box-shadow: 0 8px 20px rgba(147, 124, 255, 0.25) !important;
        transition: transform 0.15s ease, box-shadow 0.2s ease !important;
        font-family: 'Poppins', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
        backdrop-filter: blur(8px) saturate(120%) !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 24px rgba(147, 124, 255, 0.35) !important;
    }
    
    .metric-card {
        background: rgba(255, 255, 255, 0.07) !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 255, 255, 0.18) !important;
        padding: 1.1rem !important;
        text-align: center !important;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.25) !important;
        animation: fadeIn 1s ease-in;
        color: #ffffff !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .alarm-active {
        background: linear-gradient(45deg, #FF416C, #FF4B2B) !important;
        border: 2px solid #FFFFFF !important;
        animation: alarmPulse 1s infinite;
    }
    
    @keyframes alarmPulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 65, 108, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(255, 65, 108, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 65, 108, 0); }
    }
    
    .timer-active {
        background: linear-gradient(45deg, #FF5722, #FF9800) !important;
        border: 2px solid #FFFFFF !important;
        animation: glow 1.5s infinite alternate;
    }
    
    @keyframes glow {
        from { box-shadow: 0 0 10px #FF5722; }
        to { box-shadow: 0 0 20px #FF9800; }
    }
    
    .star-rating {
        font-size: 2rem;
        text-align: center;
        margin: 1rem 0;
    }
    
    .star-filled {
        color: #FFD700;
        text-shadow: 0 0 10px #FFD700;
    }
    
    .star-empty {
        color: #666666;
    }
    
    .day-pill {
        display: inline-block;
        padding: 4px 12px;
        margin: 2px;
        border-radius: 20px;
        background: rgba(147, 124, 255, 0.3);
        border: 1px solid rgba(255, 255, 255, 0.2);
        font-size: 0.8rem;
        color: white;
    }
    
    .day-pill.active {
        background: linear-gradient(45deg, #FF416C, #FF4B2B);
        border: 1px solid #FFFFFF;
    }
    
    .auto-refresh-info {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 10px;
        margin: 10px 0;
        border: 1px solid rgba(255, 255, 255, 0.1);
        font-size: 0.8rem;
        text-align: center;
    }
    
    .professional-table {
        width: 100%;
        border-collapse: collapse;
        margin: 1rem 0;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        overflow: hidden;
    }
    
    .professional-table th {
        background: rgba(147, 124, 255, 0.3);
        padding: 12px;
        text-align: left;
        color: white;
        font-weight: 600;
    }
    
    .professional-table td {
        padding: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        color: white;
    }
    
    .professional-table tr:hover {
        background: rgba(255, 255, 255, 0.05);
    }
    
    .weekly-planner-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .day-card {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.15);
        backdrop-filter: blur(10px);
    }
    
    .day-header {
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
        color: #8A2BE2;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        padding-bottom: 0.5rem;
    }
    
    .habit-item {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-left: 3px solid #8A2BE2;
    }
    
    .empty-state {
        text-align: center;
        color: rgba(255, 255, 255, 0.5);
        font-style: italic;
        padding: 1rem;
    }
    
    .completed-habit {
        opacity: 0.7;
        background: rgba(76, 175, 80, 0.1) !important;
    }
    
    .completed-habit button {
        display: none !important;
    }
    
    .stop-alarm-btn {
        background: linear-gradient(45deg, #FF416C, #FF4B2B) !important;
        border: 2px solid #FFFFFF !important;
        animation: alarmPulse 1s infinite;
    }
    
    .completed-day {
        opacity: 0.6;
        background: rgba(76, 175, 80, 0.15) !important;
        border: 1px solid rgba(76, 175, 80, 0.3) !important;
    }
    
    .completed-day .day-header {
        color: #4CAF50 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------
# API HELPERS - UPDATED FOR DATABASE INTEGRATION
# -------------------------------
def safe_json(resp):
    try:
        return resp.json()
    except:
        return {}

def register_api(name, email, password):
    resp = requests.post(f"{API_URL}/auth/register", 
                        json={"name": name, "email": email, "password": password})
    return safe_json(resp)

def login_api(email, password):
    resp = requests.post(f"{API_URL}/auth/login", 
                        json={"email": email, "password": password})
    return safe_json(resp)

def add_habit_api_backend(name, desc, user_id, target_minutes=25):
    resp = requests.post(f"{API_URL}/habit/add", 
                        json={"name": name, "description": desc, "user_id": user_id, "target_minutes": target_minutes})
    return safe_json(resp)

def list_habits_api(user_id):
    resp = requests.post(f"{API_URL}/habit/list", json={"user_id": user_id})
    data = safe_json(resp)
    return data.get("habits", []) if data.get("success") else []

def complete_habit_api_backend(hid, user_id):
    resp = requests.post(f"{API_URL}/habit/complete", 
                        json={"habit_id": hid, "user_id": user_id})
    return safe_json(resp)

def remove_habit_api_backend(hid, user_id):
    resp = requests.post(f"{API_URL}/habit/remove", 
                        json={"habit_id": hid, "user_id": user_id})
    return safe_json(resp)

def today_status_api(user_id):
    resp = requests.post(f"{API_URL}/habit/today-status", json={"user_id": user_id})
    return safe_json(resp)

def weekly_perf_api(user_id):
    """Get weekly performance from database - ONLY at end of week"""
    try:
        today = datetime.now()
        
        # Only generate report on Sunday (end of week)
        if today.weekday() != 6:  # 6 = Sunday
            return {
                "success": True,
                "message": "Weekly report will be generated at the end of the week (Sunday)",
                "total_habits": 0,
                "completed_habits": 0,
                "completion_pct": 0,
                "week_start": (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d'),
                "week_end": (today + timedelta(days=6-today.weekday())).strftime('%Y-%m-%d'),
                "daily_breakdown": []
            }
        
        # Calculate weekly performance from actual habit data (only on Sunday)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_habits = []
        total_completed = 0
        total_habits = 0
        
        # Get habits for each day of the week
        daily_breakdown = []
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            day_habits = load_previous_habits_from_json(user_id, day_date)
            
            if day_habits:
                day_completed = sum(1 for habit in day_habits if habit.get('completed', False))
                day_total = len(day_habits)
                completion_rate = (day_completed / day_total * 100) if day_total > 0 else 0
                
                daily_breakdown.append({
                    "date": day_date.strftime('%Y-%m-%d'),
                    "day_name": day_date.strftime('%A'),
                    "total_habits": day_total,
                    "completed_habits": day_completed,
                    "completion_rate": round(completion_rate, 1)
                })
                
                total_completed += day_completed
                total_habits += day_total
        
        # Calculate overall completion
        overall_completion = (total_completed / total_habits * 100) if total_habits > 0 else 0
        
        return {
            "success": True,
            "total_habits": total_habits,
            "completed_habits": total_completed,
            "completion_pct": round(overall_completion, 1),
            "week_start": week_start.strftime('%Y-%m-%d'),
            "week_end": week_end.strftime('%Y-%m-%d'),
            "daily_breakdown": daily_breakdown
        }
        
    except Exception as e:
        print(f"Error calculating weekly performance: {e}")
        return {
            "success": True,
            "total_habits": 0,
            "completed_habits": 0,
            "completion_pct": 0,
            "daily_breakdown": []
        }

# -------------------------------
# LOCAL HABIT MANAGEMENT (FOR IMMEDIATE UI UPDATES)
# -------------------------------
def add_habit_api(habit_name, habit_description, user_id, target_minutes):
    # This now only updates the backend database
    result = add_habit_api_backend(habit_name, habit_description, user_id, target_minutes)
    if result.get("success"):
        # Reload habits from database
        load_fresh_habits()
    return result

def complete_habit_api(habit_id, user_id):
    # Update backend database
    result = complete_habit_api_backend(habit_id, user_id)
    if result.get("success"):
        # Update local state
        for habit in st.session_state.today_habits:
            if habit["habit_id"] == habit_id:
                habit["completed"] = True
    return result

def remove_habit_api(habit_id, user_id):
    # Update backend database
    result = remove_habit_api_backend(habit_id, user_id)
    if result.get("success"):
        # Update local state
        st.session_state.today_habits = [h for h in st.session_state.today_habits if h["habit_id"] != habit_id]
        st.session_state.deleted_habits.add(habit_id)
    return result

# -------------------------------
# ENHANCED ALARM FUNCTIONS - FIXED
# -------------------------------
def play_alarm():
    """Enhanced alarm sound with multiple fallback methods"""
    try:
        # Try different sound file names with different paths
        sound_files = [
            "alarm.mp3", 
            "alarm.wav", 
            "alarm_sound.mp3", 
            "beep.mp3",
            "./alarm.mp3",
            "./sounds/alarm.mp3"
        ]
        sound_path = None
        
        for file in sound_files:
            if os.path.exists(file):
                sound_path = file
                print(f"Found alarm sound: {sound_path}")
                break
        
        if sound_path:
            pygame.mixer.init()
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play(-1)  # Loop indefinitely
            st.session_state.alarm_sound_playing = True
            st.session_state.active_alarm_sound = "music"
            return True
        else:
            # Create a simple beep sound using pygame if no file found
            try:
                pygame.mixer.init()
                sample_rate = 44100
                duration = 1000  # milliseconds
                frequency = 880  # Hz
                
                n_samples = int(round(duration * 0.001 * sample_rate))
                buf = np.zeros((n_samples, 2), dtype=np.int16)
                max_sample = 2**(16 - 1) - 1
                
                for i in range(n_samples):
                    t = float(i) / sample_rate
                    buf[i][0] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
                    buf[i][1] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
                
                sound = pygame.sndarray.make_sound(buf)
                sound.play(-1)  # Loop the sound
                st.session_state.alarm_sound_playing = True
                st.session_state.active_alarm_sound = sound
                return True
            except Exception as e:
                print(f"Error generating beep: {e}")
                # Fallback to JavaScript audio
                play_alarm_sound_js()
                st.session_state.alarm_sound_playing = True
                st.session_state.active_alarm_sound = "js"
                return True
    except Exception as e:
        print(f"Error playing alarm: {e}")
        # Final fallback to JavaScript
        play_alarm_sound_js()
        st.session_state.alarm_sound_playing = True
        st.session_state.active_alarm_sound = "js"
        return False

def play_alarm_sound_js():
    """Play alarm sound using JavaScript for reliability"""
    st.markdown("""
    <script>
    function playAlarmSound() {
        try {
            // Create a more complex and noticeable alarm sound
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator1 = audioContext.createOscillator();
            const oscillator2 = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator1.connect(gainNode);
            oscillator2.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Create a pulsing alarm sound
            oscillator1.type = 'sine';
            oscillator2.type = 'square';
            
            const startTime = audioContext.currentTime;
            const duration = 0.5;
            
            // Create multiple beeps
            for(let i = 0; i < 6; i++) {
                const time = startTime + i * 0.6;
                
                oscillator1.frequency.setValueAtTime(800, time);
                oscillator1.frequency.setValueAtTime(600, time + 0.3);
                
                oscillator2.frequency.setValueAtTime(400, time);
                oscillator2.frequency.setValueAtTime(300, time + 0.3);
                
                gainNode.gain.setValueAtTime(0.8, time);
                gainNode.gain.exponentialRampToValueAtTime(0.01, time + duration);
            }
            
            oscillator1.start(startTime);
            oscillator2.start(startTime);
            oscillator1.stop(startTime + 3.6);
            oscillator2.stop(startTime + 3.6);
            
        } catch(e) {
            console.log('Web Audio failed:', e);
            // Ultimate fallback - show a visual alert
            alert('🔔 HABITHUB ALARM! Time for your habit!');
        }
    }
    playAlarmSound();
    </script>
    """, unsafe_allow_html=True)

def stop_alarm():
    """Stop alarm sound - FIXED to work properly"""
    try:
        # Stop pygame music if playing
        if st.session_state.active_alarm_sound == "music":
            pygame.mixer.music.stop()
        # Stop pygame sound if playing
        elif hasattr(st.session_state.active_alarm_sound, 'stop'):
            st.session_state.active_alarm_sound.stop()
        
        st.session_state.alarm_sound_playing = False
        st.session_state.active_alarm_sound = None
        return True
    except Exception as e:
        print(f"Error stopping alarm: {e}")
        # Try to stop any pygame sounds
        try:
            pygame.mixer.music.stop()
            pygame.mixer.stop()
        except:
            pass
        st.session_state.alarm_sound_playing = False
        st.session_state.active_alarm_sound = None
        return False

def test_alarm():
    """Test alarm sound"""
    try:
        show_alarm_notification("🔊 Testing alarm sound...")
        
        sound_files = [
            "alarm.mp3", 
            "alarm.wav", 
            "alarm_sound.mp3", 
            "beep.mp3",
            "./alarm.mp3"
        ]
        sound_path = None
        
        for file in sound_files:
            if os.path.exists(file):
                sound_path = file
                break
        
        if sound_path:
            pygame.mixer.init()
            pygame.mixer.music.load(sound_path)
            pygame.mixer.music.play()
            show_alarm_popup(f"🔊 Testing alarm sound: {sound_path}", "success")
            # Add stop button for test alarm
            if st.button("🛑 Stop Test Alarm", key="stop_test_alarm"):
                pygame.mixer.music.stop()
                show_alarm_popup("Test alarm stopped", "success")
        else:
            # Use pygame to generate beep
            pygame.mixer.init()
            sample_rate = 44100
            duration = 500  # milliseconds
            frequency = 660  # Hz
            
            n_samples = int(round(duration * 0.001 * sample_rate))
            buf = np.zeros((n_samples, 2), dtype=np.int16)
            max_sample = 2**(16 - 1) - 1
            
            for i in range(n_samples):
                t = float(i) / sample_rate
                buf[i][0] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
                buf[i][1] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
            
            sound = pygame.sndarray.make_sound(buf)
            sound.play()
            show_alarm_popup("🔊 Playing generated beep sound (no alarm file found)", "info")
            # Add stop button for test alarm
            if st.button("🛑 Stop Test Alarm", key="stop_test_beep"):
                sound.stop()
                show_alarm_popup("Test alarm stopped", "success")
    except Exception as e:
        show_alarm_popup(f"Error testing alarm: {e}", "error")
        play_alarm_sound_js()

# ---------- File Utilities ----------
def save_json(file_path, data):
    try:
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False

def load_json(file_path):
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

# -------------------------------
# ENHANCED ALARM MONITORING SYSTEM
# -------------------------------
def monitor_alarms_background():
    """Background thread to monitor and trigger alarms"""
    while True:
        try:
            if st.session_state.user:
                check_alarms()
            time.sleep(30)  # Check every 30 seconds
        except Exception as e:
            print(f"Error in alarm monitor: {e}")
            time.sleep(30)

def check_alarms():
    """Enhanced alarm checking with better timing"""
    now = datetime.now()
    
    # Only check alarms once per minute to reduce overhead
    if (st.session_state.last_alarm_check_time and 
        (now - st.session_state.last_alarm_check_time).total_seconds() < 55):
        return []
    
    st.session_state.last_alarm_check_time = now
    current_time = now.strftime("%H:%M")
    current_day = calendar.day_name[now.weekday()]
    
    triggered = []
    
    # Check habit alarms
    for habit_name, alarm in list(st.session_state.alarms.items()):
        alarm_time = alarm["alarm_time"].strftime("%H:%M")
        alarm_days = alarm.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
        
        # Check if it's the right day and time
        if current_day in alarm_days and current_time == alarm_time:
            # Check cooldown to prevent multiple triggers in the same minute
            last_trigger = st.session_state.last_alarm_trigger.get(habit_name)
            if last_trigger and (now - last_trigger).total_seconds() < 55:  # 55 second cooldown
                continue
                
            triggered.append(habit_name)
            st.session_state.last_alarm_trigger[habit_name] = now
            
            # Enhanced notification with popup and toast
            popup_message = f"🔔 Habit Reminder!\n\n{habit_name} - Time to work on your habit! ⏰"
            show_alarm_popup(popup_message, "info")
            show_alarm_notification(f"Time for {habit_name}!")
            
            # Play sound with better error handling
            try:
                play_alarm()
            except Exception as e:
                print(f"Error playing habit alarm: {e}")
            
            # Record in history
            st.session_state.alarm_history.append({
                "habit_name": habit_name,
                "alarm_time": alarm["alarm_time"],
                "triggered_at": now,
                "days": alarm_days,
                "type": "habit_reminder"
            })
    
    # Check weekly alarms
    alarm_settings = load_json(ALARM_FILE)
    if alarm_settings and alarm_settings.get("enabled", True):
        alarm_time_str = alarm_settings.get("time", "")
        alarm_days = alarm_settings.get("days", [])
        
        if current_day in alarm_days and current_time == alarm_time_str:
            # Check cooldown for weekly alarm
            last_weekly_trigger = st.session_state.last_alarm_trigger.get("weekly_alarm")
            if last_weekly_trigger and (now - last_weekly_trigger).total_seconds() < 55:
                return triggered
                
            st.session_state.last_alarm_trigger["weekly_alarm"] = now
            
            quote = random.choice(MOTIVATIONAL_QUOTES)
            habits_data = load_json(HABITS_FILE) or {}
            todays_habits = habits_data.get(current_day, [])
            
            # Create notification
            if todays_habits:
                habit_text = " • ".join(todays_habits)
                popup_message = f"🔔 WEEKLY ALARM! {quote}\n\n📋 Today's Habits: {habit_text}"
            else:
                popup_message = f"🔔 WEEKLY ALARM! {quote}\n\n💡 No habits added for today. Time to plan your day!"
            
            show_alarm_popup(popup_message, "warning")
            show_alarm_notification("Weekly habit reminder! Check your habits for today.")
            
            # Play alarm with retry logic
            if not play_alarm():
                time.sleep(2)
                play_alarm()
    
    return triggered

def set_alarm(habit_name, alarm_time, days=None):
    """Enhanced alarm setting with validation"""
    if days is None:
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    st.session_state.alarms[habit_name] = {
        "habit_name": habit_name,
        "alarm_time": alarm_time,
        "triggered": False,
        "recurring": True,
        "days": days,
        "created_at": datetime.now().isoformat()
    }
    
    # Save alarms to persistent database
    if st.session_state.user:
        save_alarms_to_db(st.session_state.user["user_id"], st.session_state.alarms)
    
    days_display = ", ".join(days) if days else "daily"
    show_alarm_popup(f"🔔 Alarm set for {habit_name} at {alarm_time.strftime('%I:%M %p')} on {days_display}!", "success")
    show_alarm_notification(f"Alarm set for {habit_name}")
    return alarm_time

def remove_alarm(habit_name):
    """Remove an alarm and save changes to database"""
    if habit_name in st.session_state.alarms:
        del st.session_state.alarms[habit_name]
        # Update persistent storage
        if st.session_state.user:
            save_alarms_to_db(st.session_state.user["user_id"], st.session_state.alarms)
        show_alarm_popup(f"Alarm for {habit_name} removed!", "success")
        st.rerun()

def load_user_alarms():
    """Load alarms for the current user from persistent storage"""
    if st.session_state.user:
        user_id = st.session_state.user["user_id"]
        # Load from database instead of session state
        alarms_from_db = load_alarms_from_db(user_id)
        st.session_state.alarms = alarms_from_db

# -------------------------------
# AUTO-REFRESH MECHANISM
# -------------------------------
def setup_auto_refresh():
    """Set up automatic refresh to check alarms"""
    # This creates a simple auto-refresh mechanism
    st.markdown("""
    <script>
    // Auto-refresh the page every 60 seconds to check alarms
    setTimeout(function() {
        window.location.reload();
    }, 60000);
    </script>
    """, unsafe_allow_html=True)
    
    # Show auto-refresh info
    st.sidebar.markdown("""
    <div class="auto-refresh-info">
        🔄 Auto-refresh: 60s<br>
        🔔 Alarms work when tab is open
    </div>
    """, unsafe_allow_html=True)

# -------------------------------
# TIMER FUNCTIONS
# -------------------------------
def start_timer(habit_name, habit_id, target_minutes=25):
    st.session_state.active_timers[habit_id] = {
        "habit_name": habit_name,
        "start_time": datetime.now(),
        "habit_id": habit_id,
        "target_minutes": target_minutes
    }

def stop_timer(habit_id):
    if habit_id in st.session_state.active_timers:
        timer_data = st.session_state.active_timers[habit_id]
        end_time = datetime.now()
        duration = end_time - timer_data["start_time"]
        
        # Save to timer history
        st.session_state.timer_history.append({
            "habit_name": timer_data["habit_name"],
            "habit_id": habit_id,
            "start_time": timer_data["start_time"],
            "end_time": end_time,
            "duration": duration,
            "date": datetime.now().date(),
            "target_minutes": timer_data.get("target_minutes", 25)
        })
        
        # Remove from active timers
        del st.session_state.active_timers[habit_id]
        
        return duration
    return None

def play_completion_sound():
    """Play completion beep sound"""
    st.markdown("""
    <script>
    function playCompletion() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            // Happy completion sound
            oscillator.frequency.setValueAtTime(523.25, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(659.25, audioContext.currentTime + 0.1);
            oscillator.frequency.setValueAtTime(783.99, audioContext.currentTime + 0.2);
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 0.5);
        } catch(e) {
            console.log('Completion sound failed:', e);
        }
    }
    playCompletion();
    </script>
    """, unsafe_allow_html=True)

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# -------------------------------
# ENHANCED WEEKLY STARS SYSTEM
# -------------------------------
def calculate_weekly_stars():
    """Enhanced stars calculation with better accuracy"""
    if not st.session_state.user:
        return 0
    
    weekly_data = weekly_perf_api(st.session_state.user["user_id"])
    if weekly_data.get("success") and weekly_data.get("total_habits", 0) > 0:
        completion_pct = weekly_data.get("completion_pct", 0)
        
        # Enhanced star calculation with better thresholds
        if completion_pct >= 95:
            return 5
        elif completion_pct >= 85:
            return 4
        elif completion_pct >= 70:
            return 3
        elif completion_pct >= 50:
            return 2
        elif completion_pct >= 25:
            return 1
        else:
            return 0
    
    return 0

def display_stars(rating):
    """Display star rating"""
    stars_html = ""
    for i in range(5):
        if i < rating:
            stars_html += '<span class="star-filled">⭐</span>'
        else:
            stars_html += '<span class="star-empty">☆</span>'
    
    st.markdown(f'<div class="star-rating">{stars_html}</div>', unsafe_allow_html=True)

# -------------------------------
# USER DATA FUNCTIONS
# -------------------------------
def load_user_data(user_id):
    """Load user-specific data for charts and reports"""
    try:
        # Calculate weekly stars
        st.session_state.weekly_stars = calculate_weekly_stars()
        # Load user's persistent alarms from database
        load_user_alarms()
        
    except Exception as e:
        print(f"Error loading user data: {e}")

def get_today_habit_distribution():
    """Get today's habit distribution for pie chart"""
    today_habits = st.session_state.today_habits
    if not today_habits:
        return {"Completed": 0, "Pending": 0}
    
    completed = sum(1 for habit in today_habits if habit.get('completed', False))
    pending = len(today_habits) - completed
    
    return {
        "Completed": completed,
        "Pending": pending
    }

def create_gradient_colors(base_color, num_colors):
    """Create gradient colors from a base color"""
    colors = []
    for i in range(num_colors):
        # Create lighter shades
        factor = 0.8 + (i * 0.2) / num_colors
        r = min(255, int(int(base_color[1:3], 16) * factor))
        g = min(255, int(int(base_color[3:5], 16) * factor))
        b = min(255, int(int(base_color[5:7], 16) * factor))
        colors.append(f'#{r:02x}{g:02x}{b:02x}')
    return colors

def create_today_pie_chart(today_distribution):
    """Create pie chart for today's habit distribution with BEAUTIFUL GRADIENT COLORS"""
    if not today_distribution or (today_distribution["Completed"] == 0 and today_distribution["Pending"] == 0):
        return None
    
    labels = ['Completed', 'Pending']
    sizes = [today_distribution["Completed"], today_distribution["Pending"]]
    
    # Create beautiful gradient colors
    completed_gradient = create_gradient_colors('#8A2BE2', 3)  # Violet gradient
    pending_gradient = create_gradient_colors('#FF8E53', 3)    # Orange gradient
    
    # Use the middle shade from each gradient
    colors = [completed_gradient[1], pending_gradient[1]]
    
    fig, ax = plt.subplots(figsize=(6, 6))
    
    # Create the pie chart with gradient colors
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90,
        textprops={'fontsize': 12, 'weight': 'bold', 'color': 'white'},
        wedgeprops={'edgecolor': 'white', 'linewidth': 2, 'antialiased': True}
    )
    
    # Style the chart to perfectly match app theme
    plt.setp(autotexts, size=12, weight="bold", color="white")
    plt.setp(texts, size=12, color="white", weight="bold")
    ax.set_title("Today's Habit Completion", fontsize=14, fontweight='bold', color='white', pad=20)
    
    # Set background to match app exactly
    ax.set_facecolor('#0a0e27')
    fig.patch.set_facecolor('#0a0e27')
    
    # Add subtle shadow effect to wedges
    for wedge in wedges:
        wedge.set_linewidth(2)
        wedge.set_edgecolor('#FFFFFF')
    
    return fig

def create_weekly_chart(weekly_data):
    """Create weekly progress chart"""
    if not weekly_data or not weekly_data.get('daily_breakdown'):
        return None
    
    daily_data = weekly_data['daily_breakdown']
    days = [entry['day_name'][:3] for entry in daily_data]
    completion_rates = [entry['completion_rate'] for entry in daily_data]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create gradient bars
    colors = create_gradient_colors('#8A2BE2', len(days))
    
    bars = ax.bar(days, completion_rates, color=colors, edgecolor='white', linewidth=2)
    
    # Add value labels on bars
    for bar, value in zip(bars, completion_rates):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{value:.0f}%', ha='center', va='bottom', 
                fontweight='bold', color='white', fontsize=10)
    
    ax.set_ylabel('Completion Rate (%)', color='white', fontweight='bold')
    ax.set_ylim(0, 100)
    ax.set_title('Weekly Progress Overview', color='white', fontweight='bold', pad=20)
    
    # Style the chart
    ax.set_facecolor('#0a0e27')
    fig.patch.set_facecolor('#0a0e27')
    ax.tick_params(colors='white', labelsize=10)
    ax.grid(True, alpha=0.3, color='white')
    
    return fig

# -------------------------------
# AUTH PAGE
# -------------------------------
def auth_page():
    apply_cartoon_styles()
    
    st.markdown("""
    <div style="display: flex; justify-content: center; align-items: center; min-height: 100vh; padding: 2rem;">
        <div style="background: rgba(255, 255, 255, 0.1); backdrop-filter: blur(20px); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.2); padding: 3rem; box-shadow: 0 15px 35px rgba(138, 43, 226, 0.2); max-width: 400px; width: 100%;">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="font-size: 2.5rem; margin: 0; background: linear-gradient(135deg, #FFFFFF, #E6D4FF); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">HabitHub</h1>
                <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0;">Build fresh habits every day</p>
            </div>
    """, unsafe_allow_html=True)
    
    # Tab selection
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔐 Sign In", use_container_width=True, 
                    type="primary" if st.session_state.auth_mode == "login" else "secondary"):
            st.session_state.auth_mode = "login"
            st.rerun()
    with col2:
        if st.button("🚀 Register", use_container_width=True,
                    type="primary" if st.session_state.auth_mode == "register" else "secondary"):
            st.session_state.auth_mode = "register"
            st.rerun()
    
    st.markdown("<div style='margin: 2rem 0;'></div>", unsafe_allow_html=True)
    
    if st.session_state.auth_mode == "login":
        st.markdown("### Welcome Back")
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        if st.button("Sign In", use_container_width=True, type="primary"):
            if email and password:
                result = login_api(email, password)
                if result.get("success"):
                    st.session_state.user = {
                        "user_id": result["user_id"],
                        "name": result["name"],
                        "email": email
                    }
                    # Initialize daily habits and load user data (including alarms from DB)
                    initialize_daily_habits()
                    load_user_data(result["user_id"])  # This now loads from database
                    st.session_state.page = "home"
                    st.success("Welcome back! 🎉")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.warning("Please fill in all fields")
    
    else:
        st.markdown("### Create Account")
        name = st.text_input("Full Name", placeholder="Enter your name")
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Create a password")
        
        if st.button("Create Account", use_container_width=True, type="primary"):
            if name and email and password:
                result = register_api(name, email, password)
                if result.get("success"):
                    st.session_state.user = {
                        "user_id": result["user_id"],
                        "name": result["name"],
                        "email": email
                    }
                    st.session_state.page = "home"
                    st.success("Welcome! 🎉")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Registration failed")
            else:
                st.warning("Please fill in all fields")
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# -------------------------------
# PROFESSIONAL ALARM SYSTEM PAGE - FIXED
# -------------------------------
def habit_reminder_system_page():
    apply_cartoon_styles()
    
    st.markdown("# 🔔 Habit Reminder System")
    
    tab1, tab2 = st.tabs(["🕒 Reminder Settings", "📅 Weekly Planner"])

    # --- TAB 1: Reminder Settings ---
    with tab1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        
        # Load current settings
        alarm_settings = load_json(ALARM_FILE)
        
        if alarm_settings:
            try:
                saved_time = datetime.strptime(alarm_settings["time"], "%H:%M").time()
            except:
                saved_time = datetime.now().time()
            saved_days = alarm_settings.get("days", [])
            enabled = alarm_settings.get("enabled", True)
        else:
            saved_time = datetime.now().time()
            saved_days = []
            enabled = True

        use_alarm = st.checkbox("Enable weekly habit reminders", value=enabled)
        
        if use_alarm:
            alarm_time = st.time_input("Select reminder time", value=saved_time)
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            selected_days = st.multiselect("Select days for reminders", days, default=saved_days)

            if selected_days:
                st.write(f"**Reminders set for:** {alarm_time.strftime('%I:%M %p')}")
                days_display = "".join([f'<span class="day-pill active">{day[:3]}</span>' for day in selected_days])
                st.markdown(f"**Selected Days:** {days_display}", unsafe_allow_html=True)
            else:
                st.warning("Please select at least one day for reminders")

            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("💾 Save Settings", use_container_width=True):
                    if selected_days:
                        new_settings = {
                            "time": alarm_time.strftime("%H:%M"), 
                            "days": selected_days, 
                            "enabled": True,
                            "last_updated": datetime.now().isoformat()
                        }
                        if save_json(ALARM_FILE, new_settings):
                            show_alarm_popup("✅ Reminder settings saved! You'll receive notifications on selected days.", "success")
                            show_alarm_notification("Weekly alarm settings saved!")
                        else:
                            show_alarm_popup("❌ Failed to save settings", "error")
                    else:
                        show_alarm_popup("❌ Please select at least one day for reminders", "error")

            with col2:
                if st.button("🔊 Test Sound", use_container_width=True):
                    show_alarm_popup("Playing test sound...", "info")
                    show_alarm_notification("Testing alarm sound...")
                    threading.Thread(target=test_alarm, daemon=True).start()

            with col3:
                if st.button("⏹ Stop Alarm", use_container_width=True, type="secondary"):
                    if stop_alarm():
                        show_alarm_popup("✅ Alarm stopped successfully!", "success")
                        show_alarm_notification("Alarm stopped")
                    else:
                        show_alarm_popup("❌ No alarm is currently playing", "warning")
                
        else:
            if st.button("Disable Reminders", use_container_width=True):
                if alarm_settings:
                    alarm_settings["enabled"] = False
                    save_json(ALARM_FILE, alarm_settings)
                show_alarm_popup("Reminders disabled. Enable the checkbox above to activate weekly notifications.", "warning")

        st.markdown('</div>', unsafe_allow_html=True)

    # --- TAB 2: Weekly Planner - PROFESSIONAL STRUCTURE ---
    with tab2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📅 Weekly Habit Planner")
        
        habits = load_json(HABITS_FILE) or {}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Professional Grid Layout
        st.markdown("#### Your Weekly Schedule")
        st.markdown('<div class="weekly-planner-grid">', unsafe_allow_html=True)
        
        for day in days:
            day_habits = habits.get(day, [])
            
            # Check if this day is completed (all habits completed)
            day_completed = False
            if day_habits:
                # For weekly planner, we consider a day "completed" if all habits are marked as completed
                # Since this is a planning tool, we'll use a simple approach
                day_completed = all(habit.get('completed', False) if isinstance(habit, dict) else False for habit in day_habits)
            
            day_class = "day-card completed-day" if day_completed else "day-card"
            
            st.markdown(f'''
            <div class="{day_class}">
                <div class="day-header">{day}</div>
            ''', unsafe_allow_html=True)
            
            if day_habits:
                for i, habit in enumerate(day_habits, 1):
                    if isinstance(habit, dict):
                        habit_name = habit.get('name', 'Unknown Habit')
                        completed = habit.get('completed', False)
                        habit_class = "habit-item completed-habit" if completed else "habit-item"
                        st.markdown(f'<div class="{habit_class}">{i}. {habit_name} {"✅" if completed else ""}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="habit-item">{i}. {habit}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="empty-state">No habits scheduled</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)  # Close grid
        
        # Habit Management Section
        st.markdown("---")
        st.markdown("#### Manage Habits")
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_day = st.selectbox("Select Day", days, key="planner_day_select")
            new_habit = st.text_input("Habit Name", key="planner_habit_input", placeholder="Enter habit name...")
            
            if st.button("➕ Add Habit", use_container_width=True):
                if new_habit.strip():
                    habits.setdefault(selected_day, []).append(new_habit.strip())
                    if save_json(HABITS_FILE, habits):
                        show_alarm_popup(f"✅ Added '{new_habit}' to {selected_day}", "success")
                        st.rerun()
                    else:
                        show_alarm_popup("❌ Failed to save habit", "error")
                else:
                    show_alarm_popup("⚠️ Please enter a habit name", "warning")
        
        with col2:
            # Get habits for selected day, filtering out completed ones for removal
            day_habits = habits.get(selected_day, [])
            available_habits_to_remove = []
            
            for habit in day_habits:
                if isinstance(habit, dict):
                    if not habit.get('completed', False):  # Only show incomplete habits for removal
                        available_habits_to_remove.append(habit.get('name', 'Unknown Habit'))
                else:
                    available_habits_to_remove.append(habit)
            
            habit_to_remove = st.selectbox(
                "Select Habit to Remove",
                options=available_habits_to_remove,
                key="remove_habit_select",
                placeholder="Select a habit to remove..."
            )
            
            if st.button("🗑️ Remove Habit", use_container_width=True):
                if habit_to_remove and selected_day in habits:
                    # Find and remove the habit
                    updated_habits = []
                    for habit in habits[selected_day]:
                        if isinstance(habit, dict):
                            if habit.get('name') != habit_to_remove:
                                updated_habits.append(habit)
                        else:
                            if habit != habit_to_remove:
                                updated_habits.append(habit)
                    
                    habits[selected_day] = updated_habits
                    if save_json(HABITS_FILE, habits):
                        show_alarm_popup(f"✅ Removed '{habit_to_remove}' from {selected_day}", "success")
                        st.rerun()
                    else:
                        show_alarm_popup("❌ Failed to remove habit", "error")
                else:
                    show_alarm_popup("⚠️ Please select a habit to remove", "warning")
            
            if st.button("🧹 Clear All for Day", use_container_width=True):
                if selected_day in habits:
                    habits[selected_day] = []
                    if save_json(HABITS_FILE, habits):
                        show_alarm_popup(f"✅ Cleared all habits for {selected_day}", "success")
                        st.rerun()
                    else:
                        show_alarm_popup("❌ Failed to clear habits", "error")
        
        # Statistics Section
        st.markdown("---")
        st.markdown("#### 📊 Weekly Statistics")
        
        total_habits = sum(len(habits.get(day, [])) for day in days)
        days_with_habits = sum(1 for day in days if habits.get(day))
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Habits", total_habits)
        with col2:
            st.metric("Days Scheduled", f"{days_with_habits}/7")
        with col3:
            st.metric("Completion Rate", "Tracked Weekly")
        
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# MAIN APP PAGES
# -------------------------------
def home_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    # Set current page for unique button keys
    st.session_state.current_page = "home"
    
    # Check alarms on every page load - this will show popups on any page
    triggered_alarms = check_alarms()
    
    # Render alarm popup if any
    render_alarm_popup()
    
    # Add stop alarm button in the main interface
    if st.session_state.alarm_sound_playing:
        st.markdown('<div class="cartoon-card alarm-active">', unsafe_allow_html=True)
        st.warning("🔔 Alarm is currently playing!")
        if st.button("🛑 Stop Alarm", key="stop_alarm_main", use_container_width=True, type="primary"):
            if stop_alarm():
                show_alarm_popup("Alarm stopped successfully!", "success")
                st.rerun()
            else:
                show_alarm_popup("Failed to stop alarm", "error")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Animated greeting + date
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greeting = "Good Morning"
    elif hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"

    today_str = now.strftime("%A, %B %d, %Y")
    
    st.markdown(f"""
    <div class="fade-in">
        <div style="text-align:center; padding:1.5rem;">
            <h1 class="main-header">
                {greeting}, {st.session_state.user['name']}!
            </h1>
        </div>
        <div style="background: linear-gradient(180deg, rgba(138, 43, 226, 0.28), rgba(147, 112, 219, 0.14)); border-radius: 14px; padding: 0.6rem; text-align: center; color: #ffffff; font-weight: 600; font-size: 0.95rem; margin: 0.75rem 0 1rem 0; border: 1px solid rgba(255,255,255,0.18); backdrop-filter: blur(8px);">
            <h3 style="margin:0;">{today_str}</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Today's Fresh Start 🌟")

    # Show fresh start message if it's a new day
    today = datetime.now().date()
    if st.session_state.last_reset_date == today:
        st.success("✨ **Fresh Start!** Today is a new day. Previous habits are cleared. Add new habits to begin! ✨")

    # Get today's status - ONLY TODAY'S HABITS
    today_data = today_status_api(st.session_state.user["user_id"])
    
    if today_data.get("success"):
        total_habits = len(st.session_state.today_habits)
        completed_habits = len(st.session_state.completed_habits)
        
        if total_habits > 0:
            cols = st.columns(3)
            with cols[0]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Today's Habits</div>
                    <div style="font-size: 2rem; font-weight: bold;">{total_habits}</div>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Completed</div>
                    <div style="font-size: 2rem; font-weight: bold;">{completed_habits}</div>
                </div>
                """, unsafe_allow_html=True)
            with cols[2]:
                progress = (completed_habits/total_habits*100) if total_habits > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Today's Progress</div>
                    <div style="font-size: 2rem; font-weight: bold;">{progress:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)

            st.progress(progress/100)
            
            # Show completion message
            if completed_habits == total_habits and total_habits > 0:
                st.success("🎉 Perfect! All habits completed for today!")
            elif completed_habits > 0:
                st.info(f"Great progress! {completed_habits} habits completed.")
            else:
                st.info("🌟 Start completing your habits for today!")
                
            # Add pie chart for today's progress
            today_distribution = get_today_habit_distribution()
            if today_distribution["Completed"] > 0 or today_distribution["Pending"] > 0:
                st.markdown("### 📊 Today's Progress Chart")
                fig = create_today_pie_chart(today_distribution)
                if fig:
                    st.pyplot(fig)
        else:
            st.info("🌟 Add your first habit to start your daily journey!")
    else:
        st.error("❌ Could not load today's status")

def create_habit_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    # Set current page for unique button keys
    st.session_state.current_page = "create_habit"
    
    # Check alarms on every page load - this will show popups on any page
    triggered_alarms = check_alarms()
    
    # Render alarm popup if any
    render_alarm_popup()
    
    # Add stop alarm button
    if st.session_state.alarm_sound_playing:
        st.markdown('<div class="cartoon-card alarm-active">', unsafe_allow_html=True)
        st.warning("🔔 Alarm is currently playing!")
        if st.button("🛑 Stop Alarm", key="stop_alarm_create", use_container_width=True, type="primary"):
            if stop_alarm():
                show_alarm_popup("Alarm stopped successfully!", "success")
                st.rerun()
            else:
                show_alarm_popup("Failed to stop alarm", "error")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("### Create New Habit")
    
    with st.container():
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        
        habit_name = st.text_input("Habit Name", placeholder="What habit do you want to build?")
        habit_description = st.text_area("Description (optional)", placeholder="Add some motivation...", height=80)
        
        # Time target section
        st.markdown("### ⏱️ Time Target")
        target_minutes = st.slider("How many minutes do you want to spend on this habit?", 
                                 min_value=5, max_value=120, value=25, step=5,
                                 help="Set your target time for this habit")
        
        st.info(f"🎯 Target: {target_minutes} minutes per session")
        
        # Enhanced Alarm section with weekly scheduling
        st.markdown("### 🔔 Set Weekly Reminder")
        use_alarm = st.checkbox("Add weekly reminder for this habit")
        
        if use_alarm:
            # Default to current time + 2 minutes for easy testing
            default_time = (datetime.now() + timedelta(minutes=2)).time()
            alarm_time = st.time_input("Reminder time", value=default_time, key="alarm_time_picker")
            
            # Day selection like in phone clocks
            days_of_week = list(calendar.day_name)  # ["Monday", "Tuesday", ...]
            selected_days = st.multiselect("Select Days for Reminder", days_of_week, default=days_of_week)
            
            if alarm_time and habit_name and selected_days:
                # Display selected days as pills
                days_html = "".join([f'<span class="day-pill active">{day[:3]}</span>' for day in selected_days])
                st.markdown(f"**Selected Days:** {days_html}", unsafe_allow_html=True)
                st.info(f"Reminder will activate at {alarm_time.strftime('%I:%M %p')} on selected days for '{habit_name}'")
        
        if st.button("Create Habit", use_container_width=True, type="primary"):
            if habit_name.strip():
                # Use the API to add habit to database
                result = add_habit_api(habit_name, habit_description, st.session_state.user["user_id"], target_minutes)
                if result.get("success"):
                    # Set alarm if requested
                    if use_alarm and alarm_time and habit_name and selected_days:
                        set_alarm(habit_name, alarm_time, selected_days)
                    
                    show_alarm_popup("Habit created successfully! 🌟", "success")
                    show_alarm_notification(f"New habit '{habit_name}' created!")
                    
                    # Reload user data and refresh today's habits
                    load_user_data(st.session_state.user["user_id"])
                    load_fresh_habits()
                    time.sleep(1)
                    st.rerun()
                else:
                    show_alarm_popup("Failed to create habit", "error")
            else:
                show_alarm_popup("Please enter a habit name", "warning")
        
        st.markdown('</div>', unsafe_allow_html=True)

def my_habits_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    # Set current page for unique button keys
    st.session_state.current_page = "my_habits"
    
    # Check alarms on every page load - this will show popups on any page
    triggered_alarms = check_alarms()
    
    # Render alarm popup if any
    render_alarm_popup()
    
    # Add stop alarm button
    if st.session_state.alarm_sound_playing:
        st.markdown('<div class="cartoon-card alarm-active">', unsafe_allow_html=True)
        st.warning("🔔 Alarm is currently playing!")
        if st.button("🛑 Stop Alarm", key="stop_alarm_habits", use_container_width=True, type="primary"):
            if stop_alarm():
                show_alarm_popup("Alarm stopped successfully!", "success")
                st.rerun()
            else:
                show_alarm_popup("Failed to stop alarm", "error")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("# Today's Habits")
    
    # Show fresh start message
    today = datetime.now().date()
    if st.session_state.last_reset_date == today:
        st.success("✨ **Fresh Start!** Today is a new day. Your habits from previous days are cleared. ✨")
    
    # Only show habits for the current logged-in user - ONLY TODAY'S HABITS
    habits = st.session_state.today_habits
    if not habits:
        st.info("No habits for today. Add some habits to get started! 🌟")
        return
    
    for habit in habits:
        if habit["habit_id"] in st.session_state.deleted_habits:
            continue
            
        completed = habit.get("completed", False)
        timer_active = habit["habit_id"] in st.session_state.active_timers
        
        # Check if alarm is set for this habit
        has_alarm = habit["name"] in st.session_state.alarms
        
        bubble_class = "habit-bubble habit-completed" if completed else "habit-bubble"
        if timer_active:
            bubble_class += " timer-active"
        if has_alarm:
            bubble_class += " alarm-active"
        
        # For completed habits, add a special class that hides buttons
        if completed:
            bubble_class += " completed-habit"
        
        st.markdown(f'<div class="{bubble_class}">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write(f"**{habit['name']}**")
            if habit.get("description"):
                st.write(f"_{habit['description']}_")
            
            # Show target time
            target_minutes = habit.get('target_minutes', 25)
            st.write(f"🎯 **Target:** {target_minutes} minutes")
            
            if completed:
                st.write("✅ **Completed**")
            if timer_active:
                timer_data = st.session_state.active_timers[habit["habit_id"]]
                elapsed = datetime.now() - timer_data["start_time"]
                target_seconds = target_minutes * 60
                progress = min((elapsed.total_seconds() / target_seconds) * 100, 100)
                
                st.write(f"⏱️ **Timer:** {format_time(elapsed.total_seconds())}")
                st.progress(progress/100)
                
                # Auto-complete if target time reached
                if elapsed.total_seconds() >= target_seconds and not completed:
                    show_alarm_popup("🎉 Target time reached! Habit completed!", "success")
                    show_alarm_notification(f"'{habit['name']}' completed! 🎉")
                    complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    play_completion_sound()
                    load_fresh_habits()
                    st.rerun()
                    
            if has_alarm:
                alarm_info = st.session_state.alarms[habit["name"]]
                alarm_time = alarm_info["alarm_time"]
                days = alarm_info.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                
                # Display days as pills
                days_display = "".join([f'<span class="day-pill active">{day[:3]}</span>' for day in days])
                st.write(f"🔔 **Reminder:** {alarm_time.strftime('%I:%M %p')}")
                st.markdown(f"**Days:** {days_display}", unsafe_allow_html=True)
        
        with col2:
            if not completed:  # Only show timer buttons for incomplete habits
                if timer_active:
                    if st.button("Stop", key=f"stop_{habit['habit_id']}", use_container_width=True):
                        duration = stop_timer(habit["habit_id"])
                        if duration:
                            # Play completion sound when manually stopped
                            play_completion_sound()
                            # Auto-complete when timer stops
                            complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                            show_alarm_notification(f"'{habit['name']}' completed! 🎉")
                            load_fresh_habits()
                        st.rerun()
                else:
                    if st.button("Start", key=f"start_{habit['habit_id']}", use_container_width=True):
                        start_timer(habit["name"], habit["habit_id"], target_minutes)
                        show_alarm_notification(f"Timer started for '{habit['name']}'")
                        st.rerun()
        
        with col3:
            if not completed and not timer_active:  # Only show complete button for incomplete habits
                if st.button("Complete", key=f"comp_{habit['habit_id']}", use_container_width=True, type="primary"):
                    complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    play_completion_sound()
                    show_alarm_notification(f"'{habit['name']}' completed! 🎉")
                    load_fresh_habits()
                    load_user_data(st.session_state.user["user_id"])
                    show_alarm_popup("Habit completed! 🎉", "success")
                    time.sleep(1)
                    st.rerun()
        
        with col4:
            if not completed:  # Only show delete button for incomplete habits
                if st.button("Delete", key=f"del_{habit['habit_id']}", use_container_width=True):
                    remove_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    show_alarm_popup("Habit deleted", "success")
                    show_alarm_notification(f"'{habit['name']}' deleted")
                    time.sleep(1)
                    st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def today_status_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    # Set current page for unique button keys
    st.session_state.current_page = "today_status"
    
    # Check alarms on every page load - this will show popups on any page
    triggered_alarms = check_alarms()
    
    # Render alarm popup if any
    render_alarm_popup()
    
    # Add stop alarm button
    if st.session_state.alarm_sound_playing:
        st.markdown('<div class="cartoon-card alarm-active">', unsafe_allow_html=True)
        st.warning("🔔 Alarm is currently playing!")
        if st.button("🛑 Stop Alarm", key="stop_alarm_status", use_container_width=True, type="primary"):
            if stop_alarm():
                show_alarm_popup("Alarm stopped successfully!", "success")
                st.rerun()
            else:
                show_alarm_popup("Failed to stop alarm", "error")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("# Today's Progress")
    
    # Show only today's date clearly
    today = datetime.now().date()
    st.info(f"📅 Showing data for: **{today.strftime('%A, %B %d, %Y')}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Today's Summary")
        
        # Use today's habits from session state (already filtered)
        today_habits = st.session_state.today_habits
        total_habits = len(today_habits)
        completed_habits = sum(1 for habit in today_habits if habit.get('completed', False))
        
        if total_habits > 0:
            progress = (completed_habits / total_habits) * 100
            
            st.metric("Total Habits", f"{total_habits}")
            st.metric("Completed Today", f"{completed_habits}")
            st.metric("Today's Progress", f"{progress:.1f}%")
            st.progress(progress/100)
            
            # Today's pie chart
            today_distribution = {
                "Completed": completed_habits,
                "Pending": total_habits - completed_habits
            }
            
            st.markdown("#### Today's Distribution")
            fig = create_today_pie_chart(today_distribution)
            if fig:
                st.pyplot(fig)
        else:
            st.info("No habits for today. Add some habits to see your progress!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 🔔 Reminder Management")
        
        # Active alarms
        active_alarms = [name for name, alarm in st.session_state.alarms.items()]
        if active_alarms:
            st.markdown("#### 🔔 Active Reminders")
            for alarm_name in active_alarms:
                alarm_data = st.session_state.alarms[alarm_name]
                alarm_time = alarm_data["alarm_time"]
                days = alarm_data.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
                
                # Display days as pills
                days_display = "".join([f'<span class="day-pill active">{day[:3]}</span>' for day in days])
                
                st.write(f"**{alarm_name}**")
                st.write(f"🔔 {alarm_time.strftime('%I:%M %p')}")
                st.markdown(f"**Days:** {days_display}", unsafe_allow_html=True)
                
                # Add option to remove alarm
                if st.button(f"Remove {alarm_name} reminder", key=f"remove_{alarm_name}"):
                    remove_alarm(alarm_name)
        else:
            st.info("No active reminders. Set reminders in 'Create Habit' page.")
        
        # Alarm history
        st.markdown("#### 📋 Recent Reminders")
        if st.session_state.alarm_history:
            for alarm in st.session_state.alarm_history[-5:]:
                st.write(f"**{alarm['habit_name']}** - {alarm['triggered_at'].strftime('%I:%M %p')}")
        else:
            st.info("No reminder history yet.")
        
        st.markdown('</div>', unsafe_allow_html=True)

def weekly_perf_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    # Set current page for unique button keys
    st.session_state.current_page = "weekly_perf"
    
    # Check alarms on every page load - this will show popups on any page
    triggered_alarms = check_alarms()
    
    # Render alarm popup if any
    render_alarm_popup()
    
    # Add stop alarm button
    if st.session_state.alarm_sound_playing:
        st.markdown('<div class="cartoon-card alarm-active">', unsafe_allow_html=True)
        st.warning("🔔 Alarm is currently playing!")
        if st.button("🛑 Stop Alarm", key="stop_alarm_weekly", use_container_width=True, type="primary"):
            if stop_alarm():
                show_alarm_popup("Alarm stopped successfully!", "success")
                st.rerun()
            else:
                show_alarm_popup("Failed to stop alarm", "error")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("# Weekly Performance Report")
    
    # Get enhanced weekly data
    weekly_data = weekly_perf_api(st.session_state.user["user_id"])
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Your Weekly Performance")
        
        if weekly_data.get("success"):
            # Check if it's end of week
            today = datetime.now()
            if today.weekday() != 6:  # Not Sunday
                st.info("📅 **Weekly Report Availability**")
                st.write(f"Your comprehensive weekly report will be generated on **Sunday**.")
                st.write(f"**Current Week:** {weekly_data.get('week_start', 'N/A')} to {weekly_data.get('week_end', 'N/A')}")
                st.write("Continue building your habits throughout the week for a complete performance analysis!")
                
                # Show current progress preview without pie chart
                st.markdown("#### 🎯 Current Week Preview")
                today_habits = st.session_state.today_habits
                completed_today = sum(1 for habit in today_habits if habit.get('completed', False))
                total_today = len(today_habits)
                
                if total_today > 0:
                    st.write(f"**Today's Progress:** {completed_today}/{total_today} habits completed ({completed_today/total_today*100:.1f}%)")
                else:
                    st.write("**Today's Progress:** No habits scheduled yet")
                    
                return
            
            # Only show full report on Sunday
            completion_pct = weekly_data.get("completion_pct", 0)
            total_habits = weekly_data.get("total_habits", 0)
            completed_habits = weekly_data.get("completed_habits", 0)
            daily_breakdown = weekly_data.get("daily_breakdown", [])
            
            st.success("🎉 **Weekly Report Generated!**")
            st.write(f"**Week:** {weekly_data.get('week_start', 'N/A')} to {weekly_data.get('week_end', 'N/A')}")
            
            cols = st.columns(2)
            with cols[0]:
                st.metric("Weekly Completion", f"{completion_pct:.1f}%")
            with cols[1]:
                st.metric("Habits Completed", f"{completed_habits}/{total_habits}")
            
            # Weekly progress chart
            if daily_breakdown:
                st.markdown("#### 📊 Daily Progress")
                fig = create_weekly_chart(weekly_data)
                if fig:
                    st.pyplot(fig)
            
            # Star rating display
            st.markdown("### 🏆 Your Star Rating")
            display_stars(st.session_state.weekly_stars)
            
            # Achievement messages
            if st.session_state.weekly_stars == 5:
                st.success("🌟 **Habit Superstar!** You're amazing! Keep up the perfect work!")
            elif st.session_state.weekly_stars == 4:
                st.success("🎯 **Excellent Performer!** You're building strong habits consistently!")
            elif st.session_state.weekly_stars == 3:
                st.info("💪 **Solid Achiever!** You're making great progress!")
            elif st.session_state.weekly_stars == 2:
                st.info("📈 **Good Starter!** You're on the right track!")
            elif st.session_state.weekly_stars == 1:
                st.info("🌱 **Getting There!** Every habit counts!")
            else:
                st.info("🎯 **New Week, New Start!** Complete habits to earn stars!")
                
        else:
            st.info("Complete some habits to see your weekly performance!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Performance Metrics")
        
        st.markdown("""
        #### How Stars Are Earned:
        
        ⭐⭐⭐⭐⭐ **5 Stars** - 95%+ completion  
        ⭐⭐⭐⭐ **4 Stars** - 85%+ completion  
        ⭐⭐⭐ **3 Stars** - 70%+ completion  
        ⭐⭐ **2 Stars** - 50%+ completion  
        ⭐ **1 Star** - 25%+ completion  
        ☆ **0 Stars** - Below 25% completion
        
        #### Tips for Better Performance:
        - Complete habits consistently every day
        - Use timers to track your progress
        - Set realistic time targets
        - Don't forget to mark habits as completed
        - Build a sustainable routine
        
        **Remember:** Every star represents your dedication! 🌟
        """)
        
        st.markdown("### 🎯 This Week's Goal")
        current_stars = st.session_state.weekly_stars
        if current_stars < 5:
            next_threshold = [25, 50, 70, 85, 95][current_stars]
            st.info(f"Aim for **{next_threshold}%** completion to reach **{current_stars + 1} stars** this week!")
        else:
            st.success("🎉 You've reached the maximum stars! Maintain your excellent performance!")
        
        # Daily breakdown
        if weekly_data.get('daily_breakdown'):
            st.markdown("### 📅 Daily Breakdown")
            for day_data in weekly_data['daily_breakdown']:
                emoji = "✅" if day_data['completion_rate'] >= 80 else "🟡" if day_data['completion_rate'] >= 50 else "🔴"
                st.write(f"{emoji} **{day_data['day_name']}:** {day_data['completed_habits']}/{day_data['total_habits']} habits ({day_data['completion_rate']:.0f}%)")
        
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# MAIN APP
# -------------------------------
def main():
    # Show auth page if not logged in
    if st.session_state.user is None:
        auth_page()
        return
    
    apply_cartoon_styles()
    
    # Check alarms on every app run - this will show popups on any page
    triggered_alarms = check_alarms()
    
    # Setup auto-refresh for alarm checking
    setup_auto_refresh()
    
    # Start background alarm monitoring if not already started
    if not st.session_state.alarm_thread_started:
        threading.Thread(target=monitor_alarms_background, daemon=True).start()
        st.session_state.alarm_thread_started = True
    
    # Main app navigation for logged-in users
    st.sidebar.markdown(f"""
    <div class="cartoon-card" style="text-align:center;">
        <h3>👋 Hello, {st.session_state.user['name']}!</h3>
        <p>Weekly Stars: {st.session_state.weekly_stars}/5 ⭐</p>
        <p>Fresh start every day! ✨</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Add stop alarm button in sidebar if alarm is playing
    if st.session_state.alarm_sound_playing:
        st.sidebar.markdown("### 🔔 Alarm Active")
        if st.sidebar.button("🛑 Stop Alarm", key="stop_alarm_sidebar", use_container_width=True, type="primary"):
            if stop_alarm():
                show_alarm_popup("Alarm stopped successfully!", "success")
                st.rerun()
            else:
                show_alarm_popup("Failed to stop alarm", "error")
    
    # Active timers in sidebar
    if st.session_state.active_timers:
        st.sidebar.markdown("### ⏱️ Active Timers")
        for habit_id, timer_data in st.session_state.active_timers.items():
            elapsed = datetime.now() - timer_data["start_time"]
            target_minutes = timer_data.get("target_minutes", 25)
            target_seconds = target_minutes * 60
            progress = min((elapsed.total_seconds() / target_seconds) * 100, 100)
            
            st.sidebar.info(
                f"**{timer_data['habit_name']}**\n\n"
                f"{format_time(elapsed.total_seconds())}\n\n"
                f"Progress: {progress:.1f}%"
            )
    
    # Active alarms in sidebar
    active_alarms = [name for name, alarm in st.session_state.alarms.items()]
    if active_alarms:
        st.sidebar.markdown("### 🔔 Active Reminders")
        for alarm_name in active_alarms:
            alarm_data = st.session_state.alarms[alarm_name]
            alarm_time = alarm_data["alarm_time"]
            days = alarm_data.get("days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            days_short = ", ".join([day[:3] for day in days])
            st.sidebar.warning(f"**{alarm_name}**\n{alarm_time.strftime('%I:%M %p')}\nDays: {days_short}")
    
    # Add alarm status indicator
    current_time = datetime.now().strftime("%H:%M:%S")
    st.sidebar.markdown(f"*Last checked: {current_time}*")
    
    # Navigation
    st.sidebar.markdown("### Navigation")
    pages = {
        "🏠 Dashboard": home_page,
        "📝 Today's Habits": my_habits_page,
        "➕ Create Habit": create_habit_page,
        "📊 Today's Progress": today_status_page,
        "⭐ Weekly Report": weekly_perf_page,
        "🔔 Reminder System": habit_reminder_system_page
    }
    choice = st.sidebar.radio("Go to:", list(pages.keys()))
    pages[choice]()
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "auth"
        st.session_state.completed_habits = set()
        st.session_state.deleted_habits = set()
        st.session_state.today_habits = []
        st.session_state.active_timers = {}
        st.session_state.timer_history = []
        st.session_state.welcome_shown = False
        st.session_state.alarm_history = []
        st.session_state.user_habits_data = []
        st.session_state.user_monthly_data = []
        st.session_state.last_reset_date = None
        st.session_state.weekly_stars = 0
        st.session_state.alarms = {}
        st.session_state.last_alarm_trigger = {}
        st.session_state.show_alarm_popup = False
        st.session_state.daily_habits_loaded = False
        st.session_state.alarm_notification = None
        st.session_state.active_alarm_sound = None
        st.session_state.alarm_sound_playing = False
        st.rerun()

if __name__ == "__main__":
    main()