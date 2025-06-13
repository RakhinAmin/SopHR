import pandas as pd

def extract_values_column(df: pd.DataFrame) -> pd.DataFrame:
    credit_keywords = ["money in", "credit", "credits"]
    debit_keywords = ["money out", "debit", "debits"]
    direction_col_candidates = ["debit/credit", "type"]
    amount_col_candidates = ["amount", "amt", "value"]

    df["Values"] = 0.0  # default

    # Lowercase map of all columns
    cols_lower = {col.strip().lower(): col for col in df.columns}

    # Case 1: Debit and Credit columns are separate
    found_credit = next((cols_lower[c] for c in credit_keywords if c in cols_lower), None)
    found_debit = next((cols_lower[d] for d in debit_keywords if d in cols_lower), None)

    if found_credit:
        df[found_credit] = pd.to_numeric(df[found_credit], errors='coerce').fillna(0)
        df["Values"] += df[found_credit]

    if found_debit:
        df[found_debit] = pd.to_numeric(df[found_debit], errors='coerce').fillna(0)
        df["Values"] -= df[found_debit]

    # Case 2: One Amount column + direction indicator (e.g., Debit/Credit)
    elif not (found_credit or found_debit):
        # Try to find 'Amount' and 'Debit/Credit' style columns
        amount_col = next((cols_lower[c] for c in amount_col_candidates if c in cols_lower), None)
        direction_col = next((cols_lower[c] for c in direction_col_candidates if c in cols_lower), None)

        if amount_col and direction_col:
            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)

            def compute_signed_value(row):
                if isinstance(row[direction_col], str):
                    if row[direction_col].strip().lower() == "credit":
                        return abs(row[amount_col])
                    elif row[direction_col].strip().lower() == "debit":
                        return -abs(row[amount_col])
                return 0.0

            df["Values"] = df.apply(compute_signed_value, axis=1)

    return df
