import sqlite3
import datetime
import html
import os
import re

DB_FILE = "data/collab_pro.db"

# --- GOOGLE CLOUD SERVICES ---
try:
    from google.cloud import storage
    import google.cloud.logging
    GCP_AVAILABLE = True
except ImportError:
    GCP_AVAILABLE = False

class GoogleCloudManager:
    """Manages deep integration with Google Cloud Platform services."""
    
    @staticmethod
    def backup_to_gcs(bucket_name="collab-space-backups-9912"):
        """Backs up the local SQLite database to Google Cloud Storage (GCS)."""
        if not GCP_AVAILABLE: 
            return "GCP Libraries not installed."
        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            if not bucket.exists():
                bucket = client.create_bucket(bucket_name)
            
            blob_name = f"database_backups/collab_db_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(DB_FILE)
            return "Successfully synced securely to Google Cloud Storage!"
        except Exception as e:
            return f"GCP Authentication pending (Normal if running locally without service account): {str(e)}"
            
    @staticmethod
    def init_cloud_logging():
        """Pipes standard logs into Google Cloud Logging for production observability."""
        if GCP_AVAILABLE:
            try:
                client = google.cloud.logging.Client()
                client.setup_logging()
            except Exception:
                pass

# Initialize cloud logging natively
GoogleCloudManager.init_cloud_logging()

# --- CORE ARCHITECTURE ---
class SecurityValidator:
    """Security Layer: Handles Input Validation and Access Control (RBAC)."""
    
    @staticmethod
    def sanitize(text: str) -> str:
        """Stops Cross-Site Scripting (XSS) and Buffer Overflows."""
        if not text: return ""
        return html.escape(str(text).strip()[:2000])
        
    @staticmethod
    def validate_task(title: str) -> tuple[bool, str]:
        """Edge-case validation for inputs."""
        if not title or len(title.strip()) < 3:
            return False, "Title must be at least 3 characters."
        if len(title) > 150:
            return False, "Title exceeds maximum 150 characters."
        return True, "Valid"
        
    @staticmethod
    def check_permission(user_role: str, action: str) -> bool:
        """Role-Based Access Control (RBAC)."""
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
            c.execute('''CREATE TABLE IF NOT EXISTS docs (id INTEGER PRIMARY KEY, category TEXT, title TEXT, content TEXT, author_id INTEGER, updated_at TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS chat (id INTEGER PRIMARY KEY, user_id INTEGER, message TEXT, timestamp TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS activity (id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, timestamp TEXT)''')
            
            c.execute("SELECT COUNT(*) FROM users")
            if c.fetchone()[0] == 0:
                c.executemany("INSERT INTO users (name, role, avatar) VALUES (?, ?, ?)", 
                              [('Alice', 'Admin', '👩‍💼'), ('Bob', 'Member', '👨‍💻'), ('Charlie', 'Viewer', '🎨')])
                c.executemany("INSERT INTO tasks (title, description, status, priority, assignee_id, creator_id, due_date, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                              [('Design System Update', 'Create new color tokens.', 'In Progress', 'High', 3, 1, datetime.date.today().isoformat(), datetime.date.today().isoformat()),
                               ('Deploy to Cloud Run', 'Setup Docker and Github actions.', 'To Do', 'High', 2, 1, (datetime.date.today() + datetime.timedelta(days=3)).isoformat(), datetime.date.today().isoformat())])
                c.execute("INSERT INTO docs (category, title, content, author_id, updated_at) VALUES (?, ?, ?, ?, ?)",
                          ('Engineering', 'API Specs', '# Core API\nUse REST.', 2, datetime.datetime.now().isoformat()))
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
