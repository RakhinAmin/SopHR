import pandas as pd  # For data manipulation and Excel I/O
from io import BytesIO  # For handling in-memory byte streams
import hashlib  # For password hashing
import json  # For reading and writing JSON files
import os  # For file system operations
import sqlite3

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

import streamlit as st

import base64

def load_icon_base64(path: str) -> str:
    """Load a local PNG icon and convert it to a base64 data URI."""
    with open(path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

def inline_label_with_help(label: str, help_text: str):
    icon_data_uri = load_icon_base64("help.png")  # adjust if needed

    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 6px; font-weight: 400; margin-bottom: -2px;">
        <span>{label}</span>
        <div title="{help_text}" style="padding: 8px; border-radius: 6px; cursor: help; display: flex; align-items: center; justify-content: center;">
            <img src="{icon_data_uri}"
                 width="20" height="20"
                 style="pointer-events: none;" />
        </div>
    </div>
    """, unsafe_allow_html=True)


def inline_text_input_with_help(label: str, help_text: str, key: str, max_chars=None):
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 6px; margin-bottom: -8px;">
            <span style="font-weight: 400;">{label}</span>
            <span style="cursor: help;" title="{help_text}">
                <svg xmlns="http://www.w3.org/2000/svg" height="16" width="16" viewBox="0 0 24 24"
                    fill="none" stroke="#6c757d" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="16" x2="12" y2="12"/>
                    <line x1="12" y1="8" x2="12" y2="8"/>
                </svg>
            </span>
        </div>
    """, unsafe_allow_html=True)

    # Use a non-empty hidden label to suppress Streamlit warnings
    return st.text_input(
        label="hidden_label_for_accessibility",
        label_visibility="collapsed",
        key=key,
        max_chars=max_chars
    )

def load_usage_summary(db_path: str = "analytics.db") -> pd.DataFrame:
    df = pd.read_sql_query("SELECT * FROM usage_stats", sqlite3.connect(db_path))
    if df.empty:
        return df

    # Ensure numeric
    for col in ["total_transactions", "categorised_transactions", "uncategorised_transactions", "auto_approved_count", "avg_confidence"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["run_date"] = pd.to_datetime(df["run_at"]).dt.date
    return (
        df.groupby("run_date")
          .agg(
            runs=("id", "count"),
            total_transactions=("total_transactions", "sum"),
            categorised_transactions=("categorised_transactions", "sum"),
            auto_approved_count=("auto_approved_count", "sum"),
            avg_confidence=("avg_confidence", "mean")
          )
          .reset_index()
    )


def load_ruleset_usage(db_path: str = "analytics.db") -> pd.DataFrame:
    """
    Returns a DataFrame with columns:
      rule_set, runs
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            "SELECT rule_set, COUNT(*) AS runs FROM usage_stats GROUP BY rule_set",
            conn
        )
    return df

