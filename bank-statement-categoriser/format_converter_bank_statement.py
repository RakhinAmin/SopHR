import pandas as pd

# Load the Excel file
df = pd.read_excel(
    r"C:\Users\Sopher.Intern\Downloads\Book1.xlsx",
    sheet_name="Sheet1"
)

# Clean headers
df.columns = df.columns.str.strip()

# Convert 'Amount £' to numeric
df["Amount £"] = pd.to_numeric(df["Amount £"], errors="coerce")

# Money In / Out
df["Money In"] = df["Amount £"].apply(lambda x: x if x > 0 else 0)
df["Money Out"] = df["Amount £"].apply(lambda x: abs(x) if x < 0 else 0)

# Category columns — assume they start from column 4 onward (index 4)
category_cols = df.columns[4:]  # Adjust index if needed

# Get category as the name of the column with non-null value
df["Category"] = df[category_cols].notna().idxmax(axis=1)

# Final format
final_df = df[["Date", "Money In", "Money Out", "Description", "Category"]]

# Save
output_path = r"C:\Users\Sopher.Intern\Downloads\cleaned_output.xlsx"
final_df.to_excel(output_path, index=False)
print(f"✅ Saved to: {output_path}")
