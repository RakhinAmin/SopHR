# === IMPORTS ===
from logging import config
import pandas as pd  # Data manipulation library
from rapidfuzz import process, fuzz  # Fast fuzzy string matching
import re  # Regular expressions for text cleaning
import sys  # Used for exiting with success/failure status
import logging  # Logging infrastructure
from functools import lru_cache  # For memoization of match function
from dataclasses import dataclass  # For clean configuration structure
from logic.paths import DATA_DIR
from typing import Tuple, List, Dict, Optional  # Type annotations
import time  # Measuring execution time
from pathlib import Path  # Path utilities for file existence checking
import sqlite3  # For loading rules from a database

# === CONFIGURATION ===
@dataclass
class Config:
    """Configuration settings for the categorizer"""
    bank_statement_file: str = ""  # Input file path for bank statement
    rules_file: str = ""  # Input file path for rules
    output_file: str = ""  # Output file path
    match_threshold: int = 90  # Minimum score to consider a match valid
    num_suggestions: int = 3  # Number of suggestions to generate
    auto_approve_threshold: int = 95  # Score to auto-approve a match
    chunk_size: int = 1000  # Unused, potentially for batch processing
    cache_size: int = 1000  # Unused, default cache size (for lru_cache)
    directional_file: str = str(DATA_DIR / "directional_merchants.csv")
    use_tax_rules: bool = False        # whether to apply “Refund:” logic
    refund_edge_cases_file: str = str(DATA_DIR / "refund_edge_cases.csv")

