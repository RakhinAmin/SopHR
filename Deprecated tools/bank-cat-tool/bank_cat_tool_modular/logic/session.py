import tempfile  # Provides functions to access the system's temporary file directory
import os        # OS-level file and path operations
import uuid      # For generating a unique session identifier

# === Unique session ID and temporary directory ===
SESSION_ID = str(uuid.uuid4())[:8]  # Generate a short unique session ID using UUID
USER_TEMP_DIR = os.path.join(tempfile.gettempdir(), f"session_{SESSION_ID}")  # Create a session-specific temp folder
os.makedirs(USER_TEMP_DIR, exist_ok=True)  # Ensure the temp folder exists; create it if not

# === Backup directory for CSV exports of DB rules ===
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "..", "backups")  # Path to a backups folder one level above the script's directory
os.makedirs(BACKUP_DIR, exist_ok=True)  # Ensure the backups folder exists; create it if not
