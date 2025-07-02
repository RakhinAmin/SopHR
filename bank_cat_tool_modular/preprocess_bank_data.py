import pandas as pd  # Pandas for data manipulation

def extract_values_column(df: pd.DataFrame) -> pd.DataFrame:
    """
    Infers and computes a unified 'Values' column representing transaction amounts,
    positive for credits and negative for debits, from various bank statement formats.
    """
    credit_kws = ["money in", "credit", "credits"]
    debit_kws  = ["money out", "debit", "debits"]
    direction_cols = ["debit/credit", "type"]
    amount_cols    = ["amount", "amt", "value"]

    df = df.copy()
    df["Values"] = 0.0

    # find the first column whose name contains any of our keywords
    found_credit = next(
        (col for col in df.columns
         if any(kw in col.strip().lower() for kw in credit_kws)),
        None
    )
    found_debit = next(
        (col for col in df.columns
         if any(kw in col.strip().lower() for kw in debit_kws)),
        None
    )

    if found_credit or found_debit:
        # convert to numeric once
        if found_credit:
            df[found_credit] = pd.to_numeric(df[found_credit], errors="coerce").fillna(0)
            df["Values"] += df[found_credit]

        if found_debit:
            df[found_debit]  = pd.to_numeric(df[found_debit], errors="coerce").fillna(0)
            df["Values"] -= df[found_debit]

    else:
        # fallback to direction + amount columns
        amt_col = next(
            (col for col in df.columns
             if col.strip().lower() in amount_cols),
            None
        )
        dir_col = next(
            (col for col in df.columns
             if col.strip().lower() in direction_cols),
            None
        )

        if amt_col and dir_col:
            df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce").fillna(0)

            def signed(row):
                d = str(row[dir_col]).strip().lower()
                a = row[amt_col]
                if d == "credit":
                    return abs(a)
                if d == "debit":
                    return -abs(a)
                return 0.0

            df["Values"] = df.apply(signed, axis=1)

    return df