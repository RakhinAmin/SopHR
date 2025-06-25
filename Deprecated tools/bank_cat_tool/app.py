# === app.py ===
import streamlit as st
import pandas as pd
import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
import glob
from io import BytesIO
from fuzzy_logic_improved import TransactionCategorizer, Config
from preprocess_bank_data import extract_values_column

# === SETUP ===
SESSION_ID = str(uuid.uuid4())[:8]
USER_TEMP_DIR = os.path.join(tempfile.gettempdir(), f"session_{SESSION_ID}")
os.makedirs(USER_TEMP_DIR, exist_ok=True)
BACKUP_DIR = os.path.join(os.path.dirname(__file__), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

# === UTILITY FUNCTIONS ===
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Categorised')
    return output.getvalue()

def read_uploaded_file(file, sheet_name=None):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith((".xlsx", ".xls")):
        return pd.read_excel(file, sheet_name=sheet_name or 0)
    else:
        raise ValueError("Unsupported file format")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def load_credentials():
    path = "credentials.json"
    if not os.path.exists(path):
        default = {"username": "admin", "password": hash_password("password"), "first_run": True}
        save_credentials(default)
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_credentials(creds):
    with open("credentials.json", "w") as f:
        json.dump(creds, f)

# === ADMIN AUTH ===
def admin_login():
    creds = load_credentials()
    st.subheader("Admin Login")

    # If already logged in
    if st.session_state.get("admin_logged_in", False):

        # If user needs to reset credentials
        if st.session_state.get("force_password_reset", False) or creds.get("first_run", False):
            st.warning("You must set a new admin username and password.")

            new_username = st.text_input("New Admin Username", key="reset_username")
            new_password = st.text_input("New Password", type="password", key="reset_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="reset_confirm")

            if st.button("Update Credentials", key="update_creds_btn"):
                if not new_username or not new_password:
                    st.error("Fields cannot be empty.")
                elif new_password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    save_credentials({
                        "username": new_username,
                        "password": hash_password(new_password),
                        "first_run": False
                    })
                    st.success("Credentials updated. Please log in again.")
                    st.session_state.clear()
                    st.stop()
            return

        # Fully authenticated and no reset required
        st.success(f"Logged in as {creds['username']}")
        if st.button("Log Out", key="logout_btn"):
            st.session_state.clear()
            st.rerun()
        return

    # Not logged in yet
    username = st.text_input("Username", key="login_username_input")
    password = st.text_input("Password", type="password", key="login_password_input")

    if st.button("Login", key="login_btn"):
        if username == creds["username"] and hash_password(password) == creds["password"]:
            st.session_state["admin_logged_in"] = True
            if creds.get("first_run", False):
                st.session_state["force_password_reset"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")

# === ADMIN DASHBOARD ===
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
        df_new = pd.read_csv(uploaded_csv)
        df_new.columns = df_new.columns.str.lower().str.strip()
        if not {"description", "category"} <= set(df_new.columns):
            st.error("CSV must have 'description' and 'category'")
        else:
            conn = sqlite3.connect(selected_db)
            df_existing = pd.read_sql("SELECT description, category FROM rules", conn)
            df_combined = pd.concat([df_existing, df_new]).drop_duplicates()
            df_combined.to_sql("rules", conn, if_exists="replace", index=False)
            conn.close()
            st.success("Imported and deduplicated rules.")

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
page = st.sidebar.selectbox("Navigate", ["User Dashboard", "Admin Dashboard"])

# === ROUTING ===
if page == "Admin Dashboard":
    if st.session_state.get("admin_logged_in", False):

        # Prevent access if password reset is still required
        if st.session_state.get("force_password_reset", False):
            admin_login()  # Show reset form
        else:
            show_admin_dashboard()

    else:
        admin_login()

    st.stop()
else:
    st.title("Bank Transaction Categorisation Tool")

    st.markdown("### Choose Rule Set")
    col1, col2 = st.columns([2, 3])

    with col1:
        st.markdown("#### Built-in Rule Sets (from DB)")
        available_rule_dbs = sorted(glob.glob("rules_*.db"))
        db_choices = {os.path.basename(f).replace("rules_", "").replace(".db", "").title(): f for f in available_rule_dbs}
        selected_rule_label = st.selectbox("Select a built-in ruleset:", options=list(db_choices.keys()))
        selected_rule_db = db_choices[selected_rule_label]

    with col2:
        st.markdown("#### Or Drag and Drop a Custom Rules File")
        with open("rules_template.csv", "r") as template_file:
            st.download_button(
                label="Download Rules Template CSV",
                data=template_file.read(),
                file_name="rules_template.csv",
                mime="text/csv"
            )

        uploaded_rules_file = st.file_uploader(
            label="Drop your custom rules CSV here:",
            type=["csv"],
            help="This will override the selected built-in rule set"
        )

    st.markdown("### Output File Naming")
    client_name = st.text_input("Client Name (max 100 characters):", max_chars=100)
    cch_code = st.text_input("CCH Client Code (3–10 characters):", max_chars=10)
    raw_date = st.text_input("Year End Date (DDMMYYYY)", max_chars=8, help="e.g. 31122024")

    ye_date = f"YE{raw_date[4:] + raw_date[2:4] + raw_date[0:2]}" if raw_date and raw_date.isdigit() and len(raw_date) == 8 else ""

    bank_file = st.file_uploader(
        "Upload your bank statement file (CSV or Excel):",
        type=["csv", "xlsx", "xls"],
        key="bank"
    )

    sheet_to_process = None
    if bank_file and bank_file.name.endswith((".xlsx", ".xls")):
        try:
            bank_file.seek(0)
            excel_obj = pd.ExcelFile(bank_file)
            sheet_names = excel_obj.sheet_names
            if len(sheet_names) > 1:
                sheet_to_process = st.selectbox("Select the sheet to process:", sheet_names)
            else:
                sheet_to_process = sheet_names[0]
            bank_file.seek(0)
        except Exception as e:
            st.error(f"Failed to read Excel file: {e}")
            st.stop()

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

        original_df = read_uploaded_file(bank_file, sheet_name=sheet_to_process)
        preprocessed_df = extract_values_column(original_df.copy())

        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=USER_TEMP_DIR) as tmp_bank:
            preprocessed_df.to_csv(tmp_bank.name, index=False)
            tmp_bank_path = tmp_bank.name

        if uploaded_rules_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=USER_TEMP_DIR) as tmp_rules:
                tmp_rules.write(uploaded_rules_file.getvalue())
                tmp_rules_path = tmp_rules.name
            st.success("Using uploaded custom rules file.")
            db_conn = None
        else:
            st.info(f"Using built-in rules from: {selected_rule_label}")
            tmp_rules_path = ""
            db_conn = sqlite3.connect(selected_rule_db)

        safe_client = "".join(c for c in client_name if c.isalnum() or c in ("_", "-")).strip().replace(" ", "_")
        safe_cch = "".join(c for c in cch_code if c.isalnum()).strip().upper()
        final_date = f"YE{raw_date}"
        custom_filename = f"{safe_client}_{safe_cch}_{final_date}_{SESSION_ID}.csv"
        output_path = os.path.join(USER_TEMP_DIR, custom_filename)

        config = Config(
            bank_statement_file=tmp_bank_path,
            rules_file=tmp_rules_path,
            output_file=output_path
        )
        categorizer = TransactionCategorizer(config)

        with st.spinner("Processing transactions..."):
            if categorizer.run_categorization(db_conn=db_conn):
                output_df = pd.read_csv(output_path)
                st.success("Categorisation completed successfully!")
                st.dataframe(output_df)

                st.session_state["editable_df"] = output_df
                st.session_state["custom_filename"] = custom_filename
                st.session_state["bank_file"] = bank_file
            else:
                st.error("Something went wrong during categorisation. Check logs.")

    if (
        "editable_df" in st.session_state and
        "custom_filename" in st.session_state and
        "bank_file" in st.session_state and
        isinstance(st.session_state["bank_file"], (BytesIO, st.runtime.uploaded_file_manager.UploadedFile))
    ):
        st.markdown("### Download Options")
        include_diagnostics = st.checkbox("Include diagnostic columns in download", value=False)

        editable_df = st.session_state["editable_df"]
        custom_filename = st.session_state["custom_filename"]
        bank_file = st.session_state["bank_file"]

        bank_file.seek(0)
        original_preserved_df = read_uploaded_file(bank_file, sheet_name=sheet_to_process)
        clean_export = original_preserved_df.copy()

        if "Category" in editable_df.columns:
            clean_export["Category"] = editable_df["Category"]
        if "Values" in editable_df.columns:
            clean_export["Values"] = editable_df["Values"]

        if include_diagnostics:
            st.download_button(
                label="Download Full Categorised CSV (with diagnostics)",
                data=editable_df.to_csv(index=False).encode("utf-8"),
                file_name=custom_filename,
                mime="text/csv"
            )
            st.download_button(
                label="Download Full Categorised Excel (with diagnostics)",
                data=to_excel(editable_df),
                file_name=custom_filename.replace(".csv", ".xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.download_button(
                label="Download Clean Categorised CSV (Original + Category and Values only)",
                data=clean_export.to_csv(index=False).encode("utf-8"),
                file_name=custom_filename.replace(".csv", "_clean.csv"),
                mime="text/csv"
            )
            st.download_button(
                label="Download Clean Categorised Excel (Original + Category and Values only)",
                data=to_excel(clean_export),
                file_name=custom_filename.replace(".csv", "_clean.xlsx"),
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
