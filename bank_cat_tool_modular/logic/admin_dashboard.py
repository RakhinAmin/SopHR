from pathlib import Path
import streamlit as st
import os
import glob
import sqlite3
import pandas as pd
from logic.session import BACKUP_DIR
from logic.utils import load_usage_summary, load_ruleset_usage
from logic.paths import DATA_DIR

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
    db_paths = sorted(glob.glob(str(DATA_DIR / "rules_*.db")))
    if mode == "Merge into existing database":
        if not db_paths:
            st.warning("No existing DBs to merge into—switch to 'Create new database'.")
            return
        # Show only filenames in the dropdown
        db_labels = [os.path.basename(p) for p in db_paths]
        choice = st.selectbox("Select DB to merge into:", db_labels)
        # Map the chosen label back to its full path
        existing_db = next(p for p, label in zip(db_paths, db_labels) if label == choice)

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
                db_path = str(DATA_DIR / f"{new_db_name}.db")
                if os.path.exists(db_path):
                    os.remove(db_path)
                conn = sqlite3.connect(db_path)
                df_existing = pd.DataFrame(columns=["description", "category"])
            else:
                db_path = existing_db
                conn = sqlite3.connect(db_path)
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

            st.success(f"{mode} succeeded. Database '{db_path}' now has {len(df_combined)} unique rules.")

        except Exception as e:
            st.error(f"Failed to import CSV: {e}")

    st.markdown("---")

    # 4) Purge operations (omitted for brevity)...

    st.markdown("---")

    # === Usage over time ===
    st.subheader("Usage Statistics Over Time")
    df_summary = load_usage_summary("analytics.db")
    if df_summary.empty:
        st.info("No usage data recorded yet.")
    else:
        st.dataframe(df_summary)

    # === Rule‐set counts ===
    st.subheader("Rule‐set Usage Counts")
    df_rules = load_ruleset_usage("analytics.db")
    if df_rules.empty:
        st.info("No rule‐set usage recorded yet.")
    else:
        st.table(df_rules)
        st.bar_chart(df_rules.set_index("rule_set")["runs"])
