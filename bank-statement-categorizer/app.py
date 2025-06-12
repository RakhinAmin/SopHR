import streamlit as st
import pandas as pd
from fuzzy_logic_improved import TransactionCategorizer, Config
from preprocess_bank_data import extract_values_column
import tempfile
import os
import uuid
import time
import glob

st.set_page_config(page_title="Transaction Categoriser", layout="wide")
st.title("📅 Bank Transaction Categorisation Tool")

# --- Clean up old temporary files ---
now = time.time()
tmp_dir = tempfile.gettempdir()
for f in os.listdir(tmp_dir):
    if f.endswith(".csv") and os.path.getmtime(os.path.join(tmp_dir, f)) < now - 3600:
        try:
            os.remove(os.path.join(tmp_dir, f))
        except:
            pass

# --- Rule Set Selection ---
st.markdown("### 🧩 Choose Rule Set")

col1, col2 = st.columns([2, 3])

with col1:
    st.markdown("#### 📁 Built-in Rule Sets")
    available_rule_sets = sorted(
    f for f in glob.glob("rules_*.csv") if "template" not in f.lower()
    )
    selected_rule_set = st.selectbox(
        "Select a built-in rules file:",
        options=available_rule_sets,
        format_func=lambda x: x.replace("rules_", "").replace(".csv", "").replace("_", " ").title()
    )

with col2:
    st.markdown("#### 📝 Or Drag and Drop a Custom Rules File")

    # Add Template Download Button
    with open("rules_template.csv", "r") as template_file:
        st.download_button(
            label="📄 Download Rules Template CSV",
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
st.markdown("### 📝 Output File Naming")

client_name = st.text_input("Client Name (max 100 characters):", max_chars=100)
cch_code = st.text_input("CCH Client Code (3–10 characters):", max_chars=10)
raw_date = st.text_input("Year End Date (DDMMYYYY)", max_chars=8, help="e.g. 31122024")
ye_date = f"YE{raw_date[4:] + raw_date[2:4] + raw_date[0:2]}" if raw_date and raw_date.isdigit() and len(raw_date) == 8 else ""

# --- Bank Transaction Upload ---
st.markdown("### 🏦 Upload Bank Transactions File")
bank_file = st.file_uploader(
    "Upload your bank statement CSV (drag and drop or browse):",
    type=["csv"],
    key="bank"
)

# --- Categorisation ---
if st.button("Run Categorisation"):
    # --- Input Validation ---
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

    original_df = pd.read_csv(bank_file)
    original_df = extract_values_column(original_df)  # Apply preprocessing logic
    original_cols = list(original_df.columns)


    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_bank:
        original_df.to_csv(tmp_bank.name, index=False)
        tmp_bank_path = tmp_bank.name


    # Handle rules file: uploaded custom overrides selected
    if uploaded_rules_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_rules:
            tmp_rules.write(uploaded_rules_file.getvalue())
            tmp_rules_path = tmp_rules.name
        st.success("✅ Using uploaded custom rules file.")
    else:
        tmp_rules_path = selected_rule_set
        st.info(f"📘 Using built-in rule set: {selected_rule_set}")

    # --- Output File Construction ---
    safe_client = "".join(c for c in client_name if c.isalnum() or c in ("_", "-")).strip().replace(" ", "_")
    safe_cch = "".join(c for c in cch_code if c.isalnum()).strip().upper()
    final_date = f"YE{raw_date}"
    custom_filename = f"{safe_client}_{safe_cch}_{final_date}.csv"
    correction_filename = f"{safe_client}_{safe_cch}_{final_date}_corrections.csv"
    output_path = os.path.join(tempfile.gettempdir(), custom_filename)

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

            st.subheader("Review and Override Categories")

            editable_df = st.data_editor(
                output_df,
                num_rows="dynamic",
                use_container_width=True,
                key="editor",
                column_config={
                    "Category": st.column_config.TextColumn("Category (Editable)")
                }
            )

            overridden_rows = editable_df[editable_df["Category"] != output_df["Category"]]

            if not overridden_rows.empty:
                st.success(f"{len(overridden_rows)} transaction(s) manually overridden.")
                st.dataframe(overridden_rows)

                correction_path = os.path.join(tempfile.gettempdir(), correction_filename)
                overridden_rows.to_csv(correction_path, index=False)

                st.download_button(
                    label="Download Manual Corrections Only",
                    data=overridden_rows.to_csv(index=False).encode("utf-8"),
                    file_name=correction_filename,
                    mime="text/csv"
                )
            else:
                st.info("No manual overrides were made.")

            # --- Diagnostic Option ---
            st.markdown("### 📤 Download Options")
            include_diagnostics = st.checkbox("Include diagnostic columns in download", value=False)

            clean_cols = [col for col in original_cols if col in editable_df.columns] + ["Category"]
            clean_df = editable_df[clean_cols]

            if include_diagnostics:
                st.download_button(
                    label="Download Full Categorised CSV (with diagnostics)",
                    data=editable_df.to_csv(index=False).encode("utf-8"),
                    file_name=custom_filename,
                    mime="text/csv"
                )
            else:
                st.download_button(
                    label="Download Clean Categorised CSV (original + Category only)",
                    data=clean_df.to_csv(index=False).encode("utf-8"),
                    file_name=custom_filename.replace(".csv", "_clean.csv"),
                    mime="text/csv"
                )
        else:
            st.error("Something went wrong during categorisation. Check logs.")
