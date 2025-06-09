# bank_loader.py
import pandas as pd
from pathlib import Path
from text_cleaner import TextCleaner

class BankStatementLoader:
    def __init__(self, logger):
        self.logger = logger

    def load(self, path: str):
        self.logger.info(f"Loading bank data from {path}")
        if not Path(path).exists():
            raise FileNotFoundError("Bank file missing")
        df = pd.read_csv(path)
        if "Description" not in df.columns:
            raise ValueError("Missing 'Description' column")
        df["Description_Clean"] = df["Description"].apply(TextCleaner.enhanced)
        return df
