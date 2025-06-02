import pdfplumber
import pandas as pd
import re

def is_date(s):
    return re.match(r"\d{2}/\d{2}/\d{4}", s.strip()) is not None

def try_parse_amount(s):
    try:
        return float(s.replace(",", "").replace("£", "").replace("$", ""))
    except:
        return None

def extract_from_bank_pdf(pdf_path):
    data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            lines = page.extract_text().split('\n')
            for line in lines:
                parts = re.split(r'\s{2,}', line.strip())
                
                # Only consider lines that look like they start with a date
                if parts and is_date(parts[0]):
                    # Try basic patterns like: Date | Description | Amount | Balance
                    if len(parts) >= 3:
                        date = parts[0]
                        description = parts[1]
                        amount = try_parse_amount(parts[2])
                        balance = try_parse_amount(parts[3]) if len(parts) > 3 else None

                        data.append({
                            'Date': date,
                            'Description': description,
                            'Amount': amount,
                            'Balance': balance
                        })

    df = pd.DataFrame(data)
    return df

# Usage
if __name__ == "__main__":
    pdf_file = "bank_statement.pdf"  # Replace with your file
    df = extract_from_bank_pdf(pdf_file)
    df.to_excel("bank_statement_output.xlsx", index=False)
    print("Output saved to bank_statement_output.xlsx")
