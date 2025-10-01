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
        color: #e9ebff !important;
        text-align: center;
        margin-top: 0.5rem !important;
        margin-bottom: 0.75rem !important;
        letter-spacing: 0.3px;
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
        color: #E6E8F6 !important;
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
        color: #E6E8F6 !important;
        backdrop-filter: blur(10px) !important;
    }
    .habit-bubble h2 { font-size: 1.1rem !important; margin: 0 0 0.2rem 0 !important; }
    .habit-bubble h3 { font-size: 0.95rem !important; margin: 0.25rem 0 0 0 !important; font-weight: 600 !important; }
    .habit-bubble p, .habit-bubble div, .habit-bubble span { font-size: 0.92rem !important; }
    
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
        color: #E6E8F6 !important;
        backdrop-filter: blur(10px) !important;
    }
    
    .date-display {
        background: linear-gradient(180deg, rgba(138, 43, 226, 0.28), rgba(147, 112, 219, 0.14)) !important;
        border-radius: 14px !important;
        padding: 0.6rem !important;
        text-align: center !important;
        color: #F4F6FF !important;
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
        text-shadow: 2px 2px 0 #8A2BE2 !important;
        font-family: 'Comic Sans MS', cursive !important;
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
    </style>
    """, unsafe_allow_html=True)

    # Override with glassmorphism theme matching provided UI/background
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
    .main-header, h1, h2, h3, h4, h5, h6 {
        color: #E9EBFF !important; text-shadow: none !important; margin-bottom: 0.4rem !important;
        font-family: 'Poppins', 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif !important;
    }
    .cartoon-card { background: rgba(255,255,255,0.08) !important; border: 1px solid rgba(255,255,255,0.20) !important; border-radius: 18px !important; box-shadow: 0 10px 30px rgba(0,0,0,0.25), inset 0 1px 0 rgba(255,255,255,0.12) !important; backdrop-filter: blur(12px) saturate(120%) !important; -webkit-backdrop-filter: blur(12px) saturate(120%) !important; color: #E6E8F6 !important; padding: 1.25rem !important; }
    .habit-bubble { background: linear-gradient(180deg, rgba(255,255,255,0.10), rgba(255,255,255,0.06)) !important; border: 1px solid rgba(255,255,255,0.18) !important; border-radius: 16px !important; color:#E6E8F6 !important; backdrop-filter: blur(10px) !important; }
    .habit-bubble h2 { font-size: 1.1rem !important; margin: 0 0 0.2rem 0 !important; }
    .habit-bubble h3 { font-size: 0.95rem !important; margin: 0.25rem 0 0 0 !important; font-weight: 600 !important; }
    .habit-bubble p, .habit-bubble div, .habit-bubble span { font-size: 0.92rem !important; }
    .habit-completed { background: linear-gradient(180deg, rgba(76, 175, 80, 0.20), rgba(139,195,74,0.12)) !important; border: 1px solid rgba(182,255,182,0.30) !important; color:#E9FFEA !important; }
    .metric-card { background: rgba(255,255,255,0.07) !important; border: 1px solid rgba(255,255,255,0.18) !important; color:#E6E8F6 !important; backdrop-filter: blur(10px) !important; }
    .date-display { background: linear-gradient(180deg, rgba(138,43,226,0.28), rgba(147,112,219,0.14)) !important; border:1px solid rgba(255,255,255,0.18) !important; color:#F4F6FF !important; }
    .stButton > button { border-radius:12px !important; border:1px solid rgba(255,255,255,0.25) !important; background: linear-gradient(180deg, rgba(147,124,255,0.30), rgba(147,124,255,0.18)) !important; color:#fff !important; font-weight:600 !important; box-shadow:0 8px 20px rgba(147,124,255,0.25) !important; backdrop-filter: blur(8px) saturate(120%) !important; }
    .stButton > button:hover { transform: translateY(-1px) !important; box-shadow:0 10px 24px rgba(147,124,255,0.35) !important; }

    /* Floating Action Button centered bottom */
    .fab-wrap { position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%); z-index: 1000; }
    .fab-wrap .stButton > button { width:60px !important; height:60px !important; border-radius:50% !important; padding:0 !important; font-size:30px !important; line-height:1 !important; background:linear-gradient(135deg,#8866ff 0%, #6a4bff 100%) !important; box-shadow:0 14px 30px rgba(104,82,255,.45) !important; border:0 !important; }

    /* Large '+' hero for Add Habit */
    .plus-hero { display:flex; align-items:center; justify-content:center; height:58vh; position:relative; z-index:1; }
    .plus-hero .hint { position:absolute; bottom:18%; color:#E9EBFF; opacity:.8; }

    /* Auth layout like reference */
    .auth-wrap { display:flex; gap: 22px; align-items: stretch; justify-content:center; margin: 18px auto 8px auto; max-width: 950px; }
    .auth-left { flex: 1 1 48%; background: var(--logoDark, #5a49cc); color:#fff; border-radius: 18px; padding: 26px 28px; position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
    .auth-left h2 { margin: 0 0 8px 0; font-size: 1.6rem; }
    .auth-left p { margin: 0 0 16px 0; opacity:.95; }
    .auth-left .corner { position:absolute; right:0; top:0; width:120px; height:120px; background: rgba(255,255,255,0.18); border-bottom-left-radius: 100px; border-top-right-radius: 18px; }
    .auth-right { flex: 1 1 52%; background: #ffffff; color:#333; border-radius: 18px; padding: 22px 22px; box-shadow: 0 10px 30px rgba(0,0,0,0.25); }
    .auth-right.bright { background:#ffffff; box-shadow: 0 14px 34px rgba(106,75,255,0.35); border: 1px solid rgba(106,75,255,0.25); }
    .auth-right h3 { margin: 0 0 12px 0; font-weight: 700; color:#252a41; }
    .auth-right .stTextInput input, .auth-right .stTextArea textarea { background:#f5f6fa; border-radius:10px; height:32px; font-size:0.92rem; padding:4px 8px; }
    .auth-right .stTextInput > div > div, .auth-right .stTextArea > div > div { width: 260px !important; }
    .auth-right .stTextInput, .auth-right .stTextArea, .auth-right .stButton { display:block; margin-left:auto; margin-right:auto; }
    .auth-right .stButton > button { width: 260px !important; height: 34px !important; border-radius:10px !important; font-size:0.95rem !important; }
    @media (max-width: 900px) { .auth-wrap { flex-direction: column; max-width: 560px; } }
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

# -------------------------------
# TIMER FUNCTIONS
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
# AUTH PAGE
# -------------------------------
def auth_page():
    apply_cartoon_styles()
    logo_path = resolve_logo_path()
    logo_color = get_logo_dominant_color(logo_path) if logo_path else "#6a4bff"
    darkest_logo = darken_hex(logo_color, 0.5)

    # Left panel: Welcome, switch to Register
    st.markdown(f"""
    <div class="auth-wrap">
        <div class="auth-left" style="--logoDark: {darkest_logo}; background:{darkest_logo};">
            <div class="corner"></div>
            <h2>Hello, Welcome!</h2>
            <p>Don't have an account?</p>
            <div>
                <button id="go-register" style="background:#ffffff; color:{darkest_logo}; padding:10px 16px; border:0; border-radius:10px; font-weight:700; cursor:pointer;">Register</button>
            </div>
        </div>
        <div class="auth-right">
            <h3>{'Register' if st.session_state.auth_mode == 'register' else 'Login'}</h3>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Wire up buttons using Streamlit buttons
    colA, colB = st.columns([1,1])
    with colA:
        if st.button("I want to Register", key="swap_to_register"):
            st.session_state.auth_mode = "register"
            st.rerun()
    with colB:
        if st.button("I want to Login", key="swap_to_login"):
            st.session_state.auth_mode = "login"
            st.rerun()

    # Render the form card under the header to align with design
    st.markdown('<div class="auth-wrap" style="margin-top: 0;">', unsafe_allow_html=True)
    right_class = "auth-right bright" if st.session_state.auth_mode == "register" else "auth-right"
    st.markdown(f'<div class="{right_class}">', unsafe_allow_html=True)
    if st.session_state.auth_mode == "login":
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn", use_container_width=True):
            if login_email and login_password:
                result = login_api(login_email, login_password)
                if result.get("success"):
                    st.session_state.user = {
                        "user_id": result["user_id"],
                        "name": result["name"],
                        "email": login_email
                    }
                    st.session_state.page = "home"
                    st.success("Logged in")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Invalid credentials")
            else:
                st.warning("Fill all fields")
    else:
        reg_name = st.text_input("Name")
        reg_email = st.text_input("Email")
        reg_password = st.text_input("Password", type="password")
        if st.button("Create Account", key="register_btn", use_container_width=True):
            if reg_name and reg_email and reg_password:
                result = register_api(reg_name, reg_email, reg_password)
                if result.get("success"):
                    st.session_state.user = {
                        "user_id": result["user_id"],
                        "name": result["name"],
                        "email": reg_email
                    }
                    st.session_state.page = "home"
                    st.success("Welcome!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Registration failed")
            else:
                st.warning("Fill all fields")
    st.markdown('</div>', unsafe_allow_html=True)  # close auth-right
    st.markdown('</div>', unsafe_allow_html=True)  # close auth-wrap

# -------------------------------
# MAIN APP PAGES
# -------------------------------
def home_page():
    apply_cartoon_styles()
    
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
            <h1 style="font-size:2.2rem; margin:0; color:#3b3f5c;">
                {greeting}, {st.session_state.user['name']}!
            </h1>
        </div>
        <div class="date-display slide-in" style="background:#fff; color:#3b3f5c;">
            <h3 style="margin:0;">{today_str}</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Today's Progress")

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
                    <h3>Progress</h3>
                    <h2>{completed_habits}/{total_habits}</h2>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                progress = (completed_habits/total_habits*100) if total_habits > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Completion Rate</h3>
                    <h2>{progress:.0f}%</h2>
                </div>
                """, unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>Remaining</h3>
                    <h2>{total_habits - completed_habits}</h2>
                </div>
                """, unsafe_allow_html=True)

            st.progress(progress/100)
            
            # Show completion message (no balloons)
            if completed_habits == total_habits and total_habits > 0:
                st.success("All done for today!")
            elif completed_habits > 0:
                st.info(f"Great job! You've completed {completed_habits} today.")
        else:
            st.markdown("""
            <div class="cartoon-card" style="text-align:center;">
                <h3>No habits yet</h3>
                <p>Add your first habit to get started.</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("❌ Could not load today's status")

def add_habit_page():
    apply_cartoon_styles()
    st.markdown('<div style="display:flex; justify-content:center;">', unsafe_allow_html=True)
    st.markdown('<div class="cartoon-card" style="max-width:520px; width:100%">', unsafe_allow_html=True)
    st.markdown("### Add New Habit")
    habit_name = st.text_input("Habit Name", placeholder="e.g., Morning Run")
    habit_description = st.text_area("Description (optional)", placeholder="Add notes or goals…")
    target_minutes = st.number_input("Planned Time (minutes)", min_value=5, max_value=600, step=5, value=30)
    if st.button("Save Habit", use_container_width=True):
        if habit_name.strip():
            # capture ids before
            before_ids = set([h.get("habit_id") for h in list_habits_api(st.session_state.user["user_id"])])
            result = add_habit_api(habit_name, habit_description, st.session_state.user["user_id"])
            if result.get("success"):
                st.session_state.show_success = True
                st.success("Habit added")
                # map new habit id to target seconds
                new_list = list_habits_api(st.session_state.user["user_id"]) or []
                after_ids = set([h.get("habit_id") for h in new_list])
                new_ids = list(after_ids - before_ids)
                mapped = False
                for h in new_list:
                    if h.get("habit_id") in new_ids or h.get("name") == habit_name:
                        st.session_state.habit_targets[h["habit_id"]] = int(target_minutes) * 60
                        mapped = True
                        break
                if not mapped and new_list:
                    st.session_state.habit_targets[new_list[-1]["habit_id"]] = int(target_minutes) * 60
                time.sleep(1)
                st.rerun()
            else:
                st.error("Failed to add habit")
        else:
            st.warning("Please enter a habit name")
    st.markdown('</div>', unsafe_allow_html=True)

def my_habits_page():
    apply_cartoon_styles()
    st.markdown("# Today's Habits")
    
    # Refresh today's habits
    today_data = today_status_api(st.session_state.user["user_id"])
    if today_data.get("success"):
        st.session_state.today_habits = today_data["habits"]
    
    habits = st.session_state.today_habits
    if not habits:
        st.info("No active habits for today.")
        return
    
    for habit in habits:
        if habit["habit_id"] in st.session_state.deleted_habits:
            continue
            
        completed = habit.get("completed", False)
        timer_active = habit["habit_id"] in st.session_state.active_timers
        
        bubble_class = "habit-bubble habit-completed" if completed else "habit-bubble"
        if timer_active:
            bubble_class += " timer-active"
        
        st.markdown(f'<div class="{bubble_class}">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.write(f"#### {habit['name']}")
            if habit.get("description"):
                st.write(f"_{habit['description']}_")
            if completed:
                st.markdown("##### Completed")
            if timer_active:
                start_time = st.session_state.active_timers[habit["habit_id"]]["start_time"]
                elapsed = datetime.now() - start_time
                target = st.session_state.habit_targets.get(habit["habit_id"]) 
                if target:
                    acc_before = get_accumulated_seconds_today(habit["habit_id"])  # time logged today (excluding current run)
                    remaining = max(0, target - (acc_before + int(elapsed.total_seconds())))
                    st.markdown(f"##### Timer: {format_time(elapsed.total_seconds())} • Left: {format_time(remaining)}")
                else:
                    st.markdown(f"##### Timer: {format_time(elapsed.total_seconds())}")
        
        with col2:
            if not completed:
                if habit["habit_id"] in st.session_state.active_timers:
                    if st.button("Stop", key=f"stop_{habit['habit_id']}", use_container_width=True):
                        duration = stop_timer(habit["habit_id"])
                        if duration:
                            elapsed_secs = int(duration.total_seconds())
                            target = st.session_state.habit_targets.get(habit["habit_id"]) 
                            acc = get_accumulated_seconds_today(habit["habit_id"])  # includes new stop
                            # above function sums after stop because we append to history in stop_timer
                            if target and acc < target:
                                remaining = target - acc
                                st.warning(f"Keep going — remaining {format_time(remaining)}")
                            elif target and acc >= target:
                                st.success("Target met for today!")
                                render_beep()
                            else:
                                st.info(f"Timer stopped. Time spent: {format_time(elapsed_secs)}")
                            time.sleep(1)
                            st.rerun()
                else:
                    if st.button("Start Timer", key=f"start_{habit['habit_id']}", use_container_width=True, type="secondary"):
                        start_timer(habit["name"], habit["habit_id"])
                        st.success(f"Timer started for {habit['name']}")
                        time.sleep(1)
                        st.rerun()
        
        with col3:
            if not completed:
                if st.button("Complete", key=f"comp_{habit['habit_id']}", use_container_width=True):
                    res = complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    if res.get("success"):
                        st.session_state.completed_habits.add(habit["habit_id"])
                        st.success("Habit marked completed")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed to complete habit")
            
            if st.button("Delete", key=f"del_{habit['habit_id']}", use_container_width=True):
                remove_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                st.session_state.deleted_habits.add(habit["habit_id"])
                st.success("Habit deleted")
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def today_status_page():
    apply_cartoon_styles()
    st.markdown("# Today's Status")
    
    # Time tracking summary
    # Show summary only at end of day
    now = datetime.now()
    if now.hour < 23:
        st.info("Today's progress will be generated at the end of the day.")
        return
    total_time, habit_time = get_today_time_summary()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### Time Tracking Summary")
        
        if total_time > 0:
            st.metric("Total Time Tracked Today", format_time(total_time))
            
            st.markdown("### Time by Activity")
            for habit_name, time_seconds in habit_time.items():
                st.write(f"**{habit_name}**: {format_time(time_seconds)}")
        else:
            st.info("No time tracked today.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### Habit Completion Status")
        
        today_data = today_status_api(st.session_state.user["user_id"])
        if today_data.get("success"):
            total_habits = today_data["total_habits"]
            completed_habits = today_data["completed_habits"]
            
            if total_habits > 0:
                st.metric("Completed", completed_habits)
                st.metric("Remaining", total_habits - completed_habits)
                st.metric("Total Habits", total_habits)
                
                progress = completed_habits / total_habits
                st.progress(progress)
                
                # Motivational messages (no balloons)
                if progress == 1:
                    st.success("All habits completed today")
                elif progress >= 0.8:
                    st.success("Great work — almost there")
                elif progress >= 0.5:
                    st.info("Good progress — halfway there")
                elif progress > 0:
                    st.info("Good start — keep going")
                else:
                    st.info("🌱 Ready to begin your adventure? You've got this!")
            else:
                st.info("No habits for today.")
        else:
            st.error("❌ Could not load today's status")
        st.markdown('</div>', unsafe_allow_html=True)

def weekly_perf_page():
    apply_cartoon_styles()
    st.markdown("# Weekly Report")
    # Only generate weekly report at end of week (Sunday)
    if datetime.now().date().weekday() != 6:
        st.info("Weekly report will be available on Sunday.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        data = weekly_perf_api(st.session_state.user["user_id"])
        if data and data.get("success"):
            cols = st.columns(2)
            with cols[0]:
                st.metric("🏆 Completion %", f"{data.get('completion_pct',0)}%")
            with cols[1]:
                st.metric("⭐ Stars Earned", f"{data.get('stars',0)}/5")
            
            # Fun achievement messages
            stars = data.get('stars', 0)
            if stars == 5:
                st.success("Perfect week — well done!")
            elif stars >= 4:
                st.success("Amazing performance!")
            elif stars >= 3:
                st.info("Great job — keep it up")
            elif stars >= 2:
                st.info("Good progress — every day counts")
            else:
                st.info("Getting started — next week will be better")
        else:
            st.info("📊 No weekly data yet. Complete some quests first!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Weekly Time Distribution")
        
        # Get this week's timer data
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        week_sessions = [session for session in st.session_state.timer_history 
                        if session["date"] >= start_of_week]
        
        if week_sessions:
            # Group by habit
            habit_time_week = {}
            for session in week_sessions:
                habit_name = session["habit_name"]
                if habit_name not in habit_time_week:
                    habit_time_week[habit_name] = 0
                habit_time_week[habit_name] += session["duration"].total_seconds()
            
            # Create pie chart
            if habit_time_week:
                fig, ax = plt.subplots(figsize=(8, 6))
                colors = ['#FF8E53', '#FE6B8B', '#8A2BE2', '#9370DB', '#FFD700']
                wedges, texts, autotexts = ax.pie(
                    list(habit_time_week.values()), 
                    labels=list(habit_time_week.keys()),
                    autopct='%1.1f%%',
                    colors=colors[:len(habit_time_week)],
                    startangle=90
                )
                
                # Style the chart
                plt.setp(autotexts, size=10, weight="bold", color="white")
                plt.setp(texts, size=10)
                ax.set_title('Time Spent on Activities This Week', fontsize=14, fontweight='bold', color='#333333')
                
                st.pyplot(fig)
            else:
                st.info("⏰ No time data for this week yet.")
        else:
            st.info("📈 Start using timers to see your weekly time distribution!")
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
        <p>Ready for today's adventure? 🎯</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Active timers in sidebar
    if st.session_state.active_timers:
        st.sidebar.markdown("### ⏱️ Active Timers")
        for habit_id, timer_data in st.session_state.active_timers.items():
            elapsed = datetime.now() - timer_data["start_time"]
            st.sidebar.info(f"**{timer_data['habit_name']}**\n\n{format_time(elapsed.total_seconds())}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.user = None
        st.session_state.page = "auth"
        st.session_state.completed_habits = set()
        st.session_state.deleted_habits = set()
        st.session_state.today_habits = []
        st.session_state.active_timers = {}
        st.session_state.timer_history = []
        st.session_state.welcome_shown = False
        st.rerun()
    
    st.sidebar.markdown("### Navigation")
    pages = {
        "Home": home_page,
        "Today's Habits": my_habits_page,
        "Add Habit": add_habit_page,
        "Today's Progress": today_status_page,
        "Weekly Report": weekly_perf_page
    }
    choice = st.sidebar.radio("Choose:", list(pages.keys()), key="nav_choice")
    pages[choice]()

# FAB removed

if __name__ == "__main__":
    main()