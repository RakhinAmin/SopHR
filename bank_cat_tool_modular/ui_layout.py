import streamlit as st
import glob
import os
import pandas as pd
from logic.utils import to_excel, read_uploaded_file

def render_sidebar():
    return st.sidebar.selectbox("Navigate", ["User Dashboard", "Admin Dashboard"])

def render_admin_login():
    st.warning("You must set a new admin username and password.")
    st.text_input("Username", key="login_username_input")
    st.text_input("Password", type="password", key="login_password_input")

def render_admin_dashboard():
    st.subheader("Admin Dashboard")
    st.info("This is just a placeholder. Logic should be placed inside `show_admin_dashboard` in app.py")

def render_rule_selection():
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

    return selected_rule_label, selected_rule_db, uploaded_rules_file

def render_file_inputs():
    st.markdown("### Output File Naming")
    client_name = st.text_input("Client Name (max 100 characters):", max_chars=100)
    cch_code = st.text_input("CCH Client Code (3–10 characters):", max_chars=10)
    raw_date = st.text_input("Year End Date (DDMMYYYY)", max_chars=8, help="e.g. 31122024")
    ye_date = f"YE{raw_date[4:] + raw_date[2:4] + raw_date[0:2]}" if raw_date and raw_date.isdigit() and len(raw_date) == 8 else ""
    return client_name, cch_code, raw_date, ye_date

def render_file_inputs_get_bank_file_upload():
    bank_file = st.file_uploader(
        "Upload your bank statement file (CSV or Excel):",
        type=["csv", "xlsx", "xls"],
        key="bank"
    )

    if bank_file and bank_file.name.endswith(".csv"):
        try:
            bank_file.seek(0)
            df_preview = pd.read_csv(bank_file, nrows=5)
            if "Description" not in df_preview.columns:
                st.warning("This file is missing a 'Description' column. Categorisation may fail.")
            bank_file.seek(0)
        except Exception as e:
            st.warning(f"Unable to preview file: {e}")

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

            # === NEW: Preview Excel sheet and warn if Description column missing ===
            df_preview = pd.read_excel(bank_file, sheet_name=sheet_to_process, nrows=5)
            if "Description" not in df_preview.columns:
                st.warning("This Excel sheet is missing a 'Description' column. Categorisation may fail.")
            bank_file.seek(0)

        except Exception as e:
            st.error(f"Failed to read Excel file: {e}")
            st.stop()
    return bank_file, sheet_to_process


def render_download_section(editable_df, custom_filename, bank_file, sheet_to_process):
    st.markdown("### Download Options")
    include_diagnostics = st.checkbox("Include diagnostic columns in download", value=False)

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
