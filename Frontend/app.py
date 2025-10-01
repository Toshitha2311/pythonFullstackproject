import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
import pandas as pd

API_URL = "http://127.0.0.1:8000"

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

# -------------------------------
# CARTOON STYLING WITH ORANGE/VIOLET/WHITE THEME
# -------------------------------
def apply_cartoon_styles():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #FF8E53 0%, #FE6B8B 55%, #FF8E53 100%) !important;
        font-family: 'Comic Sans MS', 'Chalkboard SE', 'Marker Felt', sans-serif !important;
    }
    
    .main-header {
        font-family: 'Comic Sans MS', cursive !important;
        font-size: 3rem !important;
        color: #FFFFFF !important;
        text-shadow: 3px 3px 0 #8A2BE2, 6px 6px 0 #FF8E53;
        text-align: center;
        margin-bottom: 2rem !important;
        animation: bounce 2s infinite;
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
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 25px !important;
        border: 5px solid #8A2BE2 !important;
        padding: 2rem !important;
        margin: 1rem 0 !important;
        box-shadow: 10px 10px 0 #FF8E53 !important;
        transition: all 0.3s ease !important;
        animation: fadeIn 0.8s ease-in;
        color: #333333 !important;
    }
    
    .habit-bubble {
        background: linear-gradient(45deg, #FF8E53, #FE6B8B) !important;
        border-radius: 20px !important;
        padding: 1.5rem !important;
        margin: 1rem 0 !important;
        border: 4px solid #FFFFFF !important;
        box-shadow: 5px 5px 0 #8A2BE2 !important;
        transition: all 0.3s ease !important;
        animation: slideIn 0.6s ease-out;
        color: #FFFFFF !important;
    }
    
    .habit-completed {
        background: linear-gradient(45deg, #4CAF50, #8BC34A) !important;
        border: 4px solid #FFFFFF !important;
        animation: pulse 2s infinite;
        color: #FFFFFF !important;
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
        border-radius: 20px !important;
        border: 3px solid #8A2BE2 !important;
        background: linear-gradient(45deg, #FF8E53, #FE6B8B) !important;
        color: white !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
        padding: 0.8rem 2rem !important;
        box-shadow: 4px 4px 0 #8A2BE2 !important;
        transition: all 0.2s ease !important;
        font-family: 'Comic Sans MS', cursive !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 6px 6px 0 #8A2BE2 !important;
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
        background: rgba(255, 255, 255, 0.9) !important;
        border-radius: 20px !important;
        border: 4px solid #FFFFFF !important;
        padding: 1.5rem !important;
        text-align: center !important;
        box-shadow: 6px 6px 0 #8A2BE2 !important;
        animation: fadeIn 1s ease-in;
        color: #333333 !important;
    }
    
    .date-display {
        background: linear-gradient(45deg, #8A2BE2, #9370DB) !important;
        border-radius: 15px !important;
        padding: 1rem !important;
        text-align: center !important;
        color: white !important;
        font-weight: bold !important;
        margin: 1rem 0 !important;
        animation: fadeIn 1.2s ease-in;
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
# AUTH PAGE
# -------------------------------
def auth_page():
    apply_cartoon_styles()
    st.markdown('<div class="main-header">🎯 HabitHub Adventure</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["🚀 Login", "🌟 Register"])
        
        with tab1:
            st.subheader("Welcome Back Adventurer! 🎮")
            login_email = st.text_input("📧 Email", key="login_email")
            login_password = st.text_input("🔑 Password", type="password", key="login_password")
            
            if st.button("🎯 Start Adventure!", key="login_btn", use_container_width=True):
                if login_email and login_password:
                    result = login_api(login_email, login_password)
                    if result.get("success"):
                        st.session_state.user = {
                            "user_id": result["user_id"],
                            "name": result["name"],
                            "email": login_email
                        }
                        st.session_state.page = "home"
                        st.session_state.welcome_shown = True
                        st.success("🎉 Login successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials! Try again!")
                else:
                    st.warning("⚠️ Please fill all fields!")
        
        with tab2:
            st.subheader("Join the Habit Adventure! 🌈")
            reg_name = st.text_input("👤 Your Adventurer Name")
            reg_email = st.text_input("📧 Email")
            reg_password = st.text_input("🔑 Password", type="password")
            
            if st.button("🌟 Begin Journey!", key="register_btn", use_container_width=True):
                if reg_name and reg_email and reg_password:
                    result = register_api(reg_name, reg_email, reg_password)
                    if result.get("success"):
                        st.session_state.user = {
                            "user_id": result["user_id"],
                            "name": result["name"],
                            "email": reg_email
                        }
                        st.session_state.page = "home"
                        st.session_state.welcome_shown = True
                        st.success("🎉 Welcome to HabitHub! Your adventure begins!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Registration failed! Maybe you're already an adventurer?")
                else:
                    st.warning("⚠️ Please fill all fields!")
        
        st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------
# MAIN APP PAGES
# -------------------------------
def home_page():
    apply_cartoon_styles()
    
    # Show welcome message only once
    if st.session_state.welcome_shown:
        st.markdown(f"""
        <div class="welcome-message">
            <h1>🎉 Welcome to HabitHub, {st.session_state.user['name']}! 🎉</h1>
            <h3>Ready to start your journey? Let's build amazing habits together! 🌟</h3>
        </div>
        """, unsafe_allow_html=True)
        st.session_state.welcome_shown = False
    
    # Animated greeting + date
    now = datetime.now()
    hour = now.hour
    if hour < 12:
        greeting = "🌅 Good Morning"
    elif hour < 18:
        greeting = "☀️ Good Afternoon"
    else:
        greeting = "🌙 Good Evening"

    today_str = now.strftime("%A, %B %d, %Y")
    
    st.markdown(f"""
    <div class="fade-in">
        <div style="text-align:center; padding:1.5rem;">
            <h1 style="font-size:2.5rem; margin:0; color:#FFFFFF !important; text-shadow: 3px 3px 0 #8A2BE2;">
                {greeting}, {st.session_state.user['name']}!
            </h1>
        </div>
        <div class="date-display slide-in">
            <h3 style="margin:0; color:white !important; text-shadow: 2px 2px 0 #8A2BE2;">🗓️ {today_str}</h3>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📊 Your Daily Quest Progress")

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
                    <h3>🏆 Today's Progress</h3>
                    <h2>{completed_habits}/{total_habits}</h2>
                </div>
                """, unsafe_allow_html=True)
            with cols[1]:
                progress = (completed_habits/total_habits*100) if total_habits > 0 else 0
                st.markdown(f"""
                <div class="metric-card">
                    <h3>📈 Completion Rate</h3>
                    <h2>{progress:.0f}%</h2>
                </div>
                """, unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>⏳ Remaining</h3>
                    <h2>{total_habits - completed_habits}</h2>
                </div>
                """, unsafe_allow_html=True)

            st.progress(progress/100)
            
            # Show completion message
            if completed_habits == total_habits and total_habits > 0:
                st.balloons()
                st.success("🎉 Amazing! You've completed all your quests for today!")
            elif completed_habits > 0:
                st.info(f"💪 Great job! You've completed {completed_habits} quests today!")
        else:
            st.markdown("""
            <div class="cartoon-card" style="text-align:center;">
                <h3>🚀 No Quests Yet!</h3>
                <p>Add your first habit to begin your adventure! 🌈</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.error("❌ Could not load today's status")

def add_habit_page():
    apply_cartoon_styles()
    st.markdown("# ➕ Add New Quest")
    st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
    habit_name = st.text_input("🎯 Quest Name")
    habit_description = st.text_area("📝 Quest Description (Optional)")
    if st.button("✨ Add Quest!", use_container_width=True):
        if habit_name.strip():
            result = add_habit_api(habit_name, habit_description, st.session_state.user["user_id"])
            if result.get("success"):
                st.session_state.show_success = True
                st.success("🎉 New quest added to your adventure!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to add quest!")
        else:
            st.warning("⚠️ Please enter a quest name!")
    st.markdown('</div>', unsafe_allow_html=True)

def my_habits_page():
    apply_cartoon_styles()
    st.markdown("# 📝 Today's Quests")
    
    # Refresh today's habits
    today_data = today_status_api(st.session_state.user["user_id"])
    if today_data.get("success"):
        st.session_state.today_habits = today_data["habits"]
    
    habits = st.session_state.today_habits
    if not habits:
        st.info("🌟 No active quests for today. Add some adventures!")
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
            st.write(f"## 🎯 {habit['name']}")
            if habit.get("description"):
                st.write(f"_{habit['description']}_")
            if completed:
                st.markdown("### ✅ **Completed!** 🎉")
            if timer_active:
                start_time = st.session_state.active_timers[habit["habit_id"]]["start_time"]
                elapsed = datetime.now() - start_time
                st.markdown(f"### ⏱️ **Timer Running:** {format_time(elapsed.total_seconds())}")
        
        with col2:
            if not completed:
                if habit["habit_id"] in st.session_state.active_timers:
                    if st.button("⏹️ Stop", key=f"stop_{habit['habit_id']}", use_container_width=True):
                        duration = stop_timer(habit["habit_id"])
                        if duration:
                            st.success(f"⏱️ Timer stopped! Time spent: {format_time(duration.total_seconds())}")
                            time.sleep(1)
                            st.rerun()
                else:
                    if st.button("⏱️ Start Timer", key=f"start_{habit['habit_id']}", use_container_width=True, type="secondary"):
                        start_timer(habit["name"], habit["habit_id"])
                        st.success(f"⏱️ Timer started for {habit['name']}!")
                        time.sleep(1)
                        st.rerun()
        
        with col3:
            if not completed:
                if st.button("🎊 Complete", key=f"comp_{habit['habit_id']}", use_container_width=True):
                    res = complete_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                    if res.get("success"):
                        st.session_state.completed_habits.add(habit["habit_id"])
                        st.success("✅ Quest completed!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Failed to complete quest!")
            
            if st.button("🗑️ Delete", key=f"del_{habit['habit_id']}", use_container_width=True):
                remove_habit_api(habit["habit_id"], st.session_state.user["user_id"])
                st.session_state.deleted_habits.add(habit["habit_id"])
                st.success("🗑️ Quest deleted!")
                time.sleep(1)
                st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

def today_status_page():
    apply_cartoon_styles()
    st.markdown("# 📊 Today's Adventure Status")
    
    # Time tracking summary
    total_time, habit_time = get_today_time_summary()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### ⏱️ Time Tracking Summary")
        
        if total_time > 0:
            st.metric("Total Time Tracked Today", format_time(total_time))
            
            st.markdown("### 📊 Time by Activity")
            for habit_name, time_seconds in habit_time.items():
                st.write(f"**{habit_name}**: {format_time(time_seconds)}")
        else:
            st.info("⏰ No time tracked today. Start timers on your habits!")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="cartoon-card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Habit Completion Status")
        
        today_data = today_status_api(st.session_state.user["user_id"])
        if today_data.get("success"):
            total_habits = today_data["total_habits"]
            completed_habits = today_data["completed_habits"]
            
            if total_habits > 0:
                st.metric("✅ Completed", completed_habits)
                st.metric("⏳ Remaining", total_habits - completed_habits)
                st.metric("📊 Total Quests", total_habits)
                
                progress = completed_habits / total_habits
                st.progress(progress)
                
                # Motivational messages
                if progress == 1:
                    st.balloons()
                    st.success("🎉 Perfect! All quests completed! You're amazing!")
                elif progress >= 0.8:
                    st.success("🔥 Fantastic! Almost there! Keep going!")
                elif progress >= 0.5:
                    st.info("💪 Great progress! You're halfway there!")
                elif progress > 0:
                    st.info("🚀 Good start! Every quest counts!")
                else:
                    st.info("🌱 Ready to begin your adventure? You've got this!")
            else:
                st.info("📝 No quests for today. Add some adventures to get started!")
        else:
            st.error("❌ Could not load today's status")
        st.markdown('</div>', unsafe_allow_html=True)

def weekly_perf_page():
    apply_cartoon_styles()
    st.markdown("# 📈 Weekly Adventure Report")
    
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
                st.success("🌈 Legendary Adventurer! Perfect week! 🏆")
            elif stars >= 4:
                st.success("🚀 Amazing! You're a star performer! ⭐")
            elif stars >= 3:
                st.info("💪 Great job! Keep up the good work! 👍")
            elif stars >= 2:
                st.info("👍 Good progress! Every step counts! 🌟")
            else:
                st.info("🌱 Getting started! Tomorrow is a new day! 🌈")
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
    
    st.sidebar.markdown("### 🗺️ Navigation")
    pages = {
        "🏠 Home Base": home_page,
        "📝 Today's Quests": my_habits_page,
        "➕ New Quest": add_habit_page,
        "📊 Today's Progress": today_status_page,
        "📈 Weekly Report": weekly_perf_page
    }
    choice = st.sidebar.radio("Choose your path:", list(pages.keys()))
    pages[choice]()

if __name__ == "__main__":
    main()