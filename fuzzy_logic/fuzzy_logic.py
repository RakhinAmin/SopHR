import pandas as pd
from rapidfuzz import process, fuzz
import re
import sys

# === HYBRID SCORER ===
def hybrid_score(a, b, **kwargs):
    """Weighted combo of token_set_ratio (structure) and partial_ratio (substring)"""
    return 0.6 * fuzz.token_set_ratio(a, b) + 0.4 * fuzz.partial_ratio(a, b)

# CONFIGURATION
BANK_STATEMENT_FILE = r"C:\Users\Sopher.Intern\Downloads\bank_statement_test.csv"
RULES_FILE = r"C:\Users\Sopher.Intern\Downloads\rules_large.csv"
OUTPUT_FILE = "categorised_output.csv"
MATCH_THRESHOLD = 90
NUM_SUGGESTIONS = 3

# === CLEANING FUNCTION ===
def clean_description(text):
    """Lowercase, remove special characters, normalize spaces."""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# === LOAD & VALIDATE FILES ===
try:
    bank_df = pd.read_csv(BANK_STATEMENT_FILE)
    if "Description" not in bank_df.columns:
        raise ValueError("Missing 'Description' column in bank statement file")
except Exception as e:
    print(f"Error loading bank statement: {e}")
    sys.exit(1)

try:
    rules_df = pd.read_csv(RULES_FILE)
    if "Description" not in rules_df.columns or "Category" not in rules_df.columns:
        raise ValueError("Missing 'Description' or 'Category' in rules file")
    if rules_df.empty:
        raise ValueError("rules.csv is empty")
except Exception as e:
    print(f"Error loading rules file: {e}")
    sys.exit(1)

# === PREPROCESS RULE SET ===
rules_df["Description"] = rules_df["Description"].apply(clean_description)
rule_map = rules_df.set_index("Description")["Category"].to_dict()
rule_keys = list(rule_map.keys())

# === MATCHING FUNCTIONS ===
def get_best_match(desc, rules, threshold):
    desc = clean_description(desc)
    if desc in rule_map:
        return rule_map[desc], 100.0, desc
    best, score, _ = process.extractOne(desc, rules, scorer=hybrid_score)
    return (rule_map[best], score, best) if score >= threshold else ("Uncategorised", score, best)

def get_top_suggestions(desc, rules, rule_map, num=3):
    desc = clean_description(desc)
    matches = process.extract(desc, rules, scorer=hybrid_score, score_cutoff=50, limit=num)
    suggestions = [rule_map[m[0]] for m in matches]
    confidences = [round(m[1], 2) for m in matches]
    while len(suggestions) < num:
        suggestions.append("No Match")
        confidences.append(0.0)
    return suggestions, confidences

# === APPLY CATEGORISATION ===
categories = []
match_scores = []
matched_rules = []
suggestion_1 = []
suggestion_2 = []
suggestion_3 = []

try:
    for desc in bank_df["Description"]:
        category, score, matched_rule = get_best_match(desc, rule_keys, MATCH_THRESHOLD)
        categories.append(category)
        match_scores.append(round(score, 2))
        matched_rules.append(matched_rule)

        if category == "Uncategorised":
            suggestions, confidences = get_top_suggestions(desc, rule_keys, rule_map)
            suggestion_1.append(f"{suggestions[0]} ({confidences[0]}%)")
            suggestion_2.append(f"{suggestions[1]} ({confidences[1]}%)")
            suggestion_3.append(f"{suggestions[2]} ({confidences[2]}%)")
        else:
            suggestion_1.append("")
            suggestion_2.append("")
            suggestion_3.append("")
except Exception as e:
    print(f"Error during categorization: {e}")
    sys.exit(1)

# === BUILD OUTPUT ===
try:
    bank_df["Category"] = categories
    bank_df["Match_Score"] = match_scores
    bank_df["Matched_Rule"] = matched_rules
    bank_df["Suggestion_1"] = suggestion_1
    bank_df["Suggestion_2"] = suggestion_2
    bank_df["Suggestion_3"] = suggestion_3
except Exception as e:
    print(f"Error attaching results to DataFrame: {e}")
    sys.exit(1)

# === SAVE OUTPUT ===
try:
    bank_df.to_csv(OUTPUT_FILE, index=False)
    uncat_count = categories.count("Uncategorised")
    print(f"✅ Categorised transactions saved to {OUTPUT_FILE}")
    print(f"🔎 {uncat_count} uncategorised transactions out of {len(categories)}")
except Exception as e:
    print(f"Error saving to {OUTPUT_FILE}: {e}")
    sys.exit(1)
