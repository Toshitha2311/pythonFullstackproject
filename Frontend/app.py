import streamlit as st
import requests

BASE_URL = "http://127.0.0.1:8000"   # backend URL

st.set_page_config(page_title="HabitHub", layout="wide")

# ------------------------------
# SESSION STATE: Username
# ------------------------------
if "username" not in st.session_state:
    st.session_state.username = None

# ------------------------------
# LOGIN PAGE
# ------------------------------
if st.session_state.username is None:
    st.title("👋 Welcome to HabitHub")
    name = st.text_input("Enter your name to continue:")

    if st.button("Start"):
        if name.strip():
            st.session_state.username = name.strip()
            st.rerun()   # rerun the app to show navbar
    st.stop()  # prevent sidebar from showing until logged in

# ------------------------------
# HEADER + NAVIGATION
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
def get_habits():
    try:
        res = requests.get(f"{BASE_URL}/habits")
        if res.status_code == 200:
            return res.json().get("habits", [])
    except:
        return []
    return []

def mark_habit_completed(name):
    try:
        return requests.post(f"{BASE_URL}/habits/complete", json={"name": name}).json()
    except:
        return {"success": False}

def end_of_day_status():
    try:
        return requests.get(f"{BASE_URL}/habitlogs/status").json()
    except:
        return {}

def get_weekly_performance():
    try:
        return requests.get(f"{BASE_URL}/weeklyperformance").json().get("weekly_report", [])
    except:
        return []

# ------------------------------
# PAGES
# ------------------------------
if page == "🏠 Dashboard":
    st.subheader("📌 Today's Habits")
    habits = get_habits()

    if not habits:
        st.info("No habits found. Add some habits first!")
    else:
        completed_today = []
        for habit in habits:
            habit_name = habit["name"]
            checked = st.checkbox(habit_name, key=habit_name)
            if checked:
                res = mark_habit_completed(habit_name)
                if res.get("success"):
                    completed_today.append(habit_name)

        if completed_today:
            st.success(f"✅ Completed: {', '.join(completed_today)}")

    # End of day status
    status = end_of_day_status()
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
            res = requests.post(
                f"{BASE_URL}/habits", 
                json={"name": habit_name, "description": habit_desc}
            ).json()
            if res.get("success"):
                st.success(f"Habit '{habit_name}' added successfully!")
                st.rerun()
            else:
                st.error(res.get("message") or "Error adding habit")

elif page == "📊 Weekly Performance":
    st.subheader("📊 Weekly Performance")
    weekly_report = get_weekly_performance()

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
            color = "#4CAF50"   # green
        elif completion_pct >= 60:
            color = "#FFEB3B"   # yellow
        elif completion_pct >= 40:
            color = "#FF9800"   # orange
        elif completion_pct >= 20:
            color = "#F44336"   # red
        else:
            color = "#9C27B0"   # violet

        st.markdown(
            f"<div style='width:100%;height:25px;background:{color};border-radius:5px'></div>",
            unsafe_allow_html=True
        )
    else:
        st.info("Weekly performance will be generated automatically on Sunday night.")

elif page == "⚙️ Settings":
    st.subheader("⚙️ Settings")
    if st.button("Logout"):
        st.session_state.username = None
        st.rerun()
