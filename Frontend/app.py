# Frontend/app.py
import streamlit as st
import requests
import json

API_URL = "http://127.0.0.1:8000"
st.set_page_config(page_title="HabitHub", layout="wide", page_icon="🎯")

if "page" not in st.session_state: st.session_state.page = "home"

# -------------------------------
# Navigation
# -------------------------------
pages = ["Home", "Add Habit", "My Habits", "Today's Status", "Weekly Performance"]
cols = st.columns(len(pages))
for i, p in enumerate(pages):
    if cols[i].button(p):
        st.session_state.page = p.lower().replace(" ", "_")
st.markdown("---")

# -------------------------------
# API Helpers
# -------------------------------
def safe_json(resp):
    try:
        return resp.json()
    except:
        return {}

def add_habit_api(name, desc):
    return safe_json(requests.post(f"{API_URL}/habit/add", json={"name": name, "description": desc}))

def list_habits_api():
    return safe_json(requests.get(f"{API_URL}/habit/list"))

def complete_habit_api(hid):
    return safe_json(requests.post(f"{API_URL}/habit/complete", json={"habit_id": hid}))

def remove_habit_api(hid):
    return safe_json(requests.post(f"{API_URL}/habit/remove", json={"habit_id": hid}))

def today_status_api():
    return safe_json(requests.get(f"{API_URL}/habit/status"))

def weekly_perf_api():
    return safe_json(requests.get(f"{API_URL}/weekly/report"))

# -------------------------------
# Pages
# -------------------------------
def home_page():
    st.header("🎯 Welcome to HabitHub")

def add_habit_page():
    st.header("➕ Add Habit")
    with st.form("habit_form"):
        name = st.text_input("Habit Name")
        desc = st.text_area("Description")
        if st.form_submit_button("Add"):
            if not name.strip():
                st.warning("Name cannot be empty")
                return
            res = add_habit_api(name.strip(), desc)
            if res.get("success"):
                st.success(f"Added '{name}'")
            else:
                st.error(res.get("error", "Failed"))

def my_habits_page():
    st.header("📋 My Habits")
    res = list_habits_api().get("habits", [])
    if not res:
        st.info("No habits yet!")
        return
    for h in res:
        col1, col2, col3 = st.columns([4,1,1])
        col1.write(f"**{h['name']}** — {h.get('description','')}")
        if col2.button("✅ Complete", key=f"c_{h['habit_id']}"):
            complete_habit_api(h["habit_id"])
        if col3.button("🗑️ Delete", key=f"d_{h['habit_id']}"):
            remove_habit_api(h["habit_id"])

def today_status_page():
    st.header("📅 Today's Status")
    status = today_status_api().get("status", {}).get("status", [])
    for s in status:
        st.write(f"{'✅' if s['completed'] else '❌'} {s['habit_name']}")

def weekly_perf_page():
    st.header("📊 Weekly Performance")
    perf = weekly_perf_api()
    st.progress(int(perf.get("completion_pct",0)))
    st.markdown(f"Stars: {'⭐'*perf.get('stars',0)}")

# -------------------------------
# Page Router
# -------------------------------
pages_dict = {
    "home": home_page,
    "add_habit": add_habit_page,
    "my_habits": my_habits_page,
    "today_status": today_status_page,
    "weekly_performance": weekly_perf_page
}
pages_dict.get(st.session_state.page, home_page)()
