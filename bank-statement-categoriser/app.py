from io import BytesIO
import streamlit as st
import pandas as pd
from fuzzy_logic_improved import TransactionCategorizer, Config
from preprocess_bank_data import extract_values_column
import tempfile
import os
import time
import glob
import uuid

# --- Unique session ID and folder ---
SESSION_ID = str(uuid.uuid4())[:8]
USER_TEMP_DIR = os.path.join(tempfile.gettempdir(), f"session_{SESSION_ID}")
os.makedirs(USER_TEMP_DIR, exist_ok=True)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Categorised')
    return output.getvalue()

def read_uploaded_file(file, sheet_name=None):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith((".xlsx", ".xls")):
        # if sheet_name is None, default to first sheet explicitly
        return pd.read_excel(file, sheet_name=sheet_name or 0)
    else:
        raise ValueError("Unsupported file format")

st.set_page_config(page_title="Transaction Categoriser", layout="wide")
st.title("Bank Transaction Categorisation Tool")

# --- Clean up old temporary files ---
now = time.time()
tmp_dir = tempfile.gettempdir()
for f in os.listdir(tmp_dir):
    fpath = os.path.join(tmp_dir, f)
    if os.path.isfile(fpath) and os.path.getmtime(fpath) < now - 3600:
        try:
            os.remove(fpath)
        except:
            pass

# --- Rule Set Selection ---
st.markdown("### Choose Rule Set")
col1, col2 = st.columns([2, 3])

with col1:
    st.markdown("#### Built-in Rule Sets")
    available_rule_sets = sorted(
        f for f in glob.glob("rules_*.csv") if "template" not in f.lower()
    )
    selected_rule_set = st.selectbox(
        "Select a built-in rules file:",
        options=available_rule_sets,
        format_func=lambda x: x.replace("rules_", "").replace(".csv", "").replace("_", " ").title()
    )

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

# --- Output File Naming ---
st.markdown("### Output File Naming")
client_name = st.text_input("Client Name (max 100 characters):", max_chars=100)
cch_code = st.text_input("CCH Client Code (3–10 characters):", max_chars=10)
raw_date = st.text_input("Year End Date (DDMMYYYY)", max_chars=8, help="e.g. 31122024")
ye_date = f"YE{raw_date[4:] + raw_date[2:4] + raw_date[0:2]}" if raw_date and raw_date.isdigit() and len(raw_date) == 8 else ""

# --- Bank Transaction Upload ---
st.markdown("### Upload Bank Transactions File")
bank_file = st.file_uploader(
    "Upload your bank statement file (CSV or Excel):",
    type=["csv", "xlsx", "xls"],
    key="bank"
)

sheet_to_process = None
if bank_file is not None and bank_file.name.endswith((".xlsx", ".xls")):
    try:
        bank_file.seek(0)  # Ensure pointer is at the beginning
        excel_obj = pd.ExcelFile(bank_file)
        sheet_names = excel_obj.sheet_names

        if len(sheet_names) > 1:
            sheet_to_process = st.selectbox(
                "This Excel file contains multiple sheets. Select the sheet to process:",
                sheet_names
            )
        else:
            sheet_to_process = sheet_names[0]
        
        bank_file.seek(0)  # Reset again for later actual reading
    except Exception as e:
        st.error(f"Failed to read Excel file: {e}")
        st.stop()

# --- Categorisation ---
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
    else:
        tmp_rules_path = selected_rule_set
        st.info(f"Using built-in rule set: {selected_rule_set}")

    safe_client = "".join(c for c in client_name if c.isalnum() or c in ("_", "-")).strip().replace(" ", "_")
    safe_cch = "".join(c for c in cch_code if c.isalnum()).strip().upper()
    final_date = f"YE{raw_date}"
    custom_filename = f"{safe_client}_{safe_cch}_{final_date}_{SESSION_ID}.csv"
    correction_filename = f"{safe_client}_{safe_cch}_{final_date}_{SESSION_ID}_corrections.csv"
    output_path = os.path.join(USER_TEMP_DIR, custom_filename)

    config = Config(
        bank_statement_file=tmp_bank_path,
        rules_file=tmp_rules_path,
        output_file=output_path
    )

    categorizer = TransactionCategorizer(config)

    with st.spinner("Processing transactions..."):
        if categorizer.run_categorization():
            output_df = pd.read_csv(output_path)
            st.success("Categorisation completed successfully!")

            st.subheader("Categorised Transactions")
            st.dataframe(output_df)

            st.session_state["editable_df"] = output_df
            st.session_state["custom_filename"] = custom_filename
            st.session_state["bank_file"] = bank_file
        else:
            st.error("Something went wrong during categorisation. Check logs.")

# --- Post-run download block ---
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
