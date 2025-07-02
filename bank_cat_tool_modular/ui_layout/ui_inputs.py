import streamlit as st
import glob
import os
import pandas as pd
from logic.utils import inline_text_input_with_help, to_excel, read_uploaded_file, inline_label_with_help
from logic.paths import DATA_DIR

def render_sidebar():
    return st.sidebar.selectbox("Navigate", ["User Dashboard", "Admin Dashboard"])

def render_admin_login():
    st.warning("You must set a new admin username and password.")
    st.text_input("Admin Username", key="login_username_input", label_visibility="collapsed")
    st.text_input("Admin Password", type="password", key="login_password_input", label_visibility="collapsed")

def render_admin_dashboard():
    st.subheader("Admin Dashboard")
    st.info("This is just a placeholder. Logic should be placed inside `show_admin_dashboard` in app.py")

from logic.utils import load_icon_base64  # Make sure this is in your imports

def render_rule_selection():
    st.markdown("### Choose Rule Set")

    st.markdown("""
    <style>
      /* Panel cards on either side */
      div[data-testid="column"]:nth-of-type(1),
      div[data-testid="column"]:nth-of-type(3) {
        border: 1px solid #bbb;
        border-radius: 8px;
        padding: 16px;
        background: #edf2f7;
        display: flex !important;
        flex-direction: column;
        justify-content: flex-start !important;
      }

      /* Make the middle column a full-height flexbox */
      div[data-testid="column"]:nth-of-type(2) {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
      }

      /* Style the OR text inside it */
      div[data-testid="column"]:nth-of-type(2) > div {
        font-size: 80rem !important;
        font-weight: 700 !important;
        color: #223A5E !important;
        margin: 0 !important;
      }
    </style>
    """, unsafe_allow_html=True)

    col1, col_or, col2 = st.columns([0.4, 0.5, 0.4])


    with col1:
        st.markdown("#### Built-in Rule Sets")
        available_rule_dbs = sorted(glob.glob(str(DATA_DIR / "rules_*.db")))
        db_choices = {
            os.path.basename(f).replace("rules_", "").replace(".db", "").title(): f
            for f in available_rule_dbs
        }
        selected_rule_label = st.selectbox("Select a built-in ruleset:", options=list(db_choices.keys()))
        selected_rule_db = db_choices[selected_rule_label]

        st.markdown("<div style='height: 140px;'></div>", unsafe_allow_html=True)

    with col_or:
        st.markdown("<div style='text-align: center; font-weight: bold; color: #6d6e71; font-size: 40px; padding-top: 80px;'>OR</div>",
                    unsafe_allow_html=True)

    with col2:
        st.markdown("#### Custom Rules File")

        # Use your PNG icon from root
        icon_data_uri = load_icon_base64("help.png")

        st.markdown(f"""
        <style>
        .custom-help-label {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-weight: 500;
            margin-bottom: 6px;
        }}
        .custom-help-label img {{
            width: 18px;
            height: 18px;
            cursor: pointer;
        }}
        </style>
        <div class="custom-help-label">
            <span>Drop your custom rules CSV here:</span>
            <img src="{icon_data_uri}" title="This will override the selected built-in rule set" />
        </div>
        """, unsafe_allow_html=True)

        template_path = DATA_DIR / "rules_template.csv"
        with open(template_path, "r") as template_file:
            st.download_button(
                label="Download Rules Template CSV",
                data=template_file.read(),
                file_name="rules_template.csv",
                mime="text/csv"
            )
            
        st.markdown("""
        <style>
        /* Remove extra gap under download button */
        div[data-testid="stDownloadButton"] {
            margin-bottom: 0px !important;
        }
        /* Remove extra gap above uploader */
        div[data-testid="stFileUploader"] {
            margin-top: -50px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        uploaded_rules_file = st.file_uploader(
            label=" ",  # Empty to suppress default label warning
            type=["csv"],
            key="custom_rules_file"
        )

    return selected_rule_label, selected_rule_db, uploaded_rules_file

def render_file_inputs():
        # Tighten up all text‐input spacing
    st.markdown("""
        <style>
        /* Shrink top & bottom margins around each text-input container */
        div[data-testid="stTextInput"] {
            margin-top: 4px !important;
            margin-bottom: 4px !important;
        }
        /* Shrink bottom margin under inline labels (the info‐icon rows) */
        .custom-help-label, .inline-label {
            margin-bottom: 2px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("### Client Details (Mandatory)")

    inline_label_with_help("Client Name:", "Maximum 100 characters")
    client_name = st.text_input(
        label="Client Name", 
        key="client_name_input", 
        max_chars=100, 
        label_visibility="collapsed"
    )

    inline_label_with_help("CCH Client Code:", "3–10 characters (e.g. 123XYZ)")
    cch_code = st.text_input(
        label="CCH Client Code", 
        key="cch_code_input", 
        max_chars=10, 
        label_visibility="collapsed"
    )

    inline_label_with_help("Year End Date (DDMMYYYY):", "e.g. 31122024")
    raw_date = st.text_input(
        label="Year End Date", 
        key="raw_date_input", 
        max_chars=8, 
        label_visibility="collapsed"
    )

    ye_date = (
        f"YE{raw_date[4:] + raw_date[2:4] + raw_date[0:2]}"
        if raw_date and raw_date.isdigit() and len(raw_date) == 8
        else ""
    )

    return client_name, cch_code, raw_date, ye_date

def render_file_inputs_get_bank_file_upload():
    st.markdown("")
    st.markdown("")
    st.markdown("")

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

    clean_export = editable_df.copy()
    diagnostic_cols = [
        "Match_Score", "Matched_Rule", "Auto_Approved", "Description_Clean"
    ] + [col for col in clean_export.columns if col.startswith("Suggestion_")]

    if not include_diagnostics:
        clean_export = clean_export.drop(columns=diagnostic_cols, errors="ignore")

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