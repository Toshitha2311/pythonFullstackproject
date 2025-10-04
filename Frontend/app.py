import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
import pandas as pd
import os
import base64
import numpy as np
import threading
import pygame

API_URL = "http://127.0.0.1:8000"

# Initialize pygame mixer
pygame.mixer.init()

# Set page config must be the first Streamlit command
st.set_page_config(
    page_title="HabitHub", 
    layout="wide", 
    page_icon="🎯",
    initial_sidebar_state="expanded"
)

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
    st.session_state.user_alarms = {}  # Persistent alarms per user
if "alarm_threads" not in st.session_state:
    st.session_state.alarm_threads = {}

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

def add_habit_api(name, desc, user_id, target_minutes=25):
    resp = requests.post(f"{API_URL}/habit/add", 
                        json={"name": name, "description": desc, "user_id": user_id, "target_minutes": target_minutes})
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
# ALARM FUNCTIONS (PYGAME BASED)
# -------------------------------
def play_alarm_sound():
    """Play alarm sound using pygame."""
    try:
        # Create a simple beep sound using pygame
        pygame.mixer.init()
        sample_rate = 44100
        duration = 1000  # milliseconds
        frequency = 800  # Hz
        
        # Generate beep sound
        n_samples = int(round(duration * 0.001 * sample_rate))
        buf = numpy.zeros((n_samples, 2), dtype=numpy.int16)
        max_sample = 2**(16 - 1) - 1
        for s in range(n_samples):
            t = float(s) / sample_rate
            buf[s][0] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
            buf[s][1] = int(round(max_sample * math.sin(2 * math.pi * frequency * t)))
        
        sound = pygame.sndarray.make_sound(buf)
        sound.play()
        pygame.time.wait(duration)
        
    except Exception as e:
        # Fallback to JavaScript if pygame fails
        st.markdown("""
        <script>
        function playAlarmSound() {
            try {
                const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                const oscillator = audioContext.createOscillator();
                const gainNode = audioContext.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioContext.destination);
                
                const startTime = audioContext.currentTime;
                
                // First high-pitched beep
                oscillator.frequency.setValueAtTime(800, startTime);
                gainNode.gain.setValueAtTime(0.8, startTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + 0.3);
                
                // Second medium-pitched beep
                oscillator.frequency.setValueAtTime(600, startTime + 0.4);
                gainNode.gain.setValueAtTime(0.8, startTime + 0.4);
                gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + 0.7);
                
                // Third high-pitched beep
                oscillator.frequency.setValueAtTime(800, startTime + 0.8);
                gainNode.gain.setValueAtTime(0.8, startTime + 0.8);
                gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + 1.1);
                
                oscillator.start(startTime);
                oscillator.stop(startTime + 1.2);
                
            } catch(e) {
                console.log('Web Audio failed:', e);
            }
        }
        playAlarmSound();
        </script>
        """, unsafe_allow_html=True)

def schedule_alarm(habit_name, alarm_time):
    """Schedule alarm for today + repeat daily."""
    def alarm_thread():
        while True:
            now = datetime.now()
            current_time_str = now.time().strftime("%H:%M")
            target_time_str = alarm_time.strftime("%H:%M")
            
            if current_time_str == target_time_str:
                st.toast(f"⏰ Alarm for '{habit_name}' is ringing!")
                play_alarm_sound()
                
                # Record alarm history
                st.session_state.alarm_history.append({
                    "habit_name": habit_name,
                    "alarm_time": alarm_time,
                    "triggered_at": now
                })
                
                time.sleep(60)  # wait 1 min so it doesn't keep firing
            time.sleep(20)  # check every 20 sec

    # Run thread in background
    t = threading.Thread(target=alarm_thread, daemon=True)
    t.start()
    return datetime.now().replace(
        hour=alarm_time.hour, minute=alarm_time.minute, second=0, microsecond=0
    )

