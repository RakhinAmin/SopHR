# transaction_categorizer.py
import time
import pandas as pd

class TransactionCategorizer:
    def __init__(self, config, logger, rule_loader, bank_loader, matcher):
        self.config = config
        self.logger = logger
        self.rule_loader = rule_loader
        self.bank_loader = bank_loader
        self.matcher = matcher

    def categorize(self, bank_df):
        suggestions_cols = [[] for _ in range(self.config.num_suggestions)]
        categories, scores, matches, approvals = [], [], [], []

        for _, row in bank_df.iterrows():
            desc = row["Description"]
            category, score, matched = self.matcher.match(desc)
            categories.append(category)
            scores.append(score)
            matches.append(matched)
            approvals.append(score >= self.config.auto_approve_threshold and category != "Uncategorised")

            if category == "Uncategorised":
                suggestions, confs = self.matcher.suggest(desc, self.config.num_suggestions)
                for i in range(self.config.num_suggestions):
                    suggestions_cols[i].append(f"{suggestions[i]} ({confs[i]}%)")
            else:
                for i in range(self.config.num_suggestions):
                    suggestions_cols[i].append("")

        bank_df["Category"] = categories
        bank_df["Match_Score"] = scores
        bank_df["Matched_Rule"] = matches
        bank_df["Auto_Approved"] = approvals
        for i, col in enumerate(suggestions_cols):
            bank_df[f"Suggestion_{i+1}"] = col
        return bank_df
