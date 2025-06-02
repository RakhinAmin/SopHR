import os
import pdfplumber
import pytesseract
from PIL import Image
import openpyxl

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

        elif ext in ['.xlsx', '.xls', '.csv']:
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
