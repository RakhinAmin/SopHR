import pandas as pd

# === CONFIGURATION ===
file_path = r"C:\Users\Sopher.Intern\Downloads\cleanup.xlsx"
sheet = "Sheet1"
category_start_index = 7  # Adjust as needed
output_path = r"C:\Users\Sopher.Intern\Downloads\description_category_output.xlsx"

# === DEDUPLICATE FUNCTION ===
def deduplicate_columns(columns):
    seen = {}
    new_columns = []
    for col in columns:
        col_clean = str(col).strip()
        if col_clean in seen:
            seen[col_clean] += 1
            new_columns.append(f"{col_clean}.{seen[col_clean]}")
        else:
            seen[col_clean] = 0
            new_columns.append(col_clean)
    return new_columns

# === LOAD & CLEAN DATA ===
df = pd.read_excel(file_path, sheet_name=sheet)
df.columns = deduplicate_columns(df.columns)

# === GET CATEGORY COLUMNS ===
category_cols = df.columns[category_start_index:]

# === ASSIGN MULTIPLE CATEGORIES IF MULTIPLE NON-NULL VALUES ===
def find_categories(row):
    matched = [col for col in category_cols if pd.notna(row[col])]
    if not matched:
        return ""
    elif len(matched) == 1:
        return matched[0]
    else:
        return " and ".join(matched)  # Use Oxford-style 'X and Y', not CSV

df["Category"] = df.apply(find_categories, axis=1)

# === FINAL OUTPUT ===
result_df = df[["Description", "Category"]].copy()
# Optional: keep rows only with category
# result_df = result_df[result_df["Category"] != ""]

# === SAVE ===
result_df.to_excel(output_path, index=False)
print(f"✅ Multi-category output saved to: {output_path}")
