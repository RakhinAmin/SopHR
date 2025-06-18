import pandas as pd  # For data manipulation and Excel I/O
from io import BytesIO  # For handling in-memory byte streams
import hashlib  # For password hashing
import json  # For reading and writing JSON files
import os  # For file system operations

# --- Convert DataFrame to Excel bytes ---
def to_excel(df):
    """
    Converts a pandas DataFrame to an in-memory Excel file (as bytes),
    suitable for download or streaming in web apps like Streamlit.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Categorised')
    return output.getvalue()

# --- Universal file reader (CSV or Excel) ---
def read_uploaded_file(file, sheet_name=None):
    """
    Reads an uploaded file and returns it as a pandas DataFrame.
    Supports CSV and Excel (.xlsx, .xls) formats.
    """
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, sheet_name=sheet_name or 0)
    else:
        raise ValueError("Unsupported file format")

# --- Admin password hashing ---
def hash_password(password):
    """
    Hashes the given password using SHA-256 and returns the hex digest.
    """
    return hashlib.sha256(password.encode()).hexdigest()

# --- Load admin credentials from JSON ---
def load_credentials():
    """
    Loads admin credentials from 'credentials.json'.
    If the file does not exist, a default is created and saved.
    """
    path = "credentials.json"
    if not os.path.exists(path):
        default = {"username": "admin", "password": hash_password("password"), "first_run": True}
        save_credentials(default)
        return default
    with open(path, "r") as f:
        return json.load(f)

# --- Save admin credentials to JSON ---
def save_credentials(creds):
    """
    Saves the provided credentials dictionary to 'credentials.json'.
    """
    with open("credentials.json", "w") as f:
        json.dump(creds, f)
