# === IMPORTS ===
import sqlite3
import os, tempfile, pandas as pd  # Standard libraries for file handling and data processing
from fuzzy_logic_improved import TransactionCategorizer, Config  # Custom logic for transaction categorisation
from preprocess_bank_data import extract_values_column  # Preprocessing utility for extracting transaction descriptions
from .utils import read_uploaded_file  # Helper to read uploaded Excel or CSV files
from collections import namedtuple
import datetime
from logic.paths import DATA_DIR

def ensure_analytics_table(db_path: str = "analytics.db"):
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_stats (
            id                          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id                  TEXT,
            employee_name               TEXT,
            run_at                      TEXT,
            rule_set                    TEXT,
            custom_rules                INTEGER,
            use_tax_rules               INTEGER,
            total_transactions          INTEGER,
            categorised_transactions    INTEGER,
            uncategorised_transactions  INTEGER,
            auto_approved_count         INTEGER,
            avg_confidence              REAL
        )
        """)

CategorisationResult = namedtuple("CategorisationResult", ["success", "output_df", "custom_filename", "original_df", "report"])

def run_categorisation(employee_name: str, bank_file, sheet_to_process, rules_path, client_name, cch_code, raw_date, user_temp_dir, session_id, built_in_db_path=None, use_tax_rules: bool = False, refund_edge_cases_path: str = "refund_edge_cases.csv"):
    ensure_analytics_table("analytics.db")
    
    # Load the uploaded bank file and extract the relevant sheet
    original_df = read_uploaded_file(bank_file, sheet_name=sheet_to_process)

    # Preprocess the data to extract key values (e.g., transaction descriptions)
    preprocessed_df = extract_values_column(original_df.copy())

    if "Description" not in preprocessed_df.columns:
        print("[ERROR] Missing 'Description' column in processed data.")
        return CategorisationResult(False, pd.DataFrame(), custom_filename, original_df)

    # Write the preprocessed dataframe to a temporary CSV file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", dir=user_temp_dir) as tmp_bank:
        preprocessed_df.to_csv(tmp_bank.name, index=False)
        tmp_bank_path = tmp_bank.name  # Store the path to the temp CSV

    # Sanitize and format input data to build a safe and consistent output filename
    safe_client = "".join(c for c in client_name if c.isalnum() or c in ("_", "-")).strip().replace(" ", "_")
    safe_cch = "".join(c for c in cch_code if c.isalnum()).strip().upper()
    final_date = f"YE{raw_date}"  # Add 'YE' prefix to the date
    custom_filename = f"{safe_client}_{safe_cch}_{final_date}_{session_id}.csv"  # Construct the final filename
    output_path = os.path.join(user_temp_dir, custom_filename)  # Full path for the output file

    # Create configuration for the categorisation process
    config = Config(
        bank_statement_file      = tmp_bank_path,
        rules_file               = rules_path,
        output_file              = output_path,
        use_tax_rules          = use_tax_rules,
        refund_edge_cases_file = refund_edge_cases_path or str(DATA_DIR / "refund_edge_cases.csv"),
        directional_file       = str(DATA_DIR / "directional_merchants.csv"),
    )

    # Instantiate the categoriser with the config and run the categorisation process
    categorizer = TransactionCategorizer(config)
    db_conn = None
    if not rules_path and built_in_db_path:
        db_conn = sqlite3.connect(built_in_db_path)
    success = categorizer.run_categorization(db_conn=db_conn)
    if db_conn:
        db_conn.close()


    # Return status, output file path, filename, and original (unprocessed) dataframe
    output_df = pd.read_csv(output_path)

    report = categorizer.generate_report(output_df)

# Inside your run_categorisation function, after you've computed `report`:
    # Determine which ruleset was used
    rule_set = (
        "custom"
        if rules_path
        else ("tax" if use_tax_rules else "accounting")
    )

    # Ensure analytics table exists
    ensure_analytics_table("analytics.db")

    # Insert the usage stats with proper Python-native types
    with sqlite3.connect("analytics.db") as conn:
        conn.execute("""
            INSERT INTO usage_stats (
                session_id, employee_name, run_at, rule_set, custom_rules,
                use_tax_rules, total_transactions,
                categorised_transactions, uncategorised_transactions,
                auto_approved_count, avg_confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            employee_name,                       # ← new
            datetime.datetime.utcnow().isoformat(),
            rule_set,
            int(bool(rules_path)),
            int(use_tax_rules),
            int(report["total_transactions"]),
            int(report["categorised"]),
            int(report["uncategorised"]),
            int(report["auto_approved"]),
            float(report["avg_confidence"])
        ))

    return CategorisationResult(success, output_df, custom_filename, original_df, report)