# === LOGGING SETUP ===
def setup_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Clear existing handlers to avoid duplicates
    while logger.hasHandlers():
        logger.removeHandler(logger.handlers[0])

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler('categorizer.log', encoding='utf-8')
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# === ENHANCED CLEANING FUNCTIONS ===
def enhanced_clean_description(text: str) -> str:
    """Enhanced cleaning with financial-specific preprocessing"""
    if not isinstance(text, str) or not text.strip():
        return ""
    text = text.lower().strip()
    text = re.sub(r'\b(ref|payment|purchase|transaction|debit|credit)\b', '', text)
    text = re.sub(r'\b\d{4,}\b', '', text)
    text = re.sub(r'[^a-z0-9 ]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def basic_clean_description(text: str) -> str:
    """Basic cleaning function (fallback)"""
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# === HYBRID SCORER ===
def hybrid_score(a: str, b: str, **kwargs) -> float:
    return 0.6 * fuzz.token_set_ratio(a, b) + 0.4 * fuzz.partial_ratio(a, b)

# === MAIN CATEGORIZER CLASS ===
class TransactionCategorizer:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging()
        self.rule_map: Dict[str, str] = {}
        self.rule_keys: List[str] = []
        self._match_cache = {}

        try:
            dm = pd.read_csv(self.config.directional_file)
            dm = dm.dropna(subset=["description_clean"])
            self.directional = set(dm["description_clean"].astype(str))
            self.logger.info(f"Loaded {len(self.directional)} directional merchants")
        except Exception as e:
            self.directional = set()
            self.logger.warning(f"Could not load directional merchants: {e}")

        try:
            ec = pd.read_csv(self.config.refund_edge_cases_file)
            ec = ec.dropna(subset=["description_clean"])
            self.refund_edge_cases = set(ec["description_clean"].astype(str))
            self.logger.info(f"Loaded {len(self.refund_edge_cases)} refund edge-cases")
        except Exception as e:
            self.refund_edge_cases = set()
            self.logger.warning(f"Could not load refund edge-cases: {e}")

    def load_rules(self, rules_file: str = None, db_conn=None, table_name: str = "rules") -> bool:
        try:
            if db_conn:
                self.logger.info("Loading rules from database...")
                if table_name != "rules":
                    raise ValueError("Invalid table name. Only 'rules' table is supported.")
                rules_df = pd.read_sql("SELECT description, category FROM rules", db_conn)
            elif rules_file:
                self.logger.info(f"Loading rules from CSV file: {rules_file}")
                if not Path(rules_file).exists():
                    raise FileNotFoundError(f"Rules file not found: {rules_file}")
                rules_df = pd.read_csv(rules_file)
            else:
                raise ValueError("Must provide either rules_file or db_conn")

            rules_df.columns = rules_df.columns.str.lower().str.strip()
            required_cols = ["description", "category"]
            missing_cols = [col for col in required_cols if col not in rules_df.columns]
            if missing_cols:
                raise ValueError(f"Missing columns: {missing_cols}")

            rules_df = rules_df.dropna(subset=["description", "category"])
            rules_df["description_clean"] = rules_df["description"].apply(enhanced_clean_description)
            rules_df = rules_df[rules_df["description_clean"] != ""]

            self.rule_map = rules_df.set_index("description_clean")["category"].to_dict()
            self.rule_keys = list(self.rule_map.keys())
            self.logger.info(f"Loaded {len(self.rule_keys)} categorisation rules.")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load rules: {e}")
            return False

    def load_bank_statement(self, bank_file: str) -> Optional[pd.DataFrame]:
        try:
            self.logger.info(f"Loading bank statement from {bank_file}")
            if not Path(bank_file).exists():
                raise FileNotFoundError(f"Bank statement file not found: {bank_file}")

            bank_df = pd.read_csv(bank_file)
            if "Description" not in bank_df.columns:
                raise ValueError("Missing 'Description' column in bank statement file")

            bank_df["Description_Clean"] = bank_df["Description"].apply(enhanced_clean_description)
            self.logger.info(f"Successfully loaded {len(bank_df)} transactions")
            return bank_df

        except Exception as e:
            self.logger.error(f"Error loading bank statement: {e}")
            return None

    @lru_cache(maxsize=1000)
    def _cached_match(self, desc_clean: str) -> Tuple[str, float, str]:
        return self._get_best_match_internal(desc_clean)

    def _get_best_match_internal(self, desc_clean: str) -> Tuple[str, float, str]:
        if not desc_clean or not self.rule_keys:
            return ("Uncategorised", 0.0, "")

        if desc_clean in self.rule_map:
            return (self.rule_map[desc_clean], 100.0, desc_clean)

        try:
            result = process.extractOne(desc_clean, self.rule_keys, scorer=hybrid_score)
            if result is None:
                return ("Uncategorised", 0.0, "")

            best_match, score, _ = result
            if score >= self.config.match_threshold:
                return (self.rule_map[best_match], score, best_match)
            else:
                return ("Uncategorised", score, best_match)

        except Exception as e:
            self.logger.warning(f"Error in fuzzy matching for '{desc_clean}': {e}")
            return ("Uncategorised", 0.0, "")

    def get_best_match(self, desc: str) -> Tuple[str, float, str]:
        desc_clean = enhanced_clean_description(desc)
        return self._cached_match(desc_clean)

    def get_top_suggestions(self, desc: str, num: int = None) -> Tuple[List[str], List[float]]:
        if num is None:
            num = self.config.num_suggestions

        desc_clean = enhanced_clean_description(desc)
        if not desc_clean or not self.rule_keys:
            return (["No Match"] * num, [0.0] * num)

        try:
            matches = process.extract(desc_clean, self.rule_keys, scorer=hybrid_score, score_cutoff=50, limit=num)
            suggestions = [self.rule_map[match[0]] for match in matches]
            confidences = [round(match[1], 2) for match in matches]

            while len(suggestions) < num:
                suggestions.append("No Match")
                confidences.append(0.0)

            return suggestions, confidences

        except Exception as e:
            self.logger.warning(f"Error getting suggestions for '{desc}': {e}")
            return (["No Match"] * num, [0.0] * num)

    def should_auto_approve(self, category: str, score: float) -> bool:
        return (score >= self.config.auto_approve_threshold and category != "Uncategorised")

    POSITIVE_COLS = {"credit", "paid in", "money in", "inflow"}
    NEGATIVE_COLS = {"debit",  "paid out","money out","outflow"}

    def _get_signed_value(self, row: pd.Series) -> float:
        """
        Look through all columns in `row`, match case-insensitively
        against POSITIVE_COLS / NEGATIVE_COLS, and return a signed float.
        """
        for col, val in row.items():
            if pd.isnull(val):
                continue
            key = col.lower().strip()
            if key in self.POSITIVE_COLS:
                return abs(float(val))
            if key in self.NEGATIVE_COLS:
                return -abs(float(val))

        # fallback: any column named 'amount' (case-insensitive)
        for col, val in row.items():
            if pd.isnull(val):
                continue
            if col.lower().strip() == "amount":
                return float(val)

        return 0.0

    def categorize_transactions(self, bank_df: pd.DataFrame) -> pd.DataFrame:
        self.logger.info("Starting transaction categorization...")
        start_time = time.time()

        categories      = []
        match_scores    = []
        matched_rules   = []
        auto_approved   = []
        suggestion_cols = [[] for _ in range(self.config.num_suggestions)]
        values_list     = []

        total = len(bank_df)
        processed = 0

        try:
            for _, row in bank_df.iterrows():
                # 1) Read and clean description
                desc       = row["Description"]
                desc_clean = enhanced_clean_description(desc)

                # 2) Compute signed value
                value = self._get_signed_value(row)

                # 3) Fuzzy-match
                base_cat, score, matched_rule = self.get_best_match(desc)

                # 4) Prefix logic – only in tax‐mode with a built-in directional merchant
                if self.config.use_tax_rules and matched_rule in self.directional:
                    if value < 0:
                        # always prefix debits as Expense in tax mode
                        category = f"Expense: {base_cat}"
                    elif matched_rule not in self.refund_edge_cases:
                        # in tax mode, credits → Refund (unless edge‐case)
                        category = f"Refund: {base_cat}"
                    else:
                        # credits but this is an edge‐case merchant
                        category = f"Income: {base_cat}"
                else:
                    # accounting mode or custom rules or non‐directional merchants: no prefix
                    category = base_cat

                # 5) Collect results
                categories.append(category)
                match_scores.append(round(score, 2))
                matched_rules.append(matched_rule)
                auto_approved.append(self.should_auto_approve(base_cat, score))
                values_list.append(value)

                # 6) Suggestions (unchanged)
                if base_cat == "Uncategorised":
                    suggestions, confidences = self.get_top_suggestions(desc)
                    for i, (sugg, conf) in enumerate(zip(suggestions, confidences)):
                        suggestion_cols[i].append(f"{sugg} ({conf}%)")
                else:
                    for i in range(self.config.num_suggestions):
                        suggestion_cols[i].append("")

                processed += 1
                if processed % 100 == 0:
                    self.logger.info(f"Processed {processed}/{total} transactions")

            # 7) Assemble output
            out = bank_df.copy()
            out["Category"]      = categories
            out["Match_Score"]   = match_scores
            out["Matched_Rule"]  = matched_rules
            out["Values"]        = values_list
            out["Auto_Approved"] = auto_approved
            for i in range(self.config.num_suggestions):
                out[f"Suggestion_{i+1}"] = suggestion_cols[i]

            elapsed = time.time() - start_time
            self.logger.info(f"Categorization completed in {elapsed:.2f} seconds")
            return out

        except Exception as e:
            self.logger.error(f"Error during categorization: {e}")
            raise

    def generate_report(self, results_df: pd.DataFrame) -> Dict:
        total = len(results_df)
        uncategorised = (results_df["Category"] == "Uncategorised").sum()
        categorised = total - uncategorised
        auto_approved = results_df["Auto_Approved"].sum()
        categorised_scores = results_df[results_df["Category"] != "Uncategorised"]["Match_Score"]
        avg_confidence = categorised_scores.mean() if len(categorised_scores) > 0 else 0
        high_confidence = (results_df["Match_Score"] >= self.config.auto_approve_threshold).sum()

        report = {
            "total_transactions": total,
            "categorised": categorised,
            "uncategorised": uncategorised,
            "categorisation_rate": round((categorised / total) * 100, 2),
            "auto_approved": auto_approved,
            "avg_confidence": round(avg_confidence, 2),
            "high_confidence_matches": high_confidence
        }

        return report

    def save_results(self, results_df: pd.DataFrame, output_file: str) -> bool:
        try:
            results_df.to_csv(output_file, index=False)
            self.logger.info(f"[SUCCESS] Results saved to {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving results to {output_file}: {e}")
            return False

    def run_categorization(self, db_conn=None) -> bool:
        self.logger.info("Starting bank statement categorization process")
        if not self.load_rules(self.config.rules_file, db_conn=db_conn):
            return False

        bank_df = self.load_bank_statement(self.config.bank_statement_file)
        if bank_df is None:
            return False

        try:
            results_df = self.categorize_transactions(bank_df)
        except Exception as e:
            self.logger.error(f"Categorization failed: {e}")
            return False

        report = self.generate_report(results_df)
        self.logger.info("=== CATEGORIZATION REPORT ===")
        for key, value in report.items():
            self.logger.info(f"{key.replace('_', ' ').title()}: {value}")

        if not self.save_results(results_df, self.config.output_file):
            return False

        self.logger.info("[SUCCESS] Categorization process completed successfully")
        return True

# === MAIN EXECUTION ===
def main():
    config = Config()
    categorizer = TransactionCategorizer(config)
    success = categorizer.run_categorization()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
