# === app.py ===
import streamlit as st
from io import BytesIO

from logic.utils import (
    to_excel, read_uploaded_file, hash_password,
    load_credentials, save_credentials
)
from logic.session import SESSION_ID, USER_TEMP_DIR, BACKUP_DIR
from logic.categorisation import run_categorisation
from ui_layout import (
    render_sidebar,
    render_rule_selection,
    render_file_inputs,
    render_file_inputs_get_bank_file_upload,
    render_download_section
)

from fuzzy_logic_improved import TransactionCategorizer, Config

import json
import os
import glob
import sqlite3
import pandas as pd
import bcrypt
import time
import subprocess

# === Admin Session Timeout ===
SESSION_TIMEOUT_SECONDS = 30 * 60

def enforce_session_timeout():
    if "login_time" in st.session_state:
        if time.time() - st.session_state["login_time"] > SESSION_TIMEOUT_SECONDS:
            st.warning("Session expired due to inactivity.")
            st.session_state.clear()
            st.rerun()

# === Admin Auth Functions ===
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), ".secrets")
CREDENTIALS_PATH = os.path.join(CREDENTIALS_DIR, "credentials.json")

def load_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        default = {
            "username": "admin",
            "password": hash_password("password"),
            "recovery_pin": hash_password("1234"),
            "first_run": True
        }
        save_credentials(default)
        return default
    with open(CREDENTIALS_PATH, "r") as f:
        return json.load(f)

def save_credentials(creds):
    os.makedirs(CREDENTIALS_DIR, exist_ok=True)
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(creds, f)

