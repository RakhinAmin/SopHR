import os
import pandas as pd
from fuzzy_logic_improved import enhanced_clean_description
from pathlib import Path

# === Configuration ===
RULES_PATH = "rules.csv"
CORRECTIONS_DIR = "."
CORRECTION_PREFIX = "manual_corrections_"

# === Load existing rules ===
print(f"Loading main rules from: {RULES_PATH}")
rules_df = pd.read_csv(RULES_PATH)
rules_df["Description_Clean"] = rules_df["Description"].apply(enhanced_clean_description)

existing_rules = dict(zip(rules_df["Description_Clean"], rules_df["Category"]))

# === Collect all corrections ===
correction_files = [f for f in os.listdir(CORRECTIONS_DIR) if f.startswith(CORRECTION_PREFIX) and f.endswith(".csv")]

if not correction_files:
    print("No correction files found.")
    exit(0)

print(f"Found {len(correction_files)} correction files.")
all_new_rules = {}

for file in correction_files:
    path = os.path.join(CORRECTIONS_DIR, file)
    print(f"Processing {file}")
    
    try:
        df = pd.read_csv(path)
        df = df.dropna(subset=["Description", "Category"])
        df["Description_Clean"] = df["Description"].apply(enhanced_clean_description)

        for _, row in df.iterrows():
            clean_desc = row["Description_Clean"]
            category = row["Category"]

            if clean_desc not in existing_rules and clean_desc not in all_new_rules:
                all_new_rules[clean_desc] = (row["Description"], category)
            elif clean_desc in existing_rules and existing_rules[clean_desc] != category:
                print(f"[CONFLICT] '{row['Description']}' → '{category}' (already mapped to '{existing_rules[clean_desc]}')")
    except Exception as e:
        print(f"[ERROR] Could not process {file}: {e}")

# === Append new rules ===
if all_new_rules:
    print(f"\n✅ {len(all_new_rules)} new rules will be added to '{RULES_PATH}':")
    for _, (desc, cat) in all_new_rules.items():
        print(f"  - {desc} → {cat}")

    confirm = input("\nAppend these rules to rules.csv? [y/N]: ").strip().lower()
    if confirm == "y":
        new_df = pd.DataFrame.from_records(
            [(desc, cat) for desc, cat in all_new_rules.values()],
            columns=["Description", "Category"]
        )
        new_df.to_csv(RULES_PATH, mode="a", index=False, header=False)
        print("✅ Rules successfully appended.")
    else:
        print("❌ Merge aborted by user.")
else:
    print("No new unique rules to add.")