# -------------------------------
# PERSISTENT ALARM MANAGEMENT
# -------------------------------
def save_user_alarms():
    """Save alarms for the current user"""
    if st.session_state.user:
        user_id = st.session_state.user["user_id"]
        # Convert datetime objects to strings for storage
        alarms_to_save = {}
        for habit_name, alarm in st.session_state.alarms.items():
            alarms_to_save[habit_name] = {
                "alarm_time": alarm["alarm_time"].strftime("%H:%M:%S"),
                "triggered": alarm["triggered"],
                "recurring": alarm["recurring"]
            }
        st.session_state.user_alarms[user_id] = alarms_to_save

def load_user_alarms():
    """Load alarms for the current user"""
    if st.session_state.user:
        user_id = st.session_state.user["user_id"]
        if user_id in st.session_state.user_alarms:
            saved_alarms = st.session_state.user_alarms[user_id]
            # Convert string times back to time objects and create datetime objects
            for habit_name, alarm_data in saved_alarms.items():
                alarm_time = datetime.strptime(alarm_data["alarm_time"], "%H:%M:%S").time()
                
                # Start the alarm thread for this alarm
                schedule_alarm(habit_name, alarm_time)
                
                st.session_state.alarms[habit_name] = {
                    "habit_name": habit_name,
                    "alarm_time": alarm_time,
                    "triggered": False,
                    "recurring": alarm_data["recurring"]
                }

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
        # Get today's habits from API - this should only return current user's habits
        today_data = today_status_api(st.session_state.user["user_id"])
        if today_data.get("success"):
            # Filter habits to ensure only current user's habits are shown
            user_habits = [habit for habit in today_data["habits"]]
            st.session_state.today_habits = user_habits
            
            # Update completed habits set
            st.session_state.completed_habits = set()
            for habit in st.session_state.today_habits:
                if habit.get("completed"):
                    st.session_state.completed_habits.add(habit["habit_id"])

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

def set_alarm(habit_name, alarm_time):
    """Set an alarm for a specific habit - PERSISTENT across logins"""
    # Start the alarm thread
    schedule_alarm(habit_name, alarm_time)
    
    st.session_state.alarms[habit_name] = {
        "habit_name": habit_name,
        "alarm_time": alarm_time,
        "triggered": False,
        "recurring": True
    }
    
    # Save alarms for persistence
    save_user_alarms()
    
    st.success(f"🔔 Alarm set for {habit_name} at {alarm_time.strftime('%I:%M %p')}!")
    return alarm_time

def remove_alarm(habit_name):
    """Remove an alarm and save changes"""
    if habit_name in st.session_state.alarms:
        del st.session_state.alarms[habit_name]
        save_user_alarms()
        st.success(f"Alarm for {habit_name} removed!")
        st.rerun()

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
# WEEKLY STARS SYSTEM
# -------------------------------
def calculate_weekly_stars():
    """Calculate stars based on weekly performance"""
    if not st.session_state.user:
        return 0
    
    weekly_data = weekly_perf_api(st.session_state.user["user_id"])
    if weekly_data.get("success"):
        completion_pct = weekly_data.get("completion_pct", 0)
        
        # Star calculation based on completion percentage
        if completion_pct >= 90:
            return 5
        elif completion_pct >= 75:
            return 4
        elif completion_pct >= 60:
            return 3
        elif completion_pct >= 40:
            return 2
        elif completion_pct >= 20:
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
        # Load user's persistent alarms
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
                    # Initialize daily habits and load user data (including alarms)
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
        <div style="background: linear-gradient(180deg, rgba(138, 43, 226, 0.28), rgba(147, 112, 219, 0.14)); border-radius: 14px; padding: 0.6rem; text-align: center; color: #ffffff; font-weight: 600; font-size: 0.95rem; margin: 0.75rem 0 1rem 0; border: 1px solid rgba(255,255,255,0.18); backdrop-filter: blur(8px);">
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
        
        # Ensure we only show current user's habits
        user_habits = [habit for habit in today_data["habits"]]
        st.session_state.today_habits = user_habits
        
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
        
        # Time target section
        st.markdown("### ⏱️ Time Target")
        target_minutes = st.slider("How many minutes do you want to spend on this habit?", 
                                 min_value=5, max_value=120, value=25, step=5,
                                 help="Set your target time for this habit")
        
        st.info(f"🎯 Target: {target_minutes} minutes per session")
        
        # Alarm section
        st.markdown("### ⏰ Set Daily Alarm")
        use_alarm = st.checkbox("Add daily alarm reminder")
        
        if use_alarm:
            # Default to current time + 5 minutes for convenience
            default_time = (datetime.now() + timedelta(minutes=5)).time()
            alarm_time = st.time_input("Alarm time", value=default_time, key="alarm_time_picker")
            
            if alarm_time:
                alarm_datetime = set_alarm(habit_name, alarm_time)
                st.info("Alarm will ring at this time every day and persist across logins")
        
        if st.button("Create Habit", use_container_width=True, type="primary"):
            if habit_name.strip():
                result = add_habit_api(habit_name, habit_description, st.session_state.user["user_id"], target_minutes)
                if result.get("success"):
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
    initialize_daily_habits()
    
    st.markdown("# Today's Fresh Habits")
    
    # Only show habits for the current logged-in user
    habits = st.session_state.today_habits
    if not habits:
        st.info("No habits for today. Add some habits to get started! 🌟")
        return
    
    # Show fresh start message if it's a new day
    today = datetime.now().date()
    if st.session_state.last_reset_date == today and len(habits) > 0:
        st.success("✨ Fresh start for today! All habits are new. ✨")
    
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
                    st.success("🎉 Target time reached! Habit completed!")
                    complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    play_completion_sound()
                    load_fresh_habits()
                    st.rerun()
                    
            if has_alarm:
                alarm_time = st.session_state.alarms[habit["name"]]["alarm_time"]
                st.write(f"⏰ **Alarm:** {alarm_time.strftime('%I:%M %p')} daily")
        
        with col2:
            if not completed:
                if timer_active:
                    if st.button("Stop", key=f"stop_{habit['habit_id']}", use_container_width=True):
                        duration = stop_timer(habit["habit_id"])
                        if duration:
                            # Play completion sound when manually stopped
                            play_completion_sound()
                            # Auto-complete when timer stops
                            complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                            load_fresh_habits()
                        st.rerun()
                else:
                    if st.button("Start", key=f"start_{habit['habit_id']}", use_container_width=True):
                        start_timer(habit["name"], habit["habit_id"], target_minutes)
                        st.rerun()
        
        with col3:
            if not completed and not timer_active:
                if st.button("Complete", key=f"comp_{habit['habit_id']}", use_container_width=True, type="primary"):
                    complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    play_completion_sound()
                    load_fresh_habits()
                    load_user_data(st.session_state.user["user_id"])
                    st.success("Habit completed! 🎉")
                    time.sleep(1)
                    st.rerun()
        
        with col4:
            if st.button("Delete", key=f"del_{habit['habit_id']}", use_container_width=True):
                remove_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                st.session_state.deleted_habits.add(habit["habit_id"])
                load_fresh_habits()
                load_user_data(st.session_state.user["user_id"])
                st.success("Habit deleted")
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def today_status_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    st.markdown("# Today's Progress")
    
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
                
                st.metric("Total Habits", f"{total_habits}")
                st.metric("Completed Today", f"{completed_habits}")
                st.metric("Today's Progress", f"{progress:.1f}%")
                st.progress(progress/100)
                
                # Today's pie chart with BEAUTIFUL GRADIENT COLORS
                today_distribution = get_today_habit_distribution()
                st.markdown("#### Today's Distribution")
                fig = create_today_pie_chart(today_distribution)
                if fig:
                    st.pyplot(fig)
            else:
                st.info("No habits for today. Add some habits to see your progress!")
        else:
            st.error("❌ Could not load today's status")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 🔔 Alarm Management")
        
        # Active alarms
        active_alarms = [name for name, alarm in st.session_state.alarms.items()]
        if active_alarms:
            st.markdown("#### ⏰ Active Alarms")
            for alarm_name in active_alarms:
                alarm_data = st.session_state.alarms[alarm_name]
                alarm_time = alarm_data["alarm_time"]
                st.write(f"**{alarm_name}**: {alarm_time.strftime('%I:%M %p')} daily")
                
                # Add option to remove alarm
                if st.button(f"Remove {alarm_name} alarm", key=f"remove_{alarm_name}"):
                    remove_alarm(alarm_name)
        else:
            st.info("No active alarms. Set alarms in 'Add Habit' page.")
        
        # Alarm history
        st.markdown("#### 📋 Recent Alarms")
        if st.session_state.alarm_history:
            for alarm in st.session_state.alarm_history[-5:]:
                st.write(f"**{alarm['habit_name']}** - {alarm['triggered_at'].strftime('%I:%M %p')}")
        else:
            st.info("No alarm history yet.")
        
        st.markdown('</div>', unsafe_allow_html=True)

