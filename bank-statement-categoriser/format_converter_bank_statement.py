import pandas as pd  # Import the pandas library for data manipulation

# Load the Excel file
df = pd.read_excel(
    r"C:\Users\Sopher.Intern\Downloads\payments_2024.xlsx",  # Path to the Excel file
    sheet_name="Sheet1"  # Sheet to read from
)

# Clean headers
df.columns = df.columns.str.strip()  # Remove leading/trailing whitespace from column names

# Convert 'Amount £' to numeric
df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")  # Force conversion; invalid entries become NaN

# Money In / Out
df["Money In"] = df["Amount"].apply(lambda x: x if x > 0 else 0)  # Keep positive amounts as 'Money In'
df["Money Out"] = df["Amount"].apply(lambda x: abs(x) if x < 0 else 0)  # Take absolute of negatives as 'Money Out'

# Category columns — assume they start from column 4 onward (index 4)
category_cols = df.columns[4:]  # Slice to get all possible category columns (adjust if structure changes)

# Get category as the name of the column with non-null value
df["Category"] = df[category_cols].notna().idxmax(axis=1)  # Find first column with a non-null value across category columns

# Final format
final_df = df[["Date", "Money In", "Money Out", "Description", "Category"]]  # Rearrange selected columns in output

# Save
output_path = r"C:\Users\Sopher.Intern\Downloads\cleaned_output.xlsx"  # Path to save cleaned file
final_df.to_excel(output_path, index=False)  # Write to Excel without row index
print(f"✅ Saved to: {output_path}")  # Confirmation message
