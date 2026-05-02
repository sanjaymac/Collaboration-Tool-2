import sqlite3
import datetime
import html
import os
import re

DB_FILE = "data/collab_pro.db"

class SecurityValidator:
    """Security Layer: Handles Input Validation and Access Control (RBAC)."""
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Stops Cross-Site Scripting (XSS) and Buffer Overflows."""
        if not text: return ""
        return html.escape(str(text).strip()[:2000]) # Strict 2000 char limit
        
    @staticmethod
    def validate_task(title: str) -> tuple[bool, str]:
        """Edge-case validation for inputs."""
        if not title or len(title.strip()) < 3:
            return False, "Title must be at least 3 characters."
        if len(title) > 150:
            return False, "Title exceeds maximum 150 characters."
        if not re.match(r'^[\w\s\-\.\!]+$', title):
            return False, "Title contains invalid special characters."
        return True, "Valid"
        
    @staticmethod
    def check_permission(user_role: str, action: str) -> bool:
        """Role-Based Access Control (RBAC) to fix Security Exposure."""
        if user_role == 'Admin': 
            return True
        if action in ['delete_task', 'factory_reset', 'manage_users']: 
            return False
        return True

class DBManager:
    """Architecture Layer: Centralized Database Management."""
    
    @staticmethod
    def get_conn():
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_db():
        os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
        with DBManager.get_conn() as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, role TEXT, avatar TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, description TEXT, status TEXT, priority TEXT, assignee_id INTEGER, creator_id INTEGER, due_date TEXT, created_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, timestamp TEXT)''')
            
            c.execute("SELECT COUNT(*) FROM users")
            if c.fetchone()[0] == 0:
                c.executemany("INSERT INTO users (name, role, avatar) VALUES (?, ?, ?)", 
                              [('Alice', 'Admin', '👩‍💼'), ('Bob', 'Member', '👨‍💻'), ('Charlie', 'Viewer', '🎨')])
            conn.commit()

    @staticmethod
    def execute(query: str, params: tuple = ()):
        with DBManager.get_conn() as conn:
            c = conn.cursor()
            c.execute(query, params)
            conn.commit()
            
    @staticmethod
    def log_activity(user_id: int, action: str):
        DBManager.execute("INSERT INTO activity (user_id, action, timestamp) VALUES (?, ?, ?)", 
                          (user_id, SecurityValidator.sanitize(action), datetime.datetime.now().isoformat()))
