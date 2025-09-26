# Frontend/app.py
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="HabitHub", layout="wide")

# ------------------------------
# SESSION STATE: Username
# ------------------------------
if "username" not in st.session_state:
    st.session_state.username = ""

if not st.session_state.username:
    st.title("👋 Welcome to HabitHub")
    name = st.text_input("Enter your name to continue:")
    if st.button("Start"):
        if name.strip():
            st.session_state.username = name.strip()
            st.experimental_rerun()
else:
    # ------------------------------
    # SIDEBAR NAVIGATION
    # ------------------------------
    st.sidebar.title("📌 Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["🏠 Dashboard", "➕ Add Habit", "📊 Weekly Performance", "⚙️ Settings"]
    )
    st.sidebar.markdown("---")
    st.sidebar.success(f"Logged in as **{st.session_state.username}**")

    st.title(f"🎯 Welcome, {st.session_state.username}!")
    st.markdown("Manage your habits, track progress, and see weekly performance.")

    # ------------------------------
    # API HELPERS
    # ------------------------------
    def safe_get(url):
        try:
            r = requests.get(url, timeout=5)
            return r.json() if r.status_code == 200 else {}
        except:
            return {}

    def safe_post(url, json_data):
        try:
            r = requests.post(url, json=json_data, timeout=5)
            return r.json() if r.status_code == 200 else {}
        except:
            return {}

    # ------------------------------
    # PAGES
    # ------------------------------
    if page == "🏠 Dashboard":
        st.subheader("📌 Today's Habits")
        habits_resp = safe_get(f"{API_URL}/habits")
        habits = habits_resp.get("habits", []) if habits_resp else []

        if not habits:
            st.info("No habits found. Add some habits first!")
        else:
            completed_today = []
            for habit in habits:
                habit_name = habit.get("name", "")
                checked = st.checkbox(habit_name, key=habit_name)
                if checked:
                    res = safe_post(f"{API_URL}/habits/complete", {"name": habit_name})
                    if res.get("success"):
                        completed_today.append(habit_name)
            if completed_today:
                st.success(f"✅ Completed: {', '.join(completed_today)}")

        # End-of-day status
        status = safe_get(f"{API_URL}/habitlogs/status")
        if status.get("success"):
            st.subheader("💬 End-of-Day Status")
            st.info(status.get("message"))

    elif page == "➕ Add Habit":
        st.subheader("➕ Add New Habit")
        with st.form("add_habit_form"):
            habit_name = st.text_input("Habit Name")
            habit_desc = st.text_area("Description (optional)")
            submitted = st.form_submit_button("Add Habit")
            if submitted and habit_name.strip():
                res = safe_post(f"{API_URL}/habits", {"name": habit_name, "description": habit_desc})
                if res.get("success"):
                    st.success(f"Habit '{habit_name}' added successfully!")
                    st.experimental_rerun()
                else:
                    st.error(res.get("message") or "Error adding habit")

    elif page == "📊 Weekly Performance":
        st.subheader("📊 Weekly Performance")
        weekly_resp = safe_get(f"{API_URL}/weeklyperformance")
        weekly_report = weekly_resp.get("weekly_report", []) if weekly_resp else []

        if weekly_report:
            last_week = weekly_report[-1]
            completion_pct = last_week.get("completion_pct", 0)
            week_start = last_week.get("week_start")

            st.markdown(f"### 📅 Week starting {week_start}")
            st.metric(
                label=f"{st.session_state.username}'s Completion Rate",
                value=f"{completion_pct:.2f}%"
            )

            # VIBGYOR color coding
            if completion_pct >= 80:
                color = "#4CAF50"  # Green
            elif completion_pct >= 60:
                color = "#FFEB3B"  # Yellow
            elif completion_pct >= 40:
                color = "#FF9800"  # Orange
            elif completion_pct >= 20:
                color = "#F44336"  # Red
            else:
                color = "#9C27B0"  # Violet

            st.markdown(
                f"<div style='width:100%;height:25px;background:{color};border-radius:5px'></div>",
                unsafe_allow_html=True
            )
        else:
            st.info("Weekly performance will be generated automatically on Sunday night.")

    elif page == "⚙️ Settings":
        st.subheader("⚙️ Settings")
        if st.button("Logout"):
            st.session_state.username = ""
            st.experimental_rerun()
