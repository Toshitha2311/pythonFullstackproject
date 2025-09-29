import streamlit as st
import requests
import time

API_URL = "http://127.0.0.1:8000"

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------
def safe_post(endpoint, data=None, use_auth=True):
    """POST request with optional JWT auth."""
    try:
        headers = {}
        if use_auth and "access_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        res = requests.post(f"{API_URL}{endpoint}", json=data or {}, headers=headers)
        return res.json() if res.status_code == 200 else {"success": False, "message": f"Server error: {res.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def safe_get(endpoint, use_auth=True):
    """GET request with optional JWT auth."""
    try:
        headers = {}
        if use_auth and "access_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"
        res = requests.get(f"{API_URL}{endpoint}", headers=headers)
        return res.json() if res.status_code == 200 else {"success": False, "message": f"Server error: {res.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# -------------------------------
# SESSION STATE
# -------------------------------
if "show_dashboard" not in st.session_state:
    st.session_state.show_dashboard = False
if "habits_updated" not in st.session_state:
    st.session_state.habits_updated = False
if "habits_list" not in st.session_state:
    st.session_state.habits_list = []
if "completed_set" not in st.session_state:
    st.session_state.completed_set = set()
if "access_token" not in st.session_state:
    st.session_state.access_token = None

# -------------------------------
# PAGE SETUP
# -------------------------------
st.set_page_config(page_title="HabitHub", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
[data-testid="stSidebar"] {background-color: #f0f8ff;}
.stButton>button:hover {background-color: #66a6ff; color: white; transform: scale(1.05); transition: 0.3s;}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# LOGIN / REGISTER SCREEN
# -------------------------------
if not st.session_state.access_token:
    st.title("🔐 Login to HabitHub")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            res = safe_post("/auth/login", {"email": email, "password": password}, use_auth=False)
            if res.get("success"):
                st.session_state.access_token = res["access_token"]
                st.session_state.show_dashboard = True
                st.success("Login successful! ✅")
                st.experimental_rerun()
            else:
                st.warning(res.get("message"))

    with tab2:
        email = st.text_input("Register Email")
        password = st.text_input("Register Password", type="password")
        if st.button("Register"):
            res = safe_post("/auth/register", {"email": email, "password": password}, use_auth=False)
            if res.get("success"):
                st.success("Registered successfully! Please login now.")
            else:
                st.warning(res.get("message"))
    st.stop()

# -------------------------------
# WELCOME SCREEN
# -------------------------------
if not st.session_state.show_dashboard:
    st.title("🎯 Welcome to HabitHub! 🌈")
    st.image("https://media.giphy.com/media/l0HlvtIPzPdt2usKs/giphy.gif", width=300)
    if st.button("Start Your Journey!"):
        st.session_state.show_dashboard = True
        st.session_state.habits_updated = True
    st.stop()

# -------------------------------
# DASHBOARD
# -------------------------------
st.sidebar.title("HabitHub Dashboard")
page = st.sidebar.radio("Navigation", ["Habits Dashboard", "Weekly Performance", "Today's Status"])

# -------------------------------
# HABITS DASHBOARD
# -------------------------------
if page == "Habits Dashboard":
    st.title("🎯 Habits Dashboard")
    st.subheader("➕ Add New Habit")
    new_name = st.text_input("Habit Name")
    new_desc = st.text_input("Description (optional)")
    if st.button("Add Habit") and new_name.strip():
        res = safe_post("/habit/add", {"name": new_name.strip(), "description": new_desc.strip()})
        if res.get("success"):
            st.success(res.get("message"))
            st.session_state.habits_updated = True
            st.balloons()
        else:
            st.warning(res.get("message"))

    if st.session_state.habits_updated:
        res = safe_get("/habit/list")
        st.session_state.habits_list = res.get("habits", [])
        st.session_state.habits_updated = False

    habits_list = st.session_state.habits_list
    if not habits_list:
        st.info("You have no habits yet. Add one above! 🎉")

    cols = st.columns(2)
    for i, habit in enumerate(habits_list):
        col = cols[i % 2]
        with col:
            habit_name = habit["name"]
            habit_id = habit["habit_id"]
            key = f"{habit_name}_{i}"

            completed = st.checkbox(habit_name, key=key)
            if completed and habit_id not in st.session_state.completed_set:
                safe_post("/habit/complete", {"habit_id": habit_id})
                st.session_state.completed_set.add(habit_id)
                st.image("https://media.giphy.com/media/26tPoyDhjiJ2g7rEs/giphy.gif", width=200)

            st.markdown(
                f"<div style='background-color:#f4f4f4; padding:15px; border-radius:12px; margin-bottom:12px;'>"
                f"<p>{habit.get('description','')}</p></div>",
                unsafe_allow_html=True
            )

# -------------------------------
# WEEKLY PERFORMANCE
# -------------------------------
elif page == "Weekly Performance":
    st.title("🏆 Weekly Performance")
    weekly_report = safe_get("/weekly/report").get("weekly_report", [])

    if weekly_report:
        for week in weekly_report:
            week_start = week["week_start"]
            pct = week["completion_pct"]
            stars = week.get("stars", int(pct // 25))
            badge = "🌟 Completed!" if pct >= 100 else ""
            st.markdown(
                f"<div style='background-color:#cce5ff; padding:15px; border-radius:12px; margin-bottom:12px;'>"
                f"<h3>Week starting {week_start} {badge}</h3>"
                f"<p>Completion: {pct:.2f}%</p>"
                f"<p>Stars: {'⭐'*stars + '☆'*(4-stars)}</p></div>",
                unsafe_allow_html=True
            )

    if st.button("Update Weekly Performance"):
        res = safe_post("/weekly/calculate")
        if res.get("success"):
            st.success(res.get("message"))
        else:
            st.warning(res.get("message"))

# -------------------------------
# TODAY'S STATUS
# -------------------------------
elif page == "Today's Status":
    st.title("📅 Today's Habit Status")
    status = safe_get("/habit/status")
    if status.get("success"):
        for item in status["status"]["status"]:
            st.write(f"✅ {item['habit_name']}" if item["completed"] else f"❌ {item['habit_name']}")
    else:
        st.warning(status.get("message"))

# -------------------------------
# LOGOUT
# -------------------------------
if st.sidebar.button("Logout"):
    st.session_state.access_token = None
    st.session_state.show_dashboard = False
    st.session_state.habits_updated = True
    st.session_state.completed_set = set()
    st.experimental_rerun()