def admin_login():
    creds = load_credentials()
    st.subheader("Admin Login")

    # === Force reset section ===
    if (
        st.session_state.get("admin_logged_in", False)
        and (st.session_state.get("force_password_reset", False) or creds.get("first_run", False))
    ):
        st.warning("You must set a new admin username, password, and recovery PIN.")

        new_username = st.text_input("New Admin Username", key="reset_username")
        new_password = st.text_input("New Password", type="password", key="reset_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="reset_confirm")
        new_pin = st.text_input("Set Recovery PIN (digits only)", type="password", key="reset_pin")

        if st.button("Update Credentials", key="update_creds_btn"):
            if not new_username or not new_password or not new_pin:
                st.error("Fields cannot be empty.")
            elif new_password != confirm_password:
                st.error("Passwords do not match.")
            elif not new_pin.isdigit() or len(new_pin) < 4:
                st.error("PIN must be numeric and at least 4 digits.")
            else:
                save_credentials({
                    "username": new_username,
                    "password": hash_password(new_password),
                    "recovery_pin": hash_password(new_pin),
                    "first_run": False
                })
                st.success("Credentials updated. Please log in again.")
                st.session_state.clear()
                st.rerun()
        return

    # === Regular Login UI ===
    username = st.text_input("Username", key="login_username_input")
    password = st.text_input("Password", type="password", key="login_password_input")

    if st.button("Login", key="login_btn"):
        if username == creds["username"] and verify_password(password, creds["password"]):
            if not creds["password"].startswith("$2b$"):
                creds["password"] = hash_password(password)
                save_credentials(creds)
                st.info("Your password has been upgraded to a more secure format.")
            st.session_state["admin_logged_in"] = True
            st.session_state["login_time"] = time.time()
            if creds.get("first_run", False):
                st.session_state["force_password_reset"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")

    # === Recovery via PIN ===
    with st.expander("Forgot Password?"):
        pin_attempt = st.text_input("Enter Recovery PIN", type="password", key="pin_reset_input")
        if st.button("Verify PIN and Reset Credentials", key="reset_btn"):
            if verify_password(pin_attempt, creds.get("recovery_pin", "")):
                st.session_state.clear()
                st.session_state["force_password_reset"] = True
                st.success("PIN verified. You may now reset your credentials.")
                st.rerun()
            else:
                st.error("Incorrect PIN.")

# === Admin Dashboard ===
def show_admin_dashboard():
    st.subheader("Admin Dashboard")

    if st.button("Log Out", key="admin_logout_btn"):
        st.session_state.clear()
        st.rerun()

    db_files = sorted(glob.glob("rules_*.db"))
    if not db_files:
        st.warning("No DB files found.")
        return

    selected_db = st.selectbox("Select DB to manage:", db_files)

    uploaded_csv = st.file_uploader("Upload CSV to import", type=["csv"])
    if uploaded_csv:
        try:
            df_new = pd.read_csv(uploaded_csv)
            df_new.columns = df_new.columns.str.lower().str.strip()
            if not {"description", "category"} <= set(df_new.columns):
                st.error("CSV must have 'description' and 'category' columns")
            else:
                conn = sqlite3.connect(selected_db)
                try:
                    df_existing = pd.read_sql("SELECT description, category FROM rules", conn)
                except Exception:
                    df_existing = pd.DataFrame(columns=["description", "category"])

                df_new = df_new[["description", "category"]].dropna()
                df_existing = df_existing[["description", "category"]].dropna()
                df_combined = pd.concat([df_existing, df_new], ignore_index=True).drop_duplicates()
                conn.execute("DROP TABLE IF EXISTS rules")
                df_combined.to_sql("rules", conn, index=False)
                conn.close()

                st.success(f"Imported {len(df_new)} new rows. Final total: {len(df_combined)} rows.")
        except Exception as e:
            st.error(f"Failed to import CSV: {e}")

    if st.button("Purge Selected DB"):
        conn = sqlite3.connect(selected_db)
        df = pd.read_sql("SELECT * FROM rules", conn)
        csv_name = os.path.join(BACKUP_DIR, os.path.basename(selected_db).replace(".db", ".csv"))
        df.to_csv(csv_name, index=False)
        conn.execute("DELETE FROM rules")
        conn.commit()
        conn.close()
        st.success(f"Purged and backed up {selected_db}")

    if st.button("Purge All DBs"):
        for db in db_files:
            conn = sqlite3.connect(db)
            df = pd.read_sql("SELECT * FROM rules", conn)
            csv_name = os.path.join(BACKUP_DIR, os.path.basename(db).replace(".db", ".csv"))
            df.to_csv(csv_name, index=False)
            conn.execute("DELETE FROM rules")
            conn.commit()
            conn.close()
        st.success("All DBs purged and backed up.")

# === STREAMLIT LAYOUT ===
st.set_page_config(page_title="Transaction Categorisation", layout="wide")

# === ROUTING ===
page = render_sidebar()

if page == "Admin Dashboard":
    if st.session_state.get("admin_logged_in", False):
        enforce_session_timeout()
        if st.session_state.get("force_password_reset", False):
            admin_login()
        else:
            show_admin_dashboard()
    else:
        admin_login()
    st.stop()

# === MAIN USER DASHBOARD ===
st.title("Bank Transaction Categorisation Tool")

selected_rule_label, selected_rule_db, uploaded_rules_file = render_rule_selection()
client_name, cch_code, raw_date, ye_date = render_file_inputs()
bank_file, sheet_to_process = render_file_inputs_get_bank_file_upload()

if st.button("Run Categorisation"):
    errors = []
    if not client_name.strip():
        errors.append("Client Name is required.")
    if not (3 <= len(cch_code.strip()) <= 10):
        errors.append("CCH Client Code must be between 3 and 10 characters.")
    if not (raw_date.isdigit() and len(raw_date) == 8):
        errors.append("Year End Date must be 8 digits in format DDMMYYYY.")
    if not bank_file:
        errors.append("You must upload a bank transaction file.")

    if errors:
        for err in errors:
            st.error(err)
        st.stop()

    with st.spinner("Processing transactions..."):
        result = run_categorisation(
            client_name=client_name,
            cch_code=cch_code,
            raw_date=raw_date,
            bank_file=bank_file,
            sheet_to_process=sheet_to_process,
            rules_file=uploaded_rules_file,
            built_in_db_path=selected_rule_db,
            session_id=SESSION_ID,
            user_temp_dir=USER_TEMP_DIR
        )

    if result.success:
        output_df = result.output_df
        st.success("Categorisation completed successfully!")
        st.dataframe(output_df)
        st.session_state["editable_df"] = output_df
        st.session_state["custom_filename"] = result.custom_filename
        st.session_state["bank_file"] = bank_file
        st.session_state["sheet_to_process"] = sheet_to_process
    else:
        st.error("Something went wrong during categorisation. Check logs.")

if (
    "editable_df" in st.session_state and
    "custom_filename" in st.session_state and
    "bank_file" in st.session_state
):
    render_download_section(
        st.session_state["editable_df"],
        st.session_state["custom_filename"],
        st.session_state["bank_file"],
        st.session_state.get("sheet_to_process")
    )
