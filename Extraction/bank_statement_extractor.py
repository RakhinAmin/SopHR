import pdfplumber
import pandas as pd
import re

def extract_transactions(pdf_path):
    transactions = []
    date_pattern = re.compile(r"^\d{2} \w{3} \d{2}")
    txn_pattern = re.compile(r"^(\d{2} \w{3} \d{2})\s+(.+?)\s+£([\d,]+\.\d{2})\s+£([\d,]+\.\d{2})$")

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().split("\n")
            current_txn = None

            for i, line in enumerate(lines):
                line = line.strip()
                # Match full transaction line
                match = txn_pattern.match(line)
                if match:
                    date, description, amount, balance = match.groups()
                    transactions.append({
                        "Date": date,
                        "Description": description,
                        "Amount": float(amount.replace(",", "")),
                        "Balance": float(balance.replace(",", ""))
                    })
                else:
                    # Try to match partial line, and keep appending to last transaction
                    if current_txn and not date_pattern.match(line):
                        transactions[-1]["Description"] += " " + line.strip()

    return pd.DataFrame(transactions)


# === Run It ===
if __name__ == "__main__":
    pdf_file = r"C:\Users\Sopher.Intern\Documents\SopHR\Extraction\VM Statement - Dec 24.pdf"  # Replace with your actual file name
    df = extract_transactions(pdf_file)
    df.to_excel("bank_statement_output.xlsx", index=False)
    print("Saved as 'bank_statement_output.xlsx'")
