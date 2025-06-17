import pandas as pd
import sqlite3

def import_csv_to_db(csv_path: str, db_name: str):
    db_path = f"{db_name}.db"
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=["Description", "Category"])
    df = df[["Description", "Category"]]

    with sqlite3.connect(db_path) as conn:
        conn.execute("DROP TABLE IF EXISTS rules")
        df.to_sql("rules", conn, index=False)
        print(f"✅ Imported {len(df)} rules into {db_path} [rules]")

# Usage
if __name__ == "__main__":
    import_csv_to_db("rules_accounting.csv", "rules_accounting")
    #import_csv_to_db("rules_tax.csv", "rules_tax")
