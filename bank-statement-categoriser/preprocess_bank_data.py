import pandas as pd  # Pandas for data manipulation

def extract_values_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Infers and computes a unified 'Values' column representing transaction amounts,
    positive for credits and negative for debits, from various bank statement formats.
    """

    # Common keywords for identifying credit and debit columns
    credit_keywords = ["money in", "credit", "credits"]
    debit_keywords = ["money out", "debit", "debits"]

    # Columns that might indicate direction (e.g., 'Debit' or 'Credit' labels)
    direction_col_candidates = ["debit/credit", "type"]

    # Common names for amount columns
    amount_col_candidates = ["amount", "amt", "value"]

    df["Values"] = 0.0  # Initialise new column with default value

    # Create lowercase-to-original column name mapping (stripped) for flexible lookup
    cols_lower = {col.strip().lower(): col for col in df.columns}

    # Attempt to find separate credit and debit columns
    found_credit = next((cols_lower[c] for c in credit_keywords if c in cols_lower), None)
    found_debit = next((cols_lower[d] for d in debit_keywords if d in cols_lower), None)

    # If credit column is found, convert to numeric and add to 'Values'
    if found_credit:
        df[found_credit] = pd.to_numeric(df[found_credit], errors='coerce').fillna(0)
        df["Values"] += df[found_credit]

    # If debit column is found, convert to numeric and subtract from 'Values'
    if found_debit:
        df[found_debit] = pd.to_numeric(df[found_debit], errors='coerce').fillna(0)
        df["Values"] -= df[found_debit]

    # If no credit/debit columns found, fallback to direction + amount method
    elif not (found_credit or found_debit):
        amount_col = next((cols_lower[c] for c in amount_col_candidates if c in cols_lower), None)
        direction_col = next((cols_lower[c] for c in direction_col_candidates if c in cols_lower), None)

        if amount_col and direction_col:
            df[amount_col] = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)

            # Define row-wise logic to assign sign based on direction
            def compute_signed_value(row):
                if isinstance(row[direction_col], str):
                    if row[direction_col].strip().lower() == "credit":
                        return abs(row[amount_col])  # Credit = positive
                    elif row[direction_col].strip().lower() == "debit":
                        return -abs(row[amount_col])  # Debit = negative
                return 0.0  # Fallback if direction is invalid or missing

            # Apply the above logic row-wise
            df["Values"] = df.apply(compute_signed_value, axis=1)

    return df  # Return DataFrame with new 'Values' column
