# Frontend/app.py
import streamlit as st
import requests
import json
from datetime import date
import pandas as pd

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="HabitHub", layout="wide", page_icon="🎯")

# -------------------------------
# SESSION STATE INIT
# -------------------------------
if "page" not in st.session_state:
    st.session_state.page = "home"
if "completed_habits" not in st.session_state:
    st.session_state.completed_habits = set()
if "deleted_habits" not in st.session_state:
    st.session_state.deleted_habits = set()

# -------------------------------
# API HELPERS
# -------------------------------
def safe_json(resp):
    try:
        return resp.json()
    except json.decoder.JSONDecodeError:
        st.error(f"Invalid response from server: {resp.text}")
        return {}

def add_habit_api(name, desc):
    resp = requests.post(f"{API_URL}/habit/add", json={"name": name, "description": desc})
    return safe_json(resp)

def list_habits_api():
    resp = requests.get(f"{API_URL}/habit/list")
    return safe_json(resp).get("habits", [])

def complete_habit_api(hid):
    resp = requests.post(f"{API_URL}/habit/complete", json={"habit_id": hid})
    return safe_json(resp)

def remove_habit_api(hid):
    resp = requests.post(f"{API_URL}/habit/remove", json={"habit_id": hid})
    return safe_json(resp)

def today_status_api():
    resp = requests.get(f"{API_URL}/habit/status")
    return safe_json(resp)

def weekly_perf_api():
    resp = requests.get(f"{API_URL}/weekly/report")
    return safe_json(resp)

# -------------------------------
# PAGES
# -------------------------------
def home_page():
    st.markdown("## 🎯 Welcome to HabitHub")
    st.markdown("Track your habits daily, see weekly progress, and earn stars! ✨")

def add_habit_page():
    st.markdown("## ➕ Add New Habit")
    with st.form("habit_form"):
        name = st.text_input("Habit Name")
        desc = st.text_area("Description")
        if st.form_submit_button("Add Habit"):
            if not name.strip():
                st.warning("Name cannot be empty")
                return
            res = add_habit_api(name.strip(), desc)
            if res.get("success"):
                st.success(f"Added habit: {name} 🎉")
            else:
                st.error(res.get("error", "Failed to add habit"))

def my_habits_page():
    st.markdown("## 📋 My Habits")
    habits = list_habits_api()
    if not habits:
        st.info("No habits yet! Add some from 'Add Habit' page.")
        return

    for h in habits:
        habit_id = h["habit_id"]
        if habit_id in st.session_state.deleted_habits:
            continue

        col1, col2, col3 = st.columns([4,1,1])
        completed = habit_id in st.session_state.completed_habits
        col1.markdown(f"**{h['name']}** — {h.get('description','')}")
        if col2.button("✅ Complete" if not completed else "✅ Completed", key=f"c_{habit_id}"):
            complete_habit_api(habit_id)
            st.session_state.completed_habits.add(habit_id)
        if col3.button("🗑️ Delete", key=f"d_{habit_id}"):
            remove_habit_api(habit_id)
            st.session_state.deleted_habits.add(habit_id)

def today_status_page():
    st.markdown("## 📅 Today's Status")
    status_resp = today_status_api().get("status", [])
    if isinstance(status_resp, dict) and "status" in status_resp:
        status_list = status_resp["status"]
    elif isinstance(status_resp, list):
        status_list = status_resp
    else:
        status_list = []

    completed = sum(1 for s in status_list if s["completed"])
    total = len(status_list)

    if total > 0:
        df = pd.DataFrame([{"Status": "Completed", "Count": completed},
                           {"Status": "Pending", "Count": total-completed}])
        st.write(f"Today: {completed}/{total} habits completed ✅")
        st.bar_chart(df.set_index("Status"))
    else:
        st.info("No habits found for today.")

def weekly_perf_page():
    st.markdown("## 📊 Weekly Performance")
    perf = weekly_perf_api()
    pct = perf.get("completion_pct", 0)
    stars = perf.get("stars", 0)
    st.progress(int(pct))
    st.markdown(f"Completion: {pct:.2f}%")
    st.markdown(f"Stars: {'⭐'*stars}")

# -------------------------------
# PAGE NAVIGATION
# -------------------------------
pages_dict = {
    "home": home_page,
    "add_habit": add_habit_page,
    "my_habits": my_habits_page,
    "today_status": today_status_page,
    "weekly_performance": weekly_perf_page
}

cols = st.columns([1]*len(pages_dict))
for i, p in enumerate(pages_dict.keys()):
    if cols[i].button(p.replace("_"," ").title()):
        st.session_state.page = p

st.markdown("---")
pages_dict.get(st.session_state.page, home_page)()
