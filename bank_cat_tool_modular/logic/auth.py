# === logic/auth.py ===
import streamlit as st
import bcrypt
import json
import os
import time

DEFAULT_HASHED_PASSWORD = "$2b$12$mg9gXX9ddxfwI7p6nKQRe.idw6We11jCJ6mxQNnjS0bzwtca6zVT2"  # 'password'
DEFAULT_HASHED_PIN = "$2b$12$pvtnsxmS3atyJGYsTu0kGOi4K2h/xhZkhzZyPF3pV3N14EHtTLCD2"       # '1234'

CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "..", ".secrets")
CREDENTIALS_PATH = os.path.join(CREDENTIALS_DIR, "credentials.json")

SESSION_TIMEOUT_SECONDS = 30 * 60

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def load_credentials():
    if not os.path.exists(CREDENTIALS_PATH):
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        default = {
            "username": "admin",
            "password": DEFAULT_HASHED_PASSWORD,
            "recovery_pin": DEFAULT_HASHED_PIN,
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

def enforce_session_timeout():
    if "login_time" in st.session_state:
        if time.time() - st.session_state["login_time"] > SESSION_TIMEOUT_SECONDS:
            st.warning("Session expired due to inactivity.")
            st.session_state.clear()
            st.rerun()

def admin_login():
    creds = load_credentials()
    st.subheader("Admin Login")

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

    with st.expander("Forgot Password?"):
        pin_attempt = st.text_input("Enter Recovery PIN", type="password", key="pin_reset_input")
        if st.button("Verify PIN and Reset Credentials", key="reset_btn"):
            if verify_password(pin_attempt, creds.get("recovery_pin", "")):
                st.session_state["force_password_reset"] = True
                st.session_state["admin_logged_in"] = True
                st.success("PIN verified. You may now reset your credentials.")
                st.rerun()
            else:
                st.error("Incorrect PIN.")