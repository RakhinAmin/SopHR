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
        # Attempt to load categorisation rules from either a database or CSV file
        try:
            if db_conn:
                # If a database connection is provided, load rules from the specified table
                self.logger.info("Loading rules from database...")
                # Only the default 'rules' table is allowed
                if table_name != "rules":
                    raise ValueError("Invalid table name. Only 'rules' table is supported.")
                # Read description and category columns into a DataFrame
                rules_df = pd.read_sql("SELECT description, category FROM rules", db_conn)

            elif rules_file:
                # If a file path is provided instead, load rules from a CSV file
                self.logger.info(f"Loading rules from CSV file: {rules_file}")
                # Verify that the file exists before attempting to read
                if not Path(rules_file).exists():
                    raise FileNotFoundError(f"Rules file not found: {rules_file}")
                # Read CSV into a DataFrame
                rules_df = pd.read_csv(rules_file)

            else:
                # Neither a database connection nor a file path was provided
                raise ValueError("Must provide either rules_file or db_conn")

            # Standardise column names to lowercase without surrounding whitespace
            rules_df.columns = rules_df.columns.str.lower().str.strip()
            # Define the required columns for successful processing
            required_cols = ["description", "category"]
            # Identify any missing required columns
            missing_cols = [col for col in required_cols if col not in rules_df.columns]
            if missing_cols:
                raise ValueError(f"Missing columns: {missing_cols}")

            # Remove any rows where description or category is missing
            rules_df = rules_df.dropna(subset=["description", "category"])
            # Clean each description using the enhanced cleaning function
            rules_df["description_clean"] = rules_df["description"].apply(enhanced_clean_description)
            # Discard any entries whose cleaned description is empty
            rules_df = rules_df[rules_df["description_clean"] != ""]

            # Build a mapping from cleaned description to category
            self.rule_map = rules_df.set_index("description_clean")["category"].to_dict()
            # Store the list of rule keys for quick access
            self.rule_keys = list(self.rule_map.keys())
            self.logger.info(f"Loaded {len(self.rule_keys)} categorisation rules.")
            return True

        except Exception as e:
            # Log any failure and return False to indicate loading did not succeed
            self.logger.error(f"Failed to load rules: {e}")
            return False

    def load_bank_statement(self, bank_file: str) -> Optional[pd.DataFrame]:
        # Attempt to read a bank statement CSV into a DataFrame
        try:
            self.logger.info(f"Loading bank statement from {bank_file}")
            # Verify that the specified file path exists
            if not Path(bank_file).exists():
                raise FileNotFoundError(f"Bank statement file not found: {bank_file}")

            # Read the CSV file into a DataFrame
            bank_df = pd.read_csv(bank_file)
            # Ensure the essential 'Description' column is present
            if "Description" not in bank_df.columns:
                raise ValueError("Missing 'Description' column in bank statement file")

            # Apply cleaning function to each transaction description
            bank_df["Description_Clean"] = bank_df["Description"].apply(enhanced_clean_description)
            self.logger.info(f"Successfully loaded {len(bank_df)} transactions")
            # Return the processed DataFrame on success
            return bank_df

        except Exception as e:
            # Log any error encountered and return None to indicate failure
            self.logger.error(f"Error loading bank statement: {e}")
            return None

    @lru_cache(maxsize=1000)
    def _cached_match(self, desc_clean: str) -> Tuple[str, float, str]:
        # Use LRU cache to store up to 1000 recent match results for efficiency
        # desc_clean: cleaned description string to match
        # Returns a tuple of (best_match, similarity_score, category)
        return self._get_best_match_internal(desc_clean)  # Delegate to internal matching logic

    def _get_best_match_internal(self, desc_clean: str) -> Tuple[str, float, str]:
        # Determine the best matching rule for a cleaned description string
        # Returns a tuple: (category, similarity_score, matched_rule_key)

        # If the description is empty or no rules have been loaded, return uncategorised
        if not desc_clean or not self.rule_keys:
            return ("Uncategorised", 0.0, "")

        # If there is an exact match in the rule map, return it with a perfect score
        if desc_clean in self.rule_map:
            return (self.rule_map[desc_clean], 100.0, desc_clean)

        try:
            # Perform fuzzy matching against loaded rule keys using a hybrid scoring function
            result = process.extractOne(desc_clean, self.rule_keys, scorer=hybrid_score)
            # If no match is found, treat as uncategorised
            if result is None:
                return ("Uncategorised", 0.0, "")

            best_match, score, _ = result
            # If score meets or exceeds the threshold, return the matched category
            if score >= self.config.match_threshold:
                return (self.rule_map[best_match], score, best_match)
            # Otherwise, return uncategorised with the highest-scoring candidate for reference
            else:
                return ("Uncategorised", score, best_match)

        except Exception as e:
            # Log any errors during fuzzy matching and return uncategorised
            self.logger.warning(f"Error in fuzzy matching for '{desc_clean}': {e}")
            return ("Uncategorised", 0.0, "")

    def get_best_match(self, desc: str) -> Tuple[str, float, str]:
        # Clean the raw description text using the enhanced cleaning function
        desc_clean = enhanced_clean_description(desc)
        # Delegate to the cached matcher to obtain (category, similarity_score, matched_rule_key)
        return self._cached_match(desc_clean)

    def get_top_suggestions(self, desc: str, num: int = None) -> Tuple[List[str], List[float]]:
        # Determine how many suggestions to return, defaulting to configuration if not provided
        if num is None:
            num = self.config.num_suggestions

        # Clean the raw description text before matching
        desc_clean = enhanced_clean_description(desc)
        # If the cleaned description is empty or there are no rules loaded, return placeholder results
        if not desc_clean or not self.rule_keys:
            return (["No Match"] * num, [0.0] * num)

        try:
            # Perform fuzzy matching to retrieve up to 'num' close matches above the score cutoff
            matches = process.extract(
                desc_clean,
                self.rule_keys,
                scorer=hybrid_score,
                score_cutoff=50,
                limit=num
            )
            # Map each matched rule key to its category
            suggestions = [self.rule_map[match[0]] for match in matches]
            # Round the similarity scores to two decimal places for readability
            confidences = [round(match[1], 2) for match in matches]

            # If fewer than 'num' matches were found, pad the results with 'No Match'
            while len(suggestions) < num:
                suggestions.append("No Match")
                confidences.append(0.0)

            return suggestions, confidences

        except Exception as e:
            # Log any errors encountered and return placeholder results
            self.logger.warning(f"Error getting suggestions for '{desc}': {e}")
            return (["No Match"] * num, [0.0] * num)

    def should_auto_approve(self, category: str, score: float) -> bool:
        # Return True if the match score meets the auto-approval threshold and is not uncategorised
        return (score >= self.config.auto_approve_threshold and category != "Uncategorised")

    POSITIVE_COLS = {"credit", "paid in", "money in", "inflow"}
    NEGATIVE_COLS = {"debit", "paid out", "money out", "outflow"}

    def _get_signed_value(self, row: pd.Series) -> float:
        """
        Sum up all 'positive' columns minus all 'negative' columns, regardless of order.
        Fallback to a single 'amount' column only if neither found.
        """
        credit_total = 0.0
        debit_total  = 0.0

        # 1) accumulate across every column tagged as positive
        for col, val in row.items():
            if pd.isnull(val):
                continue
            key = col.lower().strip()
            if key in self.POSITIVE_COLS:
                credit_total += abs(float(val))

        # 2) accumulate across every column tagged as negative
        for col, val in row.items():
            if pd.isnull(val):
                continue
            key = col.lower().strip()
            if key in self.NEGATIVE_COLS:
                debit_total += abs(float(val))

        # 3) if we saw *any* credit or debit, return their difference
        if credit_total != 0.0 or debit_total != 0.0:
            return credit_total - debit_total

        # 4) fallback: single 'amount' column (could already be signed)
        for col, val in row.items():
            if pd.isnull(val):
                continue
            if col.lower().strip() == "amount":
                return float(val)

        # 5) truly nothing found → zero
        return 0.0

    def categorize_transactions(self, bank_df: pd.DataFrame) -> pd.DataFrame:
        # Log start of categorisation process and record start time
        self.logger.info("Starting transaction categorization...")
        start_time = time.time()

        # Initialise containers for results
        categories      = []
        match_scores    = []
        matched_rules   = []
        auto_approved   = []
        suggestion_cols = [[] for _ in range(self.config.num_suggestions)]
        values_list     = []

        total = len(bank_df)
        processed = 0

        try:
            # Iterate over each transaction row
            for _, row in bank_df.iterrows():
                # 1) Read raw description and clean it
                desc       = row["Description"]
                desc_clean = enhanced_clean_description(desc)

                # 2) Compute the signed transaction value (credit vs debit)
                value = self._get_signed_value(row)

                # 3) Perform fuzzy matching to get base category, score, and matched rule key
                base_cat, score, matched_rule = self.get_best_match(desc)

                # 4) Apply prefix logic when in tax mode and merchant is directional
                if self.config.use_tax_rules and matched_rule in self.directional:
                    if value < 0:
                        # In tax mode, negative values always treated as expenses
                        category = f"Expense: {base_cat}"
                    elif matched_rule not in self.refund_edge_cases:
                        # Positive values become refunds unless flagged as edge cases
                        category = f"Refund: {base_cat}"
                    else:
                        # Edge‐case merchant credits treated as income
                        category = f"Income: {base_cat}"
                else:
                    # Default accounting or custom rules: use base category without prefix
                    category = base_cat

                # 5) Append results to respective lists
                categories.append(category)
                match_scores.append(round(score, 2))
                matched_rules.append(matched_rule)
                auto_approved.append(self.should_auto_approve(base_cat, score))
                values_list.append(value)

                # 6) Provide alternative suggestions for uncategorised items
                if base_cat == "Uncategorised":
                    suggestions, confidences = self.get_top_suggestions(desc)
                    for i, (sugg, conf) in enumerate(zip(suggestions, confidences)):
                        suggestion_cols[i].append(f"{sugg} ({conf}%)")
                else:
                    # Not uncategorised: leave suggestion fields empty
                    for i in range(self.config.num_suggestions):
                        suggestion_cols[i].append("")

                processed += 1
                # Periodically log progress every 100 transactions
                if processed % 100 == 0:
                    self.logger.info(f"Processed {processed}/{total} transactions")

            # 7) Build output DataFrame by copying input and adding result columns
            out = bank_df.copy()
            out["Category"]      = categories
            out["Match_Score"]   = match_scores
            out["Matched_Rule"]  = matched_rules
            out["Values"]        = values_list
            out["Auto_Approved"] = auto_approved
            for i in range(self.config.num_suggestions):
                out[f"Suggestion_{i+1}"] = suggestion_cols[i]

            # Log total time taken for categorisation
            elapsed = time.time() - start_time
            self.logger.info(f"Categorization completed in {elapsed:.2f} seconds")
            return out

        except Exception as e:
            # Log unexpected errors and re‐raise for upstream handling
            self.logger.error(f"Error during categorization: {e}")
            raise

    def generate_report(self, results_df: pd.DataFrame) -> Dict:
        # Calculate the total number of transactions processed
        total = len(results_df)
        # Count how many transactions remain uncategorised
        uncategorised = (results_df["Category"] == "Uncategorised").sum()
        # Determine how many transactions were successfully categorised
        categorised = total - uncategorised
        # Sum the number of transactions that were auto-approved
        auto_approved = results_df["Auto_Approved"].sum()
        # Select match scores for only those transactions that were categorised
        categorised_scores = results_df[results_df["Category"] != "Uncategorised"]["Match_Score"]
        # Compute the average confidence score for categorised transactions (or zero if none)
        avg_confidence = categorised_scores.mean() if len(categorised_scores) > 0 else 0
        # Count transactions whose score meets or exceeds the auto-approval threshold
        high_confidence = (results_df["Match_Score"] >= self.config.auto_approve_threshold).sum()

        # Build the summary report with rounded values for readability
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
        """
        Save the processed results DataFrame to a CSV file.

        Returns True on success, False on failure.
        """
        try:
            # Write the DataFrame to CSV without the index column
            results_df.to_csv(output_file, index=False)
            # Log a success message with the output file path
            self.logger.info(f"[SUCCESS] Results saved to {output_file}")
            return True
        except Exception as e:
            # Log any error encountered during file writing
            self.logger.error(f"Error saving results to {output_file}: {e}")
            return False

    def run_categorization(self, db_conn=None) -> bool:
        # Log the start of the overall categorisation process
        self.logger.info("Starting bank statement categorization process")

        # Load categorisation rules from file or database; abort if unsuccessful
        if not self.load_rules(self.config.rules_file, db_conn=db_conn):
            return False

        # Load the bank statement into a DataFrame; abort if unsuccessful
        bank_df = self.load_bank_statement(self.config.bank_statement_file)
        if bank_df is None:
            return False

        try:
            # Apply categorisation logic to all transactions
            results_df = self.categorize_transactions(bank_df)
        except Exception as e:
            # Log any failure during transaction processing and abort
            self.logger.error(f"Categorization failed: {e}")
            return False

        # Generate a summary report from the results
        report = self.generate_report(results_df)
        # Log each metric in the report for visibility
        self.logger.info("=== CATEGORIZATION REPORT ===")
        for key, value in report.items():
            self.logger.info(f"{key.replace('_', ' ').title()}: {value}")

        # Save the detailed results to CSV; abort if unsuccessful
        if not self.save_results(results_df, self.config.output_file):
            return False

        # Log successful completion of the entire process
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
