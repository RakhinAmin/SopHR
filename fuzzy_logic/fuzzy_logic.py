import pandas as pd
from rapidfuzz import process, fuzz
import sys

# CONFIGURATION
BANK_STATEMENT_FILE = r"C:\Users\Sopher.Intern\Downloads\bank_statement.csv"
RULES_FILE = r"C:\Users\Sopher.Intern\Downloads\rules.csv"
OUTPUT_FILE = "categorised_output.csv"
MATCH_THRESHOLD = 90
NUM_SUGGESTIONS = 3

# Error handling for file loading and validation
try:
    bank_df = pd.read_csv(BANK_STATEMENT_FILE)
    if "Description" not in bank_df.columns:
        raise ValueError("Missing 'Description' column in bank_statement.csv")
except FileNotFoundError:
    print(f"Error: File '{BANK_STATEMENT_FILE}' not found")
    sys.exit(1)
except Exception as e:
    print(f"Error loading {BANK_STATEMENT_FILE}: {e}")
    sys.exit(1)

try:
    rules_df = pd.read_csv(RULES_FILE)
    if "Description" not in rules_df.columns or "Category" not in rules_df.columns:
        raise ValueError("Missing 'Description' or 'Category' column in rules.csv")
    if rules_df.empty:
        raise ValueError("rules.csv is empty")
    if rules_df["Description"].duplicated().any():
        print("Warning: Duplicate descriptions found in rules.csv; using first occurrence")
except FileNotFoundError:
    print(f"Error: File '{RULES_FILE}' not found")
    sys.exit(1)
except Exception as e:
    print(f"Error loading {RULES_FILE}: {e}")
    sys.exit(1)

# Preprocess rules for performance
rules_df["Description"] = rules_df["Description"].str.lower().str.strip()
rule_map = rules_df.set_index("Description")["Category"].to_dict()
rule_keys = list(rule_map.keys())

def get_best_match(desc, rules, threshold):
    """Find best category match for a description."""
    if not isinstance(desc, str):
        return None
    desc = desc.lower().strip()
    # Pre-filter: check for exact match to skip fuzzy matching
    if desc in rule_map:
        return rule_map[desc]
    best, score, _ = process.extractOne(desc, rules, scorer=fuzz.partial_ratio)
    return rule_map[best] if score >= threshold else None

def get_top_suggestions(desc, rules, num=3):
    """Get top category suggestions for unmatched descriptions."""
    if not isinstance(desc, str):
        return ["No Match"] * num
    desc = desc.lower().strip()
    # Pre-filter: check for exact match
    if desc in rule_map:
        return [rule_map[desc]] + ["No Match"] * (num - 1)
    matches = process.extract(desc, rules, scorer=fuzz.partial_ratio, score_cutoff=50, limit=num)
    suggestions = [rule_map[m[0]] if m[1] >= 50 else "No Match" for m in matches]
    # Pad if fewer than num suggestions
    return suggestions + ["No Match"] * (num - len(suggestions))

# Apply fuzzy logic with error handling
categories = []
suggestion_1 = []
suggestion_2 = []
suggestion_3 = []

try:
    for desc in bank_df["Description"]:
        best_match = get_best_match(desc, rule_keys, MATCH_THRESHOLD)
        if best_match:
            categories.append(best_match)
            suggestion_1.append("")
            suggestion_2.append("")
            suggestion_3.append("")
        else:
            suggestions = get_top_suggestions(desc, rule_keys, NUM_SUGGESTIONS)
            categories.append("Uncategorised")
            suggestion_1.append(suggestions[0])
            suggestion_2.append(suggestions[1])
            suggestion_3.append(suggestions[2])
except Exception as e:
    print(f"Error during categorization: {e}")
    sys.exit(1)

# Attach results to DataFrame
try:
    bank_df["Category"] = categories
    bank_df["Suggestion_1"] = suggestion_1
    bank_df["Suggestion_2"] = suggestion_2
    bank_df["Suggestion_3"] = suggestion_3
except Exception as e:
    print(f"Error attaching results to DataFrame: {e}")
    sys.exit(1)

# Save output
try:
    bank_df.to_csv(OUTPUT_FILE, index=False)
    uncat_count = sum(1 for cat in categories if cat == "Uncategorised")
    print(f"✅ Categorised transactions saved to {OUTPUT_FILE}")
    print(f"Summary: {len(categories) - uncat_count} categorized, {uncat_count} uncategorised")
except Exception as e:
    print(f"Error saving to {OUTPUT_FILE}: {e}")
    sys.exit(1)