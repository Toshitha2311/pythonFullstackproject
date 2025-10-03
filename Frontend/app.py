import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
import pandas as pd
import os
import base64

API_URL = "http://127.0.0.1:8000"

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="HabitHub", 
    layout="wide", 
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

# -------------------------------
# ASSET HELPERS
# -------------------------------
def resolve_logo_path():
    """Return first existing logo path from common locations or env variable.
    Set HABITHUB_LOGO to override."""
    env_path = os.environ.get("HABITHUB_LOGO")
    if env_path and os.path.exists(env_path):
        return env_path
    here = os.path.dirname(__file__)
    candidates = [
        os.path.join(here, "assets", "logo.png"),
        os.path.join(here, "assets", "logo.jpg"),
        os.path.join(here, "assets", "logo.jpeg"),
        os.path.join(here, "logo.png"),
        os.path.join(os.path.dirname(here), "Frontend", "assets", "logo.png"),
        os.path.join(os.path.dirname(here), "assets", "logo.png"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

# Try to get a dominant hex color from the logo (fallback to theme purple)
def get_logo_dominant_color(img_path, default="#6a4bff"):
    try:
        from PIL import Image
        img = Image.open(img_path).convert("RGBA")
        # Resize small to speed up, ignore alpha by compositing on white
        img = img.resize((64, 64))
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        img = Image.alpha_composite(bg, img).convert("RGB")
        # Get colors and pick the most frequent (excluding near-white)
        colors = img.getcolors(64*64)
        if not colors:
            return default
        # sort by count desc, prefer non-white-ish colors
        colors.sort(key=lambda c: c[0], reverse=True)
        for count, rgb in colors:
            r, g, b = rgb
            # skip very light colors
            if (r+g+b) < 735:  # < 245*3
                return "#%02x%02x%02x" % (r, g, b)
        # All light, return top
        r, g, b = colors[0][1]
        return "#%02x%02x%02x" % (r, g, b)
    except Exception:
        return default

# Darken a hex color by a given factor (0-1, where lower = darker)
def darken_hex(hex_color: str, factor: float = 0.75) -> str:
    try:
        hc = hex_color.lstrip('#')
        if len(hc) != 6:
            return hex_color
        r = int(hc[0:2], 16)
        g = int(hc[2:4], 16)
        b = int(hc[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color

def lighten_hex(hex_color: str, factor: float = 1.2) -> str:
    try:
        hc = hex_color.lstrip('#')
        if len(hc) != 6:
            return hex_color
        r = int(hc[0:2], 16)
        g = int(hc[2:4], 16)
        b = int(hc[4:6], 16)
        r = max(0, min(255, int(r * factor)))
        g = max(0, min(255, int(g * factor)))
        b = max(0, min(255, int(b * factor)))
        return f"#{r:02x}{g:02x}{b:02x}"
    except Exception:
        return hex_color

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
    # map habit_id -> target seconds per day
    st.session_state.habit_targets = {}
if "auth_mode" not in st.session_state:
    # 'login' or 'register' to control right panel form
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

# -------------------------------
# CARTOON STYLING WITH ORANGE/VIOLET/WHITE THEME
# -------------------------------
def apply_cartoon_styles():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp {
        /* Glassmorphism-inspired neon gradient background */
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
    
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    .fade-in {
        animation: fadeIn 1s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .slide-in {
        animation: slideIn 0.8s ease-out;
    }
    
    @keyframes slideIn {
        from { transform: translateX(-100px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    .cartoon-card {
        /* Frosted glass card */
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
        animation: slideIn 0.6s ease-out;
        color: #ffffff !important;
        backdrop-filter: blur(10px) !important;
    }
    .habit-bubble h2 { font-size: 1.1rem !important; margin: 0 0 0.2rem 0 !important; color: #ffffff !important; }
    .habit-bubble h3 { font-size: 0.95rem !important; margin: 0.25rem 0 0 0 !important; font-weight: 600 !important; color: #ffffff !important; }
    .habit-bubble p, .habit-bubble div, .habit-bubble span { font-size: 0.92rem !important; color: #ffffff !important; }
    
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
    
    .habit-bubble:hover {
        transform: scale(1.02) !important;
        box-shadow: 8px 8px 0 #8A2BE2 !important;
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
    
    .complete-btn {
        background: linear-gradient(45deg, #4CAF50, #8BC34A) !important;
        border: 3px solid #FFFFFF !important;
    }
    
    .timer-btn {
        background: linear-gradient(45deg, #2196F3, #21CBF3) !important;
        border: 3px solid #FFFFFF !important;
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
    
    .date-display {
        background: linear-gradient(180deg, rgba(138, 43, 226, 0.28), rgba(147, 112, 219, 0.14)) !important;
        border-radius: 14px !important;
        padding: 0.6rem !important;
        text-align: center !important;
        color: #ffffff !important;
        font-weight: 600 !important; font-size: 0.95rem !important;
        margin: 0.75rem 0 1rem 0 !important;
        animation: fadeIn 1.2s ease-in;
        border: 1px solid rgba(255,255,255,0.18) !important;
        backdrop-filter: blur(8px) !important;
    }
    
    .timer-active {
        background: linear-gradient(45deg, #FF5722, #FF9800) !important;
        border: 4px solid #FFFFFF !important;
        animation: glow 1.5s infinite alternate;
    }
    
    @keyframes glow {
        from { box-shadow: 0 0 10px #FF5722; }
        to { box-shadow: 0 0 20px #FF9800; }
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3) !important;
        font-family: 'Poppins', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
    }
    
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        color: #333333 !important;
        font-weight: bold !important;
    }
    
    .welcome-message {
        background: linear-gradient(45deg, #8A2BE2, #FF8E53) !important;
        border-radius: 20px !important;
        padding: 2rem !important;
        text-align: center !important;
        color: white !important;
        margin: 2rem 0 !important;
        animation: fadeIn 2s ease-in;
    }
    
    /* Alarm specific styles */
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

    /* Auth page specific styles */
    .auth-container {
        display: flex;
        justify-content: center;
        align-items: center;
        min-height: 100vh;
        padding: 2rem;
    }
    
    .auth-card {
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(20px) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        padding: 3rem !important;
        box-shadow: 0 15px 35px rgba(138, 43, 226, 0.2) !important;
        max-width: 400px;
        width: 100%;
    }
    
    .auth-title {
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .auth-title h1 {
        font-size: 2.5rem !important;
        margin: 0 !important;
        background: linear-gradient(135deg, #FFFFFF, #E6D4FF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    .auth-title p {
        color: rgba(255,255,255,0.8) !important;
        margin: 0.5rem 0 0 0 !important;
    }
    
    .auth-tabs {
        display: flex;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .auth-tab {
        flex: 1;
        text-align: center;
        padding: 0.8rem;
        border-radius: 10px;
        cursor: pointer;
        transition: all 0.3s ease;
        background: rgba(255, 255, 255, 0.1);
        color: #ffffff !important;
    }
    
    .auth-tab.active {
        background: linear-gradient(135deg, #7B2CBF, #5A189A);
        color: white !important;
    }
    
    .auth-form input {
        background: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 10px !important;
        padding: 0.8rem 1rem !important;
        color: white !important;
        width: 100%;
        margin-bottom: 1rem;
    }
    
    .auth-form input::placeholder {
        color: rgba(255, 255, 255, 0.6) !important;
    }
    </style>
    """, unsafe_allow_html=True)

# -------------------------------
# API HELPERS
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

def add_habit_api(name, desc, user_id):
    resp = requests.post(f"{API_URL}/habit/add", 
                        json={"name": name, "description": desc, "user_id": user_id})
    return safe_json(resp)

def list_habits_api(user_id):
    resp = requests.post(f"{API_URL}/habit/list", json={"user_id": user_id})
    data = safe_json(resp)
    return data.get("habits", []) if data.get("success") else []

def complete_habit_api(hid, user_id):
    resp = requests.post(f"{API_URL}/habit/complete", 
                        json={"habit_id": hid, "user_id": user_id})
    return safe_json(resp)

def remove_habit_api(hid, user_id):
    resp = requests.post(f"{API_URL}/habit/remove", 
                        json={"habit_id": hid, "user_id": user_id})
    return safe_json(resp)

def today_status_api(user_id):
    resp = requests.post(f"{API_URL}/habit/today-status", json={"user_id": user_id})
    return safe_json(resp)

def weekly_perf_api(user_id):
    resp = requests.post(f"{API_URL}/weekly/report", json={"user_id": user_id})
    return safe_json(resp)

def monthly_report_api(user_id):
    """Get monthly progress data"""
    resp = requests.post(f"{API_URL}/monthly/report", json={"user_id": user_id})
    return safe_json(resp)

def user_habits_history_api(user_id):
    """Get user's habit completion history"""
    resp = requests.post(f"{API_URL}/habits/history", json={"user_id": user_id})
    return safe_json(resp)

def reset_daily_habits_api(user_id):
    """Reset habits for new day"""
    resp = requests.post(f"{API_URL}/habits/reset-daily", json={"user_id": user_id})
    return safe_json(resp)

# -------------------------------
# DAILY HABIT MANAGEMENT
# -------------------------------
def initialize_daily_habits():
    """Reset habits for new day and load fresh habits"""
    if not st.session_state.user:
        return
    
    today = datetime.now().date()
    
    # Check if we need to reset for a new day
    if st.session_state.last_reset_date != today:
        # Reset completed habits and load fresh habits
        st.session_state.completed_habits = set()
        st.session_state.deleted_habits = set()
        st.session_state.active_timers = {}
        st.session_state.today_habits = []
        st.session_state.last_reset_date = today
        
        # Load fresh habits for today
        load_fresh_habits()

def load_fresh_habits():
    """Load fresh habits for today - previous habits don't carry over"""
    if st.session_state.user:
        # Get today's habits from API
        today_data = today_status_api(st.session_state.user["user_id"])
        if today_data.get("success"):
            st.session_state.today_habits = today_data["habits"]
            
            # Update completed habits set
            st.session_state.completed_habits = set()
            for habit in st.session_state.today_habits:
                if habit.get("completed"):
                    st.session_state.completed_habits.add(habit["habit_id"])

# -------------------------------
# TIMER & ALARM FUNCTIONS
# -------------------------------
def start_timer(habit_name, habit_id):
    st.session_state.active_timers[habit_id] = {
        "habit_name": habit_name,
        "start_time": datetime.now(),
        "habit_id": habit_id
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
            "date": datetime.now().date()
        })
        
        # Remove from active timers
        del st.session_state.active_timers[habit_id]
        
        return duration
    return None

def set_alarm(habit_name, alarm_time):
    """Set an alarm for a specific habit"""
    st.session_state.alarms[habit_name] = {
        "alarm_time": alarm_time,
        "triggered": False
    }

def check_alarms():
    """Check if any alarms should go off"""
    current_time = datetime.now().time()
    triggered_alarms = []
    
    for habit_name, alarm in st.session_state.alarms.items():
        if not alarm["triggered"] and current_time >= alarm["alarm_time"]:
            play_alarm_sound()
            st.session_state.alarm_history.append({
                "habit_name": habit_name,
                "alarm_time": alarm["alarm_time"],
                "triggered_at": datetime.now()
            })
            alarm["triggered"] = True
            triggered_alarms.append(habit_name)
    
    return triggered_alarms

def play_alarm_sound():
    """Play alarm sound using JavaScript"""
    st.markdown("""
    <script>
    function playAlarm() {
        try {
            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioContext.createOscillator();
            const gainNode = audioContext.createGain();
            
            oscillator.connect(gainNode);
            gainNode.connect(audioContext.destination);
            
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
            oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.5);
            oscillator.frequency.setValueAtTime(800, audioContext.currentTime + 1.0);
            
            gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1.5);
            
            oscillator.start(audioContext.currentTime);
            oscillator.stop(audioContext.currentTime + 1.5);
        } catch(e) {
            console.log('Audio not supported:', e);
        }
    }
    playAlarm();
    </script>
    """, unsafe_allow_html=True)

def get_today_time_summary():
    today = datetime.now().date()
    today_sessions = [session for session in st.session_state.timer_history 
                     if session["date"] == today]
    
    total_time = sum([session["duration"].total_seconds() for session in today_sessions], 0)
    
    # Group by habit
    habit_time = {}
    for session in today_sessions:
        habit_name = session["habit_name"]
        if habit_name not in habit_time:
            habit_time[habit_name] = 0
        habit_time[habit_name] += session["duration"].total_seconds()
    
    return total_time, habit_time

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

# -------------------------------
# TIME HELPERS (targets + beep)
# -------------------------------
def get_accumulated_seconds_today(habit_id):
    """Sum durations today for a habit from session timer_history."""
    today = datetime.now().date()
    total = 0
    for s in st.session_state.timer_history:
        if s.get("habit_id") == habit_id and s.get("date") == today:
            total += int(s.get("duration", timedelta()).total_seconds())
    return total

def render_beep():
    """Play a short beep using WebAudio API."""
    st.markdown(
        """
        <script>
        (function(){
          try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const o = ctx.createOscillator();
            const g = ctx.createGain();
            o.type = 'sine';
            o.frequency.setValueAtTime(880, ctx.currentTime);
            g.gain.setValueAtTime(0.0001, ctx.currentTime);
            g.gain.exponentialRampToValueAtTime(0.2, ctx.currentTime + 0.01);
            g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.4);
            o.connect(g); g.connect(ctx.destination); o.start(); o.stop(ctx.currentTime + 0.45);
          } catch(e) { console.warn('Beep failed', e); }
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

# -------------------------------
# USER DATA FUNCTIONS
# -------------------------------
def load_user_data(user_id):
    """Load user-specific data for charts and reports"""
    try:
        # Load user habits history
        habits_data = user_habits_history_api(user_id)
        if habits_data.get("success"):
            st.session_state.user_habits_data = habits_data.get("habits", [])
        
        # Load monthly data
        monthly_data = monthly_report_api(user_id)
        if monthly_data.get("success"):
            st.session_state.user_monthly_data = monthly_data.get("monthly_data", [])
        
    except Exception as e:
        print(f"Error loading user data: {e}")

def get_user_monthly_progress(user_id):
    """Get user's actual monthly progress data"""
    monthly_data = monthly_report_api(user_id)
    if monthly_data.get("success"):
        return monthly_data.get("monthly_data", [])
    
    # Fallback: Generate from user habits data
    user_data = st.session_state.user_habits_data
    if not user_data:
        return []
    
    # Process user data to create monthly progress
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    monthly_progress = []
    
    current = start_of_month
    while current <= today:
        # Calculate completion rate for this day from user data
        day_habits = [h for h in user_data if h.get('date') == current.isoformat()]
        if day_habits:
            total = len(day_habits)
            completed = sum(1 for h in day_habits if h.get('completed', False))
            completion_rate = (completed / total * 100) if total > 0 else 0
        else:
            completion_rate = 0
            
        monthly_progress.append({
            "date": current.strftime("%Y-%m-%d"),
            "completion_rate": completion_rate,
            "total_habits": len(day_habits),
            "completed_habits": completed if day_habits else 0
        })
        current += timedelta(days=1)
    
    return monthly_progress

def get_user_weekly_performance(user_id):
    """Get detailed weekly performance based on real user data"""
    user_data = st.session_state.user_habits_data
    if not user_data:
        return {"completion_pct": 0, "stars": 0, "daily_completion": []}
    
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    # Get habits for this week
    week_habits = []
    daily_completion = []
    
    current = start_of_week
    for i in range(7):
        day_date = current + timedelta(days=i)
        if day_date > today:
            break
            
        day_habits = [h for h in user_data if h.get('date') == day_date.isoformat()]
        if day_habits:
            total = len(day_habits)
            completed = sum(1 for h in day_habits if h.get('completed', False))
            completion_rate = (completed / total * 100) if total > 0 else 0
            week_habits.extend(day_habits)
        else:
            completion_rate = 0
            
        daily_completion.append({
            "date": day_date,
            "completion_rate": completion_rate,
            "total_habits": len(day_habits) if day_habits else 0,
            "completed_habits": completed if day_habits else 0
        })
    
    # Calculate overall weekly completion
    if week_habits:
        total_habits = len(week_habits)
        completed_habits = sum(1 for h in week_habits if h.get('completed', False))
        completion_pct = (completed_habits / total_habits * 100) if total_habits > 0 else 0
        stars = min(5, int(completion_pct / 20))
    else:
        completion_pct = 0
        stars = 0
    
    return {
        "completion_pct": completion_pct,
        "stars": stars,
        "total_habits": len(week_habits),
        "completed_habits": completed_habits if week_habits else 0,
        "daily_completion": daily_completion
    }

def get_user_habit_distribution():
    """Get actual user habit distribution for pie chart"""
    user_data = st.session_state.user_habits_data
    if not user_data:
        return {}
    
    # Get habits from current month
    today = datetime.now().date()
    start_of_month = today.replace(day=1)
    month_habits = [h for h in user_data 
                   if h.get('date') and datetime.strptime(h['date'], '%Y-%m-%d').date() >= start_of_month]
    
    habit_stats = {}
    for habit in month_habits:
        name = habit.get('name')
        if name not in habit_stats:
            habit_stats[name] = {'total': 0, 'completed': 0}
        habit_stats[name]['total'] += 1
        if habit.get('completed', False):
            habit_stats[name]['completed'] += 1
    
    return habit_stats

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

# -------------------------------
# CHART FUNCTIONS
# -------------------------------
def create_today_pie_chart(today_distribution):
    """Create pie chart for today's habit distribution"""
    if not today_distribution or (today_distribution["Completed"] == 0 and today_distribution["Pending"] == 0):
        return None
    
    labels = ['Completed', 'Pending']
    sizes = [today_distribution["Completed"], today_distribution["Pending"]]
    colors = ['#4CAF50', '#FF8E53']
    
    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=labels,
        autopct='%1.1f%%',
        colors=colors,
        startangle=90
    )
    
    # Style the chart
    plt.setp(autotexts, size=10, weight="bold", color="white")
    plt.setp(texts, size=10, color="white")
    ax.set_title("Today's Habit Completion", fontsize=14, fontweight='bold', color='white')
    ax.set_facecolor('#0a0e27')
    fig.patch.set_facecolor('#0a0e27')
    
    return fig

def create_weekly_chart(weekly_data):
    """Create weekly progress chart based on real user data"""
    if not weekly_data or not weekly_data.get('daily_completion'):
        return None
    
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    completion_rates = [day['completion_rate'] for day in weekly_data['daily_completion']]
    
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(days[:len(completion_rates)], completion_rates, color='#FF8E53', alpha=0.8)
    ax.set_xlabel('Day', fontsize=12, color='white')
    ax.set_ylabel('Completion Rate (%)', fontsize=12, color='white')
    ax.set_title('Your Weekly Performance', fontsize=14, fontweight='bold', color='white')
    ax.set_ylim(0, 100)
    ax.tick_params(colors='white')
    ax.set_facecolor('#0a0e27')
    fig.patch.set_facecolor('#0a0e27')
    
    # Add value labels on bars
    for bar, value in zip(bars, completion_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f'{value:.0f}%', 
                ha='center', va='bottom', color='white', fontweight='bold')
    
    plt.tight_layout()
    return fig

def create_monthly_chart(monthly_data):
    """Create monthly progress chart based on user data"""
    if not monthly_data:
        return None
    
    dates = [data['date'] for data in monthly_data]
    completion_rates = [data['completion_rate'] for data in monthly_data]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(dates, completion_rates, marker='o', linewidth=2, color='#8A2BE2', markersize=6)
    ax.fill_between(dates, completion_rates, alpha=0.3, color='#8A2BE2')
    ax.set_xlabel('Date', fontsize=12, color='white')
    ax.set_ylabel('Completion Rate (%)', fontsize=12, color='white')
    ax.set_title('Your Monthly Progress Trend', fontsize=14, fontweight='bold', color='white')
    ax.grid(True, alpha=0.3)
    ax.tick_params(colors='white')
    ax.set_facecolor('#0a0e27')
    fig.patch.set_facecolor('#0a0e27')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

# -------------------------------
# AUTH PAGE (Original design with improved font colors)
# -------------------------------
def auth_page():
    apply_cartoon_styles()
    
    st.markdown("""
    <div class="auth-container">
        <div class="auth-card">
            <div class="auth-title">
                <h1>HabitHub</h1>
                <p>Build fresh habits every day</p>
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
                    # Initialize daily habits and load user data
                    initialize_daily_habits()
                    load_user_data(result["user_id"])
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
# MAIN APP PAGES
# -------------------------------
def home_page():
    apply_cartoon_styles()
    check_alarms()
    initialize_daily_habits()
    
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
        <div class="date-display slide-in">
            <h3 style="margin:0;">{today_str}</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Today's Fresh Start 🌟")

    # Get today's status
    today_data = today_status_api(st.session_state.user["user_id"])
    
    if today_data.get("success"):
        total_habits = today_data["total_habits"]
        completed_habits = today_data["completed_habits"]
        st.session_state.today_habits = today_data["habits"]
        
        # Update completed habits in session state
        st.session_state.completed_habits = set()
        for habit in st.session_state.today_habits:
            if habit.get("completed"):
                st.session_state.completed_habits.add(habit["habit_id"])

        if total_habits > 0:
            cols = st.columns(3)
            with cols[0]:
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Today's Progress</div>
                    <div style="font-size: 2rem; font-weight: bold;">{completed_habits}/{total_habits}</div>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                progress = (completed_habits/total_habits*100) if total_habits > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Completion</div>
                    <div style="font-size: 2rem; font-weight: bold;">{progress:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)
            with cols[2]:
                # Get yesterday's completion from real data
                yesterday = (datetime.now() - timedelta(days=1)).date()
                user_data = st.session_state.user_habits_data
                yesterday_habits = [h for h in user_data if h.get('date') == yesterday.isoformat()]
                if yesterday_habits:
                    total_yesterday = len(yesterday_habits)
                    completed_yesterday = sum(1 for h in yesterday_habits if h.get('completed', False))
                    yesterday_completion = (completed_yesterday / total_yesterday * 100) if total_yesterday > 0 else 0
                else:
                    yesterday_completion = 0
                
                st.markdown(f"""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; opacity: 0.8;">Yesterday</div>
                    <div style="font-size: 2rem; font-weight: bold;">{yesterday_completion:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)

            st.progress(progress/100)
            
            # Show completion message
            if completed_habits == total_habits and total_habits > 0:
                st.success("🎉 Perfect! All habits completed for today!")
            elif completed_habits > 0:
                st.info(f"Great progress! {completed_habits} habits completed.")
        else:
            st.info("🌟 Add your first habit to start your daily journey!")
    else:
        st.error("❌ Could not load today's status")

def add_habit_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    st.markdown("### Add New Habit")
    
    with st.container():
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        
        habit_name = st.text_input("Habit Name", placeholder="What habit do you want to build?")
        habit_description = st.text_area("Description (optional)", placeholder="Add some motivation...", height=80)
        target_minutes = st.number_input("Target Time (minutes)", min_value=1, max_value=240, value=25)
        
        # Alarm section
        st.markdown("### ⏰ Set Alarm")
        use_alarm = st.checkbox("Add alarm reminder")
        
        if use_alarm:
            alarm_time = st.time_input("Alarm time", value=datetime.now().time())
            st.info(f"Alarm will ring at {alarm_time.strftime('%I:%M %p')}")
        
        if st.button("Create Habit", use_container_width=True, type="primary"):
            if habit_name.strip():
                result = add_habit_api(habit_name, habit_description, st.session_state.user["user_id"])
                if result.get("success"):
                    if use_alarm:
                        set_alarm(habit_name, alarm_time)
                        st.success(f"Habit created! 🎉 Alarm set for {alarm_time.strftime('%I:%M %p')}")
                    else:
                        st.success("Habit created! 🌟")
                    
                    # Reload user data and refresh today's habits
                    load_user_data(st.session_state.user["user_id"])
                    load_fresh_habits()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Failed to create habit")
            else:
                st.warning("Please enter a habit name")
        
        st.markdown('</div>', unsafe_allow_html=True)

def my_habits_page():
    apply_cartoon_styles()
    check_alarms()
    initialize_daily_habits()
    
    st.markdown("# Today's Fresh Habits")
    
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
        
        st.markdown(f'<div class="{bubble_class}">', unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.write(f"**{habit['name']}**")
            if habit.get("description"):
                st.write(f"_{habit['description']}_")
            if completed:
                st.write("✅ **Completed**")
            if timer_active:
                timer_data = st.session_state.active_timers[habit["habit_id"]]
                elapsed = datetime.now() - timer_data["start_time"]
                st.write(f"⏱️ **Timer:** {format_time(elapsed.total_seconds())}")
            if has_alarm:
                alarm_time = st.session_state.alarms[habit["name"]]["alarm_time"]
                st.write(f"⏰ **Alarm:** {alarm_time.strftime('%I:%M %p')}")
        
        with col2:
            if not completed:
                if timer_active:
                    if st.button("Stop", key=f"stop_{habit['habit_id']}", use_container_width=True):
                        duration = stop_timer(habit["habit_id"])
                        if duration:
                            complete_habit_in_db(habit["habit_id"], int(duration.total_seconds()))
                            load_fresh_habits()  # Refresh today's habits
                        st.rerun()
                else:
                    if st.button("Start", key=f"start_{habit['habit_id']}", use_container_width=True):
                        start_timer(habit["name"], habit["habit_id"])
                        st.rerun()
        
        with col3:
            if not completed and not timer_active:
                if st.button("Complete", key=f"comp_{habit['habit_id']}", use_container_width=True, type="primary"):
                    complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    load_fresh_habits()  # Refresh today's habits
                    load_user_data(st.session_state.user["user_id"])  # Update charts
                    st.success("Habit completed! 🎉")
                    time.sleep(1)
                    st.rerun()
        
        with col4:
            if st.button("Delete", key=f"del_{habit['habit_id']}", use_container_width=True):
                remove_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                st.session_state.deleted_habits.add(habit["habit_id"])
                load_fresh_habits()  # Refresh today's habits
                load_user_data(st.session_state.user["user_id"])  # Update charts
                st.success("Habit deleted")
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def today_status_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    st.markdown("# Today's Progress & Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Today's Summary")
        
        today_data = today_status_api(st.session_state.user["user_id"])
        if today_data.get("success"):
            total_habits = today_data["total_habits"]
            completed_habits = today_data["completed_habits"]
            
            if total_habits > 0:
                progress = (completed_habits / total_habits) * 100
                
                st.metric("Completed Habits", f"{completed_habits}/{total_habits}")
                st.metric("Completion Rate", f"{progress:.1f}%")
                st.progress(progress/100)
                
                # Today's pie chart
                today_distribution = get_today_habit_distribution()
                st.markdown("#### Today's Distribution")
                fig = create_today_pie_chart(today_distribution)
                if fig:
                    st.pyplot(fig)
                
                # Time tracking summary
                total_time, habit_time = get_today_time_summary()
                if total_time > 0:
                    st.metric("Total Time Tracked", format_time(total_time))
            else:
                st.info("No habits for today. Add some habits to see your progress!")
        else:
            st.error("❌ Could not load today's status")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Your Monthly Progress")
        
        # Get user's actual monthly data
        monthly_data = get_user_monthly_progress(st.session_state.user["user_id"])
        if monthly_data:
            # Create monthly chart
            fig = create_monthly_chart(monthly_data)
            if fig:
                st.pyplot(fig)
            
            # Show monthly stats based on actual user data
            current_month = datetime.now().strftime("%B")
            avg_completion = sum(day['completion_rate'] for day in monthly_data) / len(monthly_data)
            best_day = max(monthly_data, key=lambda x: x['completion_rate'])
            
            st.metric(f"Your Average ({current_month})", f"{avg_completion:.1f}%")
            st.metric("Your Best Day", f"{best_day['completion_rate']}% on {best_day['date']}")
        else:
            st.info("Track your habits to see monthly progress!")
        st.markdown('</div>', unsafe_allow_html=True)

def weekly_perf_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    st.markdown("# Weekly Report & Analytics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 🏆 Your Weekly Performance")
        
        # Get user's actual weekly data
        weekly_data = get_user_weekly_performance(st.session_state.user["user_id"])
        if weekly_data:
            cols = st.columns(2)
            with cols[0]:
                st.metric("Your Completion %", f"{weekly_data.get('completion_pct',0):.1f}%")
            with cols[1]:
                st.metric("Stars Earned", f"{weekly_data.get('stars',0)}/5")
            
            # Create weekly chart based on real data
            completion_rates = [day['completion_rate'] for day in weekly_data['daily_completion']]
            fig = create_weekly_chart(weekly_data)
            if fig:
                st.pyplot(fig)
            
            # Show daily breakdown
            st.markdown("#### Daily Breakdown")
            for day in weekly_data['daily_completion']:
                st.write(f"**{day['date'].strftime('%A')}**: {day['completed_habits']}/{day['total_habits']} habits ({day['completion_rate']:.1f}%)")
            
            # Achievement messages based on actual performance
            stars = weekly_data.get('stars', 0)
            if stars == 5:
                st.success("🌟 Perfect week — you're a habit superstar!")
            elif stars >= 4:
                st.success("🎯 Amazing performance — keep up the great work!")
            elif stars >= 3:
                st.info("💪 Solid week — you're building strong habits!")
            elif stars >= 2:
                st.info("📈 Good progress — every day counts!")
            else:
                st.info("🌱 Getting started — next week will be even better!")
        else:
            st.info("📊 Complete some habits to see your weekly performance!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Your Habit Analytics")
        
        # Get user's actual habit distribution
        habit_stats = get_user_habit_distribution()
        if habit_stats:
            # Show habit statistics
            st.markdown("#### Your Top Habits This Month")
            for habit_name, stats in list(habit_stats.items())[:5]:  # Show top 5
                completion_rate = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0
                st.write(f"**{habit_name}**: {stats['completed']}/{stats['total']} completed ({completion_rate:.1f}%)")
            
            # Weekly comparison
            st.markdown("#### Week Over Week")
            current_week = get_user_weekly_performance(st.session_state.user["user_id"])
            last_week_date = datetime.now().date() - timedelta(days=7)
            # In a real app, you'd fetch last week's data from the database
            
            if current_week['completion_pct'] > 0:
                st.metric("This Week's Completion", f"{current_week['completion_pct']:.1f}%")
        else:
            st.info("Add and complete habits to see your analytics!")
        
        # Alarm history
        if st.session_state.alarm_history:
            st.markdown("### 🔔 Recent Alarms")
            for alarm in st.session_state.alarm_history[-5:]:  # Show last 5 alarms
                st.write(f"**{alarm['habit_name']}** - {alarm['triggered_at'].strftime('%I:%M %p')}")
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
    
    # Main app navigation for logged-in users
    st.sidebar.markdown(f"""
    <div class="cartoon-card" style="text-align:center;">
        <h3>👋 Hello, {st.session_state.user['name']}!</h3>
        <p>Fresh start every day! ✨</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Active timers in sidebar
    if st.session_state.active_timers:
        st.sidebar.markdown("### ⏱️ Active Timers")
        for habit_id, timer_data in st.session_state.active_timers.items():
            elapsed = datetime.now() - timer_data["start_time"]
            st.sidebar.info(f"**{timer_data['habit_name']}**\n\n{format_time(elapsed.total_seconds())}")
    
    # Active alarms in sidebar
    active_alarms = [name for name, alarm in st.session_state.alarms.items() if not alarm["triggered"]]
    if active_alarms:
        st.sidebar.markdown("### ⏰ Active Alarms")
        for alarm_name in active_alarms:
            alarm_time = st.session_state.alarms[alarm_name]["alarm_time"]
            st.sidebar.warning(f"**{alarm_name}**\n{alarm_time.strftime('%I:%M %p')}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "auth"
        st.session_state.completed_habits = set()
        st.session_state.deleted_habits = set()
        st.session_state.today_habits = []
        st.session_state.active_timers = {}
        st.session_state.timer_history = []
        st.session_state.welcome_shown = False
        st.session_state.alarms = {}
        st.session_state.alarm_history = []
        st.session_state.user_habits_data = []
        st.session_state.user_monthly_data = []
        st.session_state.last_reset_date = None
        st.rerun()
    
    st.sidebar.markdown("### Navigation")
    pages = {
        "🏠 Home": home_page,
        "📝 Today's Habits": my_habits_page,
        "➕ Add Habit": add_habit_page,
        "📊 Today's Progress": today_status_page,
        "📈 Weekly Report": weekly_perf_page
    }
    choice = st.sidebar.radio("Go to:", list(pages.keys()))
    pages[choice]()

if __name__ == "__main__":
    main()