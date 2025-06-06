import pandas as pd
import os

# === FILE CONFIGURATION ===
CATEGORISED_FILE = r"C:\Users\Sopher.Intern\Downloads\categorised_output.csv"  # file where user made corrections
RULES_FILE = r"C:\Users\Sopher.Intern\Downloads\rules.csv"                     # existing rulebook
BACKUP_FILE = r"C:\Users\Sopher.Intern\Downloads\rules_backup.csv"             # optional backup before overwriting

# === LOAD FILES ===
try:
    categorised_df = pd.read_csv(CATEGORISED_FILE)
    rules_df = pd.read_csv(RULES_FILE)
except FileNotFoundError as e:
    print(f"❌ File not found: {e.filename}")
    exit(1)

# === CLEAN AND COMPARE ===
categorised_df = categorised_df.dropna(subset=["Description", "Category"])
rules_df = rules_df.dropna(subset=["Description", "Category"])

# Ensure consistent casing and strip
categorised_df["Description"] = categorised_df["Description"].str.strip()
rules_df["Description"] = rules_df["Description"].str.strip()

# Filter new user-labeled rows
new_entries = categorised_df[
    (categorised_df["Category"] != "Uncategorised") &
    (~categorised_df["Description"].isin(rules_df["Description"]))
][["Description", "Category"]].drop_duplicates()

if new_entries.empty:
    print("ℹ️ No new user corrections found to learn from.")
    exit(0)

# === BACKUP OLD RULEBOOK ===
if os.path.exists(RULES_FILE):
    rules_df.to_csv(BACKUP_FILE, index=False)
    print(f"🔐 Backup of existing rules saved to {BACKUP_FILE}")

# === MERGE & SAVE UPDATED RULEBOOK ===
updated_rules = pd.concat([rules_df, new_entries], ignore_index=True).drop_duplicates()
updated_rules.to_csv(RULES_FILE, index=False)
print(f"✅ Learned and added {len(new_entries)} new rules to {RULES_FILE}")
