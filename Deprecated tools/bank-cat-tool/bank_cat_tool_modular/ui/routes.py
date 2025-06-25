# === ui/routes.py ===
import streamlit as st
from logic.auth import admin_login, enforce_session_timeout
from logic.admin_dashboard import show_admin_dashboard
from logic.session import SESSION_ID, USER_TEMP_DIR
from logic.categorisation import run_categorisation
from ui_layout.ui_inputs import (
    render_sidebar, render_rule_selection, render_file_inputs,
    render_file_inputs_get_bank_file_upload, render_download_section
)
from ui_layout.styles import apply_custom_styles
import tempfile


def route_page():
    apply_custom_styles()
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

    # === User Dashboard ===
    st.title("Bank Analysis Tool")

    selected_rule_label, selected_rule_db, uploaded_rules_file = render_rule_selection()
    client_name, cch_code, raw_date, ye_date = render_file_inputs()
    bank_file, sheet_to_process = render_file_inputs_get_bank_file_upload()

    if st.button("Run Categorisation"):
        st.session_state["trigger_categorisation"] = True

    if st.session_state.get("trigger_categorisation", False):
        st.session_state["trigger_categorisation"] = False

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

        if not uploaded_rules_file and not selected_rule_db:
            st.error("You must either upload a rules CSV file or select a built-in rule database.")
            st.stop()

        tmp_uploaded_rules_path = None
        if uploaded_rules_file:
            uploaded_rules_file.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=USER_TEMP_DIR) as tmp_file:
                tmp_file.write(uploaded_rules_file.read())
                tmp_uploaded_rules_path = tmp_file.name

        with st.spinner("Processing transactions..."):
            result = run_categorisation(
                client_name=client_name,
                cch_code=cch_code,
                raw_date=raw_date,
                bank_file=bank_file,
                sheet_to_process=sheet_to_process,
                rules_path=tmp_uploaded_rules_path,
                built_in_db_path=selected_rule_db,
                session_id=SESSION_ID,
                user_temp_dir=USER_TEMP_DIR
            )

        if not result.success:
            st.error("Categorisation failed. Make sure your bank file includes a 'Description' column.")
            st.stop()

        st.success("Categorisation completed successfully!")
        st.dataframe(result.output_df)

        st.markdown("### Categorisation Summary")
        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Total Transactions", result.report["total_transactions"])
        col2.metric("Categorised", result.report["categorised"])
        col3.metric("Uncategorised", result.report["uncategorised"])
        rate = result.report["categorisation_rate"]
        rate_colour = "red" if rate < 50 else "black"
        col4.markdown(
            f"""
            <div style='text-align: center;'>
                <span style='font-weight: 600;'>Categorisation Rate</span><br>
                <span style='font-size: 2em; color: {rate_colour};'>{rate:.2f}%</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1.metric("Auto-Approved", result.report["auto_approved"])
        col2.metric("Avg Confidence", f"{result.report['avg_confidence']}%")
        col3.metric("High Confidence Matches", result.report["high_confidence_matches"])

        st.session_state["editable_df"] = result.output_df
        st.session_state["custom_filename"] = result.custom_filename
        st.session_state["bank_file"] = bank_file
        st.session_state["sheet_to_process"] = sheet_to_process

    if all(k in st.session_state for k in ["editable_df", "custom_filename", "bank_file"]):
        render_download_section(
            st.session_state["editable_df"],
            st.session_state["custom_filename"],
            st.session_state["bank_file"],
            st.session_state.get("sheet_to_process")
        )