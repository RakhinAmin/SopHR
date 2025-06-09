# text_cleaner.py
import re

class TextCleaner:
    @staticmethod
    def enhanced(text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            return ""
        text = text.lower().strip()
        text = re.sub(r'\b(ref|payment|purchase|transaction|debit|credit)\b', '', text)
        text = re.sub(r'\b\d{4,}\b', '', text)
        text = re.sub(r'[^a-z0-9 ]', '', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def basic(text: str) -> str:
        if not isinstance(text, str):
            return ""
        text = text.lower()
        text = re.sub(r"[^a-z0-9 ]", "", text)
        return re.sub(r"\s+", " ", text).strip()
