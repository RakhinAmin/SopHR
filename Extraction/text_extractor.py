import os
import pdfplumber
import pytesseract
from PIL import Image
import openpyxl

SUPPORTED_EXTENSIONS = ['.txt', '.pdf', '.xlsx', '.png', '.jpg', '.jpeg']

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[-1].lower()

    try:

        if ext == '.pdf':
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() or ""
            return text


        elif ext in ['.png', '.jpg', '.jpeg']:
            image = Image.open(file_path)
            return pytesseract.image_to_string(image)

        elif ext == ['.xlsx', '.xls', '.csv']:
            wb = openpyxl.load_workbook(file_path, data_only=True)
            text = ""
            for sheet in wb.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    text += " ".join([str(cell) if cell else "" for cell in row]) + "\n"
            return text

        else:
            return f"Unsupported file type: {ext}"

    except Exception as e:
        return f"Error processing {file_path}: {str(e)}"

def extract_from_folder(folder_path):
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            path = os.path.join(root, file)
            if os.path.splitext(file)[-1].lower() in SUPPORTED_EXTENSIONS:
                print(f"\n--- {file} ---")
                print(extract_text_from_file(path))

# 🔧 Update this with your test folder path
if __name__ == "__main__":
    test_folder = r"C:\Users\Rakhin.Amin\OneDrive - Sopher + Co LLP\Software Development\BankStatements\SopHR\Extraction"  # Replace with your folder name
    extract_from_folder(test_folder)
