# rule_loader.py
import pandas as pd
from pathlib import Path
from text_cleaner import TextCleaner

class RuleLoader:
    def __init__(self, logger):
        self.logger = logger

    def load_rules(self, rules_file: str):
        self.logger.info(f"Loading rules from {rules_file}")
        if not Path(rules_file).exists():
            raise FileNotFoundError("Rules file missing")

        rules_df = pd.read_csv(rules_file)
        if rules_df.empty or not all(col in rules_df for col in ["Description", "Category"]):
            raise ValueError("Missing or malformed rule file")

        rules_df = rules_df.dropna(subset=["Description", "Category"])
        rules_df["Description_Clean"] = rules_df["Description"].apply(TextCleaner.enhanced)
        rules_df = rules_df[rules_df["Description_Clean"] != ""]
        rule_map = rules_df.set_index("Description_Clean")["Category"].to_dict()
        return rule_map
