# === IMPORTS ===
import os, time, tempfile  # Libraries for file operations, time tracking, and temporary directory access

def cleanup_temp_files(age_seconds=3600):
    """
    Deletes temporary files older than the specified age (default: 1 hour = 3600 seconds)
    """
    now = time.time()  # Current time in seconds since epoch
    tmp_dir = tempfile.gettempdir()  # Path to the system's temporary directory

    # Iterate over each file in the temporary directory
    for f in os.listdir(tmp_dir):
        fpath = os.path.join(tmp_dir, f)  # Full path to the file

        # Check if it's a file and if it's older than the specified age
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < now - age_seconds:
            try:
                os.remove(fpath)  # Attempt to delete the file
            except:
                pass  # Silently ignore errors (e.g., permission issues)
