import streamlit as st
import pandas as pd
import datetime
import os
import plotly.express as px
import google.generativeai as genai

# Google Cloud Services Integrationm
try:
    import google.cloud.logging
    import logging
    client = google.cloud.logging.Client()
    client.setup_logging()
    logging.info("CollabSpace initialized on Google Cloud Run.")
except Exception:
    pass

from core_logic import DBManager, SecurityValidator

# --- CONFIGURATION ---
st.set_page_config(page_title="CollabSpace Pro", page_icon="🌌", layout="wide", initial_sidebar_state="expanded")
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

@st.cache_data(ttl=2)
def get_docs() -> pd.DataFrame:
    with DBManager.get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM docs", conn)

@st.cache_data(ttl=2)
def get_chat() -> pd.DataFrame:
    with DBManager.get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM chat", conn)

@st.cache_data(ttl=5)
def get_activity() -> pd.DataFrame:
    with DBManager.get_conn() as conn:
        return pd.read_sql_query("SELECT * FROM activity ORDER BY timestamp DESC LIMIT 20", conn)

def inject_premium_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
        background-color: #0b0f19 !important;
    }
    
    /* Premium Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border-right: 1px solid #1e293b;
    }
    
    /* Metrics */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 16px; padding: 20px; border: 1px solid #334155;
        box-shadow: inset 0 1px 1px rgba(255, 255, 255, 0.05);
    }
    div[data-testid="stMetricValue"] { font-size: 2.5rem; font-weight: 700; color: #818cf8; }
    
    /* Glassmorphism Cards */
    .premium-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 20px;
    }
    .premium-card:hover { transform: translateY(-2px); border-color: rgba(99, 102, 241, 0.4); }
    .premium-card h3 { margin-top: 0; color: #f8fafc; }
    
    /* Kanban */
    .kanban-header { font-weight: 600; font-size: 1.1rem; padding: 12px; margin-bottom: 16px; border-radius: 8px; text-align: center; text-transform: uppercase; letter-spacing: 1px; }
    .todo-h { border-bottom: 3px solid #64748b; color: #cbd5e1; background: rgba(255,255,255,0.02); }
    .prog-h { border-bottom: 3px solid #3b82f6; color: #93c5fd; background: rgba(255,255,255,0.02); }
    .rev-h  { border-bottom: 3px solid #f59e0b; color: #fcd34d; background: rgba(255,255,255,0.02); }
    .done-h { border-bottom: 3px solid #10b981; color: #6ee7b7; background: rgba(255,255,255,0.02); }
    
    .kanban-task { background: #1e293b; padding: 16px; border-radius: 12px; border: 1px solid #334155; margin-bottom: 16px; }
    .kanban-task h4 { margin: 0 0 8px 0; color: #f8fafc; font-size: 1.1rem; }
    .kanban-task p { margin: 0 0 12px 0; color: #94a3b8; font-size: 0.9rem; line-height: 1.5; }
    
    .badge { padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
    .badge-High { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-Medium { background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-Low { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }
    </style>
    """, unsafe_allow_html=True)

def main():
    inject_premium_css()
    users_df = get_users()
    tasks_df = get_tasks()
    
    with st.sidebar:
        st.markdown("<h1 style='text-align: center; font-size: 2rem; background: -webkit-linear-gradient(#818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>CollabSpace Pro</h1>", unsafe_allow_html=True)
        st.markdown("---")
        
        # Identity
        if 'user_id' not in st.session_state:
            st.session_state.user_id = int(users_df.iloc[0]['id'])
        
        user_opts = {r['id']: f"{r['avatar']} {r['name']} ({r['role']})" for _, r in users_df.iterrows()}
        st.session_state.user_id = st.selectbox("Identity Profile", options=list(user_opts.keys()), format_func=lambda x: user_opts[x])
        active_role = users_df[users_df['id'] == st.session_state.user_id].iloc[0]['role']
        active_name = users_df[users_df['id'] == st.session_state.user_id].iloc[0]['name']
        
        st.markdown("---")
        menu = st.radio("Navigation", [
            "📊 Executive Dashboard", 
            "📋 Workflow Engine", 
            "📅 Project Timeline",
            "📚 Knowledge Wiki",
            "💬 Team Chat",
            "🤖 Google AI Copilot",
            "⚙️ Admin Settings"
        ], label_visibility="collapsed")

    if menu == "📊 Executive Dashboard":
        st.markdown(f"<h1>Welcome back, {active_name} 👋</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8; font-size: 1.1rem;'>Here is your high-level overview of workspace operations.</p>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Tasks", len(tasks_df))
        c2.metric("In Progress", len(tasks_df[tasks_df['status'] == 'In Progress']))
        c3.metric("Resolved", len(tasks_df[tasks_df['status'] == 'Done']))
        c4.metric("Active Members", len(users_df))
        
        st.markdown("<br>", unsafe_allow_html=True)
        colA, colB = st.columns([2, 1])
        
        with colA:
            st.markdown("<div class='premium-card'><h3>Resource Allocation Matrix</h3></div>", unsafe_allow_html=True)
            if not tasks_df.empty:
                chart_df = tasks_df.copy()
                user_dict = {r['id']: r['name'] for _, r in users_df.iterrows()}
                chart_df['Assignee'] = chart_df['assignee_id'].map(user_dict).fillna('Unassigned')
                fig = px.bar(chart_df, x="Assignee", color="status", template="plotly_dark", 
                             color_discrete_map={"To Do": "#64748b", "In Progress": "#3b82f6", "Review": "#f59e0b", "Done": "#10b981"})
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", margin=dict(t=0, l=0, r=0, b=0))
                st.plotly_chart(fig, use_container_width=True)

        with colB:
            st.markdown("<div class='premium-card'><h3>Audit Log</h3></div>", unsafe_allow_html=True)
            act_df = get_activity()
            with st.container(height=380, border=False):
                for _, row in act_df.iterrows():
                    u_name = users_df[users_df['id'] == row['user_id']].iloc[0]['name'] if not users_df[users_df['id'] == row['user_id']].empty else 'System'
                    dt = datetime.datetime.fromisoformat(row['timestamp']).strftime("%H:%M")
                    st.markdown(f"<div style='border-left: 2px solid #818cf8; padding-left: 10px; margin-bottom: 12px;'><b style='color:#e2e8f0;'>{u_name}</b> <span style='color:#94a3b8;'>{row['action']}</span><br><span style='font-size:0.8rem;color:#64748b;'>{dt}</span></div>", unsafe_allow_html=True)

    elif menu == "📋 Workflow Engine":
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("<h1>📋 Advanced Kanban</h1>", unsafe_allow_html=True)
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Inject New Workflow Task", type="primary", use_container_width=True):
                create_task_dialog(users_df, st.session_state.user_id, active_role)
            
        cols = st.columns(4)
        statuses = [("To Do", "todo-h"), ("In Progress", "prog-h"), ("Review", "rev-h"), ("Done", "done-h")]
        user_dict = {r['id']: r['name'] for _, r in users_df.iterrows()}
        
        for i, (status, css_class) in enumerate(statuses):
            with cols[i]:
                st.markdown(f"<div class='kanban-header {css_class}'>{status}</div>", unsafe_allow_html=True)
                for _, task in tasks_df[tasks_df['status'] == status].iterrows():
                    safe_title = SecurityValidator.sanitize(task['title'])
                    safe_prio = SecurityValidator.sanitize(task['priority'])
                    a_name = SecurityValidator.sanitize(user_dict.get(task['assignee_id'], "Unassigned"))
                    
                    st.markdown(f"""
                    <div class="kanban-task">
                        <div style="margin-bottom: 10px;"><span class="badge badge-{safe_prio}">{safe_prio}</span></div>
                        <h4>{safe_title}</h4>
                        <p>{SecurityValidator.sanitize(task['description'])}</p>
                        <div style="display:flex; justify-content:space-between; color:#64748b; font-size:0.85rem; border-top:1px solid #334155; padding-top:10px;">
                            <span>👤 {a_name}</span>
                            <span>📅 {SecurityValidator.sanitize(task['due_date'])}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Manage Task", key=f"t_{task['id']}", use_container_width=True):
                        update_task_dialog(task, active_role, st.session_state.user_id)

    elif menu == "📅 Project Timeline":
        st.markdown("<h1>📅 Gantt Roadmap</h1>", unsafe_allow_html=True)
        if not tasks_df.empty:
            timeline_df = tasks_df.dropna(subset=['created_at', 'due_date']).copy()
            if not timeline_df.empty:
                user_dict = {r['id']: r['name'] for _, r in users_df.iterrows()}
                timeline_df['Assignee'] = timeline_df['assignee_id'].map(user_dict).fillna('Unassigned')
                
                fig = px.timeline(timeline_df, x_start="created_at", x_end="due_date", y="Assignee", color="status",
                                  hover_name="title", text="title", template="plotly_dark",
                                  color_discrete_map={"To Do": "#64748b", "In Progress": "#3b82f6", "Review": "#f59e0b", "Done": "#10b981"})
                fig.update_yaxes(autorange="reversed")
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=500)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No tasks with valid dates found for timeline.")
        else:
            st.info("No tasks available.")

    elif menu == "📚 Knowledge Wiki":
        st.markdown("<h1>📚 Secure Knowledge Base</h1>", unsafe_allow_html=True)
        docs_df = get_docs()
        
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("➕ New Document", type="primary", use_container_width=True):
                create_doc_dialog(st.session_state.user_id)
            
            st.markdown("### Directory")
            selected_doc_id = None
            for _, doc in docs_df.iterrows():
                if st.button(f"📄 {doc['title']}", key=f"d_{doc['id']}", use_container_width=True):
                    st.session_state.active_doc = doc['id']
            active_id = st.session_state.get('active_doc', docs_df.iloc[0]['id'] if not docs_df.empty else None)
            
        with c2:
            if active_id and not docs_df[docs_df['id'] == active_id].empty:
                doc = docs_df[docs_df['id'] == active_id].iloc[0]
                st.markdown(f"<div class='premium-card'><h2>{doc['title']}</h2><span class='badge badge-High'>{doc['category']}</span><hr>", unsafe_allow_html=True)
                
                t1, t2 = st.tabs(["Read Mode", "Edit Mode"])
                with t1:
                    st.markdown(doc['content'])
                with t2:
                    new_content = st.text_area("Markdown Data", value=doc['content'], height=400, label_visibility="collapsed")
                    if st.button("Commit Changes", type="primary"):
                        DBManager.execute("UPDATE docs SET content=?, updated_at=? WHERE id=?", (new_content, datetime.datetime.now().isoformat(), active_id))
                        DBManager.log_activity(st.session_state.user_id, f"Updated doc: {doc['title']}")
                        get_docs.clear()
                        get_activity.clear()
                        st.rerun()

    elif menu == "💬 Team Chat":
        st.markdown("<h1>💬 Global Sync Channel</h1>", unsafe_allow_html=True)
        chat_df = get_chat()
        
        with st.container(height=500, border=False):
            if chat_df.empty:
                st.info("No messages. Start the sync!")
            else:
                for _, msg in chat_df.iterrows():
                    user_data = users_df[users_df['id'] == msg['user_id']]
                    if not user_data.empty:
                        u_name, avatar = user_data.iloc[0]['name'], user_data.iloc[0]['avatar']
                    else:
                        u_name, avatar = "Unknown", "👤"
                        
                    with st.chat_message(name=u_name, avatar=avatar):
                        st.write(msg['message'])
                        st.caption(datetime.datetime.fromisoformat(msg['timestamp']).strftime("%H:%M"))
                        
        if prompt := st.chat_input("Broadcast message to team..."):
            DBManager.execute("INSERT INTO chat (user_id, message, timestamp) VALUES (?, ?, ?)", 
                              (st.session_state.user_id, prompt, datetime.datetime.now().isoformat()))
            get_chat.clear()
            st.rerun()

    elif menu == "🤖 Google AI Copilot":
        st.markdown("<h1>🤖 Google AI Workflow Summarizer</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#94a3b8'>Harness Google Gemini to perform deep analysis on workspace data.</p>", unsafe_allow_html=True)
        if not GOOGLE_API_KEY:
            st.warning("Supply GOOGLE_API_KEY environment variable to activate Gemini API integration.")
        else:
            if st.button("Generate Executive Summary", type="primary"):
                with st.spinner("Analyzing Database via Google Gemini..."):
                    model = genai.GenerativeModel('gemini-pro')
                    prompt = f"Analyze this workflow data and write a short summary on bottlenecks: {tasks_df.to_string()}"
                    res = model.generate_content(prompt)
                    st.markdown(f"<div class='premium-card'>{res.text}</div>", unsafe_allow_html=True)

    elif menu == "⚙️ Admin Settings":
        st.markdown("<h1>⚙️ Advanced Settings</h1>", unsafe_allow_html=True)
        
        st.markdown("<div class='premium-card'><h3>Data Export (CSV) & Cloud Backup</h3><p>Securely download database ledgers or sync directly to Google Cloud Storage.</p></div>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.download_button("📥 Export Task Ledger", tasks_df.to_csv(index=False), "tasks.csv", use_container_width=True)
        with col2:
            if st.button("☁️ Sync Backup to Google Cloud Storage", type="primary", use_container_width=True):
                from core_logic import GoogleCloudManager
                with st.spinner("Connecting to Google Cloud Platform..."):
                    res = GoogleCloudManager.backup_to_gcs()
                    st.info(res)
        
        st.markdown("<br><div class='premium-card' style='border-color: #ef4444;'><h3>Danger Zone</h3></div>", unsafe_allow_html=True)
        pwd = st.text_input("Root Access Token", type="password")
        if st.button("Execute Factory Reset", type="primary"):
            if pwd == "admin123":
                DBManager.execute("DELETE FROM tasks")
                DBManager.execute("DELETE FROM docs")
                DBManager.execute("DELETE FROM chat")
                DBManager.execute("DELETE FROM activity")
                get_tasks.clear(); get_docs.clear(); get_chat.clear(); get_activity.clear()
                st.success("Wipe complete.")
                st.rerun()
            else:
                st.error("Authentication failed.")

@st.dialog("Initialize Task")
def create_task_dialog(users_df, user_id, role):
    if not SecurityValidator.check_permission(role, 'create_task'):
        st.error("Access Denied.")
        return
        
    t = st.text_input("Task Title")
    d = st.text_area("Details")
    s = st.selectbox("Pipeline Stage", ["To Do", "In Progress", "Review", "Done"])
    p = st.selectbox("Priority Level", ["Low", "Medium", "High"])
    assignee = st.selectbox("Assign To", ["Unassigned"] + users_df['name'].tolist())
    
    if st.button("Commit to DB"):
        valid, msg = SecurityValidator.validate_task(t)
        if not valid: st.error(msg)
        else:
            a_id = None if assignee == "Unassigned" else int(users_df[users_df['name'] == assignee].iloc[0]['id'])
            DBManager.execute("INSERT INTO tasks (title, description, status, priority, assignee_id, creator_id, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              (t, d, s, p, a_id, user_id, datetime.date.today().isoformat(), datetime.date.today().isoformat()))
            DBManager.log_activity(user_id, f"Created task: {t}")
            get_tasks.clear(); get_activity.clear()
            st.rerun()

@st.dialog("Update Pipeline State")
def update_task_dialog(task, role, user_id):
    ns = st.selectbox("New State", ["To Do", "In Progress", "Review", "Done"], index=["To Do", "In Progress", "Review", "Done"].index(task['status']))
    col1, col2 = st.columns(2)
    if col1.button("Update State", type="primary"):
        DBManager.execute("UPDATE tasks SET status=? WHERE id=?", (ns, task['id']))
        DBManager.log_activity(user_id, f"Moved task to {ns}")
        get_tasks.clear(); get_activity.clear()
        st.rerun()
    if col2.button("Delete (Admin Only)"):
        if not SecurityValidator.check_permission(role, 'delete_task'):
            st.error("Security violation: Action blocked by RBAC.")
        else:
            DBManager.execute("DELETE FROM tasks WHERE id=?", (task['id'],))
            DBManager.log_activity(user_id, "Deleted a task")
            get_tasks.clear(); get_activity.clear()
            st.rerun()

@st.dialog("Create Document")
def create_doc_dialog(user_id):
    title = st.text_input("Document Title")
    cat = st.selectbox("Category", ["Engineering", "Product", "General"])
    if st.button("Initialize Doc"):
        if title:
            DBManager.execute("INSERT INTO docs (category, title, content, author_id, updated_at) VALUES (?, ?, ?, ?, ?)",
                              (cat, title, f"# {title}\nStart typing...", user_id, datetime.datetime.now().isoformat()))
            DBManager.log_activity(user_id, f"Created doc: {title}")
            get_docs.clear(); get_activity.clear()
            st.rerun()

if __name__ == "__main__":
    main()
