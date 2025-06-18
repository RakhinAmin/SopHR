import tempfile
import os
import uuid

# === Unique session ID and temporary directory ===
SESSION_ID = str(uuid.uuid4())[:8]
USER_TEMP_DIR = os.path.join(tempfile.gettempdir(), f"session_{SESSION_ID}")
os.makedirs(USER_TEMP_DIR, exist_ok=True)

# === Backup directory for CSV exports of DB rules ===
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)
