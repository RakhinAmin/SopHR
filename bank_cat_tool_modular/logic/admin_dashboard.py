# === logic/admin_dashboard.py ===
import streamlit as st
import os
import glob
import sqlite3
import pandas as pd
from logic.session import BACKUP_DIR

def show_admin_dashboard():
    st.subheader("Admin Dashboard")

    # Log out button
    if st.button("Log Out", key="admin_logout_btn"):
        st.session_state.clear()
        st.rerun()

    # 1) Choose import mode
    mode = st.radio(
        "Import mode:",
        ("Create new database", "Merge into existing database"),
        index=1
    )

    # 2a) If merging, pick an existing DB
    existing_db = None
    db_files = sorted(glob.glob("rules_*.db"))
    if mode == "Merge into existing database":
        if not db_files:
            st.warning("No existing DBs to merge into—switch to 'Create new database'.")
            return
        existing_db = st.selectbox("Select DB to merge into:", db_files)

    # 2b) If creating new, ask for a filename
    new_db_name = None
    if mode == "Create new database":
        new_db_name = st.text_input(
            "New DB filename (without .db):",
            value="rules_new",
            help="A '.db' extension will be added automatically."
        ).strip()
        if not new_db_name:
            st.info("Enter a name to create a new database.")
    
    # 3) Upload CSV
    uploaded_csv = st.file_uploader("Upload CSV to import", type=["csv"])
    if uploaded_csv:
        try:
            df_new = pd.read_csv(uploaded_csv)
            df_new.columns = df_new.columns.str.lower().str.strip()
            if not {"description", "category"}.issubset(df_new.columns):
                st.error("CSV must have at least 'description' and 'category' columns.")
                return

            # Determine target DB path
            if mode == "Create new database":
                db_path = f"{new_db_name}.db"
                # remove existing file if overriding
                if os.path.exists(db_path):
                    os.remove(db_path)
                conn = sqlite3.connect(db_path)
                df_existing = pd.DataFrame(columns=["description", "category"])
            else:
                db_path = existing_db
                conn = sqlite3.connect(db_path)
                # load existing rules or start empty if table missing
                try:
                    df_existing = pd.read_sql("SELECT description, category FROM rules", conn)
                except Exception:
                    df_existing = pd.DataFrame(columns=["description", "category"])

            # Combine and dedupe
            df_combined = pd.concat([df_existing, df_new[["description", "category"]]], ignore_index=True)
            df_combined = df_combined.drop_duplicates().reset_index(drop=True)

            # Write back to SQLite
            conn.execute("DROP TABLE IF EXISTS rules")
            df_combined.to_sql("rules", conn, index=False)
            conn.close()

            st.success(
                f"{mode} succeeded. Database '{db_path}' now has {len(df_combined)} unique rules."
            )

        except Exception as e:
            st.error(f"Failed to import CSV: {e}")

    st.markdown("---")

    # 4) Purge operations
    if db_files:
        selected_db = st.selectbox("Select DB to manage:", db_files, key="purge_select")
        if st.button("Purge Selected DB"):
            conn = sqlite3.connect(selected_db)
            df = pd.read_sql("SELECT * FROM rules", conn)
            conn.execute("DELETE FROM rules"); conn.commit(); conn.close()
            csv_name = os.path.join(
                BACKUP_DIR, os.path.basename(selected_db).replace(".db", ".csv")
            )
            df.to_csv(csv_name, index=False)
            st.success(f"Purged and backed up {selected_db}")

        if st.button("Purge All DBs"):
            for db in db_files:
                conn = sqlite3.connect(db)
                df = pd.read_sql("SELECT * FROM rules", conn)
                conn.execute("DELETE FROM rules"); conn.commit(); conn.close()
                csv_name = os.path.join(
                    BACKUP_DIR, os.path.basename(db).replace(".db", ".csv")
                )
                df.to_csv(csv_name, index=False)
            st.success("All DBs purged and backed up.")
