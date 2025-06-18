import pandas as pd
from io import BytesIO
import hashlib
import json
import os

# --- Convert DataFrame to Excel bytes ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Categorised')
    return output.getvalue()

# --- Universal file reader (CSV or Excel) ---
def read_uploaded_file(file, sheet_name=None):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, sheet_name=sheet_name or 0)
    else:
        raise ValueError("Unsupported file format")

# --- Admin password hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Load admin credentials from JSON ---
def load_credentials():
    path = "credentials.json"
    if not os.path.exists(path):
        default = {"username": "admin", "password": hash_password("password"), "first_run": True}
        save_credentials(default)
        return default
    with open(path, "r") as f:
        return json.load(f)

# --- Save admin credentials to JSON ---
def save_credentials(creds):
    with open("credentials.json", "w") as f:
        json.dump(creds, f)