def weekly_perf_page():
    apply_cartoon_styles()
    initialize_daily_habits()
    
    st.markdown("# Weekly Report & Stars")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Your Weekly Performance")
        
        # Get weekly data from API
        weekly_data = weekly_perf_api(st.session_state.user["user_id"])
        if weekly_data.get("success"):
            completion_pct = weekly_data.get("completion_pct", 0)
            total_habits = weekly_data.get("total_habits", 0)
            completed_habits = weekly_data.get("completed_habits", 0)
            
            cols = st.columns(2)
            with cols[0]:
                st.metric("Weekly Completion", f"{completion_pct:.1f}%")
            with cols[1]:
                st.metric("Habits Completed", f"{completed_habits}/{total_habits}")
            
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
        st.markdown("### 📊 Star System Guide")
        
        st.markdown("""
        #### How Stars Are Earned:
        
        ⭐⭐⭐⭐⭐ **5 Stars** - 90%+ completion  
        ⭐⭐⭐⭐ **4 Stars** - 75%+ completion  
        ⭐⭐⭐ **3 Stars** - 60%+ completion  
        ⭐⭐ **2 Stars** - 40%+ completion  
        ⭐ **1 Star** - 20%+ completion  
        ☆ **0 Stars** - Below 20% completion
        
        #### Tips for More Stars:
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
            next_threshold = [20, 40, 60, 75, 90][current_stars]
            st.info(f"Aim for **{next_threshold}%** completion to reach **{current_stars + 1} stars** this week!")
        else:
            st.success("🎉 You've reached the maximum stars! Maintain your excellent performance!")
        
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
        <p>Weekly Stars: {st.session_state.weekly_stars}/5 ⭐</p>
        <p>Fresh start every day! ✨</p>
    </div>
    """, unsafe_allow_html=True)
    
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
        st.sidebar.markdown("### ⏰ Active Alarms")
        for alarm_name in active_alarms:
            alarm_time = st.session_state.alarms[alarm_name]["alarm_time"]
            st.sidebar.warning(f"**{alarm_name}**\n{alarm_time.strftime('%I:%M %p')} daily")
    
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
        st.rerun()
    
    st.sidebar.markdown("### Navigation")
    pages = {
        "🏠 Home": home_page,
        "📝 Today's Habits": my_habits_page,
        "➕ Add Habit": add_habit_page,
        "📊 Today's Progress": today_status_page,
        "⭐ Weekly Report": weekly_perf_page
    }
    choice = st.sidebar.radio("Go to:", list(pages.keys()))
    pages[choice]()

if __name__ == "__main__":
    main()