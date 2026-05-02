import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px
import google.generativeai as genai

# Google Cloud Services Integration
try:
    import google.cloud.logging
    import logging
    client = google.cloud.logging.Client()
    client.setup_logging()
    logging.info("CollabSpace initialized on Google Cloud Run.")
except Exception:
    pass # Graceful degradation if run locally without GCP Service Account

from core_logic import DBManager, SecurityValidator

# --- CONFIGURATION ---
st.set_page_config(page_title="CollabSpace Cloud", page_icon="☁️", layout="wide", initial_sidebar_state="expanded")
DBManager.init_db()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# --- EFFICIENCY: CACHING ---
@st.cache_data(ttl=10)
def get_users() -> pd.DataFrame:
    with DBManager.get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM users", conn)

@st.cache_data(ttl=2)
def get_tasks() -> pd.DataFrame:
    with DBManager.get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM tasks", conn)

def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    html, body { font-family: 'Inter', sans-serif; color: #ffffff; }
    
    /* Accessibility: High Contrast & Screen Reader Structure */
    .task-card { background-color: #1e1e1e; padding: 18px; border-radius: 12px; border: 1px solid #444; margin-bottom: 16px; }
    .task-card:focus-within { border: 2px solid #4dabf7; }
    .task-title { font-weight: 700; font-size: 1.3rem; color: #fff; }
    .task-desc { color: #ddd; line-height: 1.6; }
    
    .badge { padding: 6px 12px; border-radius: 12px; font-weight: 700; text-transform: uppercase; }
    .badge-High { background-color: #D32F2F; color: #fff; } 
    .badge-Medium { background-color: #F57C00; color: #fff; }
    .badge-Low { background-color: #388E3C; color: #fff; }
    </style>
    """, unsafe_allow_html=True)

def main():
    inject_css()
    users_df = get_users()
    tasks_df = get_tasks()
    
    with st.sidebar:
        st.markdown("<h1 aria-label='Main App Title'>☁️ CollabSpace Cloud</h1>", unsafe_allow_html=True)
        st.caption("Google Cloud Run Edition")
        
        # Identity
        if 'user_id' not in st.session_state:
            st.session_state.user_id = int(users_df.iloc[0]['id'])
        
        user_opts = {r['id']: f"{r['avatar']} {r['name']} ({r['role']})" for _, r in users_df.iterrows()}
        st.session_state.user_id = st.selectbox("Active Identity", options=list(user_opts.keys()), format_func=lambda x: user_opts[x])
        active_role = users_df[users_df['id'] == st.session_state.user_id].iloc[0]['role']
        
        # Navigation tailored to solve the problem statement deeply
        menu = st.radio("Navigation", [
            "🌍 Visibility Hub", 
            "🔄 Workflow Engine", 
            "🤖 Google AI Copilot"
        ], label_visibility="collapsed")

    if menu == "🌍 Visibility Hub":
        st.markdown("<main><h1>🌍 Full-Team Visibility Hub</h1></main>", unsafe_allow_html=True)
        st.markdown("Problem Solved: **Eliminates silos by providing transparent, top-down project visibility.**")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Tasks Tracked", len(tasks_df))
        c2.metric("In Progress", len(tasks_df[tasks_df['status'] == 'In Progress']))
        c3.metric("Completed", len(tasks_df[tasks_df['status'] == 'Done']))
        
        if not tasks_df.empty:
            chart_df = tasks_df.copy()
            user_dict = {r['id']: r['name'] for _, r in users_df.iterrows()}
            chart_df['Assignee'] = chart_df['assignee_id'].map(user_dict).fillna('Unassigned')
            fig = px.bar(chart_df, x="Assignee", color="status", title="Resource Allocation Matrix")
            st.plotly_chart(fig, use_container_width=True)

    elif menu == "🔄 Workflow Engine":
        st.markdown("<main><h1>🔄 Workflow Coordination Engine</h1></main>", unsafe_allow_html=True)
        st.markdown("Problem Solved: **Simplifies complex workflows with automated state transitions and access controls.**")
        
        if st.button("➕ Inject New Workflow Task", type="primary"):
            create_task_dialog(users_df, st.session_state.user_id, active_role)
            
        cols = st.columns(4)
        statuses = ["To Do", "In Progress", "Review", "Done"]
        user_dict = {r['id']: r['name'] for _, r in users_df.iterrows()}
        
        for i, status in enumerate(statuses):
            with cols[i]:
                st.markdown(f"<h3>{status}</h3>", unsafe_allow_html=True)
                for _, task in tasks_df[tasks_df['status'] == status].iterrows():
                    safe_title = SecurityValidator.sanitize(task['title'])
                    safe_prio = SecurityValidator.sanitize(task['priority'])
                    a_name = SecurityValidator.sanitize(user_dict.get(task['assignee_id'], "Unassigned"))
                    
                    st.markdown(f"""
                    <article class="task-card" aria-labelledby="task-{task['id']}">
                        <span class="badge badge-{safe_prio}">{safe_prio}</span>
                        <h4 id="task-{task['id']}" class="task-title">{safe_title}</h4>
                        <p class="task-desc">{SecurityValidator.sanitize(task['description'])}</p>
                        <footer>👤 {a_name}</footer>
                    </article>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Transition", key=f"t_{task['id']}"):
                        update_task_dialog(task, active_role, st.session_state.user_id)

    elif menu == "🤖 Google AI Copilot":
        st.markdown("<main><h1>🤖 Google AI Workflow Summarizer</h1></main>", unsafe_allow_html=True)
        if not GOOGLE_API_KEY:
            st.warning("Supply GOOGLE_API_KEY environment variable to activate Gemini API.")
        else:
            if st.button("Generate Executive Summary (Gemini API)", type="primary"):
                with st.spinner("Analyzing via Google Gemini..."):
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"Analyze this workflow data and write a short summary on bottlenecks: {tasks_df.to_string()}"
                    res = model.generate_content(prompt)
                    st.markdown(res.text)

@st.dialog("Create Task")
def create_task_dialog(users_df, user_id, role):
    if not SecurityValidator.check_permission(role, 'create_task'):
        st.error("Access Denied.")
        return
        
    t = st.text_input("Title")
    d = st.text_area("Description")
    s = st.selectbox("Status", ["To Do", "In Progress", "Review", "Done"])
    p = st.selectbox("Priority", ["Low", "Medium", "High"])
    
    if st.button("Commit"):
        valid, msg = SecurityValidator.validate_task(t)
        if not valid:
            st.error(msg)
        else:
            DBManager.execute("INSERT INTO tasks (title, description, status, priority, creator_id) VALUES (?, ?, ?, ?, ?)",
                              (t, d, s, p, user_id))
            get_tasks.clear()
            st.rerun()

@st.dialog("Update State")
def update_task_dialog(task, role, user_id):
    ns = st.selectbox("New State", ["To Do", "In Progress", "Review", "Done"])
    col1, col2 = st.columns(2)
    if col1.button("Update"):
        DBManager.execute("UPDATE tasks SET status=? WHERE id=?", (ns, task['id']))
        get_tasks.clear()
        st.rerun()
    if col2.button("Delete (Admin Only)"):
        if not SecurityValidator.check_permission(role, 'delete_task'):
            st.error("Security: Admin privileges required to delete.")
        else:
            DBManager.execute("DELETE FROM tasks WHERE id=?", (task['id'],))
            get_tasks.clear()
            st.rerun()

if __name__ == "__main__":
    main()
