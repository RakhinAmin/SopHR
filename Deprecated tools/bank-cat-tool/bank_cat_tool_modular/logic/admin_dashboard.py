# === logic/admin_dashboard.py ===
import streamlit as st
import os
import glob
import sqlite3
import pandas as pd
from logic.session import BACKUP_DIR

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
