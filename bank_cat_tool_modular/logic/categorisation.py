import os, tempfile, pandas as pd
from fuzzy_logic_improved import TransactionCategorizer, Config
from preprocess_bank_data import extract_values_column
from .utils import read_uploaded_file

def run_categorisation(bank_file, sheet_to_process, rules_path, client_name, cch_code, raw_date, user_temp_dir, session_id):
    original_df = read_uploaded_file(bank_file, sheet_name=sheet_to_process)
    preprocessed_df = extract_values_column(original_df.copy())

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=user_temp_dir) as tmp_bank:
        preprocessed_df.to_csv(tmp_bank.name, index=False)
        tmp_bank_path = tmp_bank.name

    safe_client = "".join(c for c in client_name if c.isalnum() or c in ("_", "-")).strip().replace(" ", "_")
    safe_cch = "".join(c for c in cch_code if c.isalnum()).strip().upper()
    final_date = f"YE{raw_date}"
    custom_filename = f"{safe_client}_{safe_cch}_{final_date}_{session_id}.csv"
    output_path = os.path.join(user_temp_dir, custom_filename)

    config = Config(
        bank_statement_file=tmp_bank_path,
        rules_file=rules_path,
        output_file=output_path
    )
    categorizer = TransactionCategorizer(config)

    success = categorizer.run_categorization()
    return success, output_path, custom_filename, original_df
