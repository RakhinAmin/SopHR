# === logic/admin_dashboard.py ===
from pathlib import Path
import streamlit as st
import os
import glob
import sqlite3
import pandas as pd
import datetime
from logic.session import BACKUP_DIR
from logic.utils import load_ruleset_usage
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
        db_labels = [os.path.basename(p) for p in db_paths]
        choice = st.selectbox("Select DB to merge into:", db_labels)
        existing_db = next(p for p, lbl in zip(db_paths, db_labels) if lbl == choice)

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

    # 4) Purge operations
    if db_paths:
        purge_labels = [os.path.basename(p) for p in db_paths]
        selected_label = st.selectbox("Select DB to manage:", purge_labels, key="purge_select")
        selected_db = next(p for p, lbl in zip(db_paths, purge_labels) if lbl == selected_label)

        if st.button("Purge Selected DB"):
            conn = sqlite3.connect(selected_db)
            df_rules = pd.read_sql("SELECT * FROM rules", conn)
            conn.execute("DELETE FROM rules")
            conn.commit()
            conn.close()

            backup_csv = os.path.join(
                BACKUP_DIR,
                os.path.basename(selected_db).replace(".db", ".csv")
            )
            df_rules.to_csv(backup_csv, index=False)
            st.success(f"Purged and backed up {selected_label}")

        if st.button("Purge All DBs"):
            for p in db_paths:
                conn = sqlite3.connect(p)
                df_rules = pd.read_sql("SELECT * FROM rules", conn)
                conn.execute("DELETE FROM rules")
                conn.commit()
                conn.close()

                backup_csv = os.path.join(
                    BACKUP_DIR,
                    os.path.basename(p).replace(".db", ".csv")
                )
                df_rules.to_csv(backup_csv, index=False)
            st.success("All DBs purged and backed up.")

    st.markdown("---")

    # --- Employee filter ---
    st.subheader("Filter by Employee")
    with sqlite3.connect("analytics.db") as conn:
        emp_df = pd.read_sql_query(
            "SELECT DISTINCT employee_name FROM usage_stats WHERE employee_name IS NOT NULL",
            conn
        )
    emp_list = ["All"] + sorted(emp_df["employee_name"].dropna().tolist())
    selected_emp = st.selectbox("Employee:", emp_list)

    # --- Date range filter ---
    st.subheader("Filter by Date Range")
    col_from, col_to = st.columns(2)
    from_str = col_from.text_input("From (DD/MM/YYYY)", key="analytics_from")
    to_str   = col_to.text_input("To   (DD/MM/YYYY)", key="analytics_to")

    # --- Load & filter raw stats ---
    raw = pd.read_sql_query("SELECT * FROM usage_stats", sqlite3.connect("analytics.db"))
    if selected_emp != "All":
        raw = raw[raw["employee_name"] == selected_emp]
    raw["run_date"] = pd.to_datetime(raw["run_at"]).dt.date

    # Apply date filtering
    try:
        d0 = datetime.datetime.strptime(from_str, "%d/%m/%Y").date() if from_str else raw["run_date"].min()
        d1 = datetime.datetime.strptime(to_str,   "%d/%m/%Y").date() if to_str   else raw["run_date"].max()
        if d0 > d1:
            st.error("From date must be on or before To date.")
            filtered = raw.iloc[0:0]
        else:
            mask = (raw["run_date"] >= d0) & (raw["run_date"] <= d1)
            filtered = raw.loc[mask]
    except ValueError:
        st.error("Invalid date format. Please use DD/MM/YYYY.")
        filtered = raw.iloc[0:0]

    # --- Usage Statistics Over Time ---
    st.subheader("Usage Statistics Over Time")
    if filtered.empty:
        st.info("No usage data for the selected filters.")
    else:
        summary = (
            filtered
            .groupby("run_date")
            .agg(
                runs=("id", "count"),
                total_transactions=("total_transactions", "sum"),
                categorised_transactions=("categorised_transactions", "sum"),
                auto_approved_count=("auto_approved_count", "sum"),
                avg_confidence=("avg_confidence", "mean")
            )
            .reset_index()
        )
        summary["run_date"] = pd.to_datetime(summary["run_date"]).dt.strftime("%d-%m-%Y")
        st.dataframe(summary)

    # --- Usage by Employee ---
    st.subheader("Usage by Employee")
    emp_summary = (
        filtered
        .groupby("employee_name")
        .agg(
            Runs               = ("id", "count"),
            Total_Transactions = ("total_transactions", "sum"),
            Categorised        = ("categorised_transactions", "sum"),
            Avg_Confidence     = ("avg_confidence", "mean")
        )
        .reset_index()
        .rename(columns={"employee_name": "Name"})
    )
    if emp_summary.empty:
        st.info("No employee usage data for the selected filters.")
    else:
        st.dataframe(emp_summary)

    # --- Rule-set Usage Over Time (line chart) ---
    st.subheader("Rule-set Usage Over Time")
    rs_counts = (
        filtered
        .groupby(["run_date", "rule_set"])
        .size()
        .reset_index(name="frequency")
    )
    if rs_counts.empty:
        st.info("No rule-set usage data for the selected filters.")
    else:
        rs_pivot = rs_counts.pivot(index="run_date", columns="rule_set", values="frequency").fillna(0)
        rs_pivot.index = pd.to_datetime(rs_pivot.index)
        st.line_chart(rs_pivot)
