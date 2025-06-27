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

def import_directional(csv_path: str, db_name: str):
    df = pd.read_csv(csv_path).dropna(subset=["description_clean"])
    with sqlite3.connect(f"{db_name}.db") as conn:
        conn.execute("DROP TABLE IF EXISTS directional_merchants")
        df.to_sql("directional_merchants", conn, index=False)
        print(f"Imported {len(df)} directional entries")

# Usage
if __name__ == "__main__":
    #import_csv_to_db("rules_accounting.csv", "rules_accounting")
    #import_csv_to_db(r"C:\Users\Sopher.Intern\Documents\SopHR\bank_cat_tool_modular\rules_tax.csv", "rules_tax")
    import_directional(r"C:\Users\Sopher.Intern\Documents\SopHR\bank_cat_tool_modular\directional_merchants.csv", "directional")
