# === IMPORTS ===
import pandas as pd  # Data manipulation library
from rapidfuzz import process, fuzz  # Fast fuzzy string matching
import re  # Regular expressions for text cleaning
import sys  # Used for exiting with success/failure status
import logging  # Logging infrastructure
from functools import lru_cache  # For memoization of match function
from dataclasses import dataclass  # For clean configuration structure
from typing import Tuple, List, Dict, Optional  # Type annotations
import time  # Measuring execution time
from pathlib import Path  # Path utilities for file existence checking

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

# === LOGGING SETUP ===
def setup_logging():
    """Configure logging for the application"""
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # Format for logs

    console_handler = logging.StreamHandler()  # Logs to stdout
    console_handler.setFormatter(formatter)  # Attach formatter to console logs

    file_handler = logging.FileHandler('categorizer.log', encoding='utf-8')  # Log file handler
    file_handler.setFormatter(formatter)  # Attach formatter to file logs

    logger = logging.getLogger(__name__)  # Get logger instance
    logger.setLevel(logging.INFO)  # Set logging level
    logger.addHandler(console_handler)  # Add console handler
    logger.addHandler(file_handler)  # Add file handler

    return logger  # Return configured logger

# === ENHANCED CLEANING FUNCTIONS ===
def enhanced_clean_description(text: str) -> str:
    """Enhanced cleaning with financial-specific preprocessing"""
    if not isinstance(text, str) or not text.strip():  # Handle null or non-string input
        return ""
    
    text = text.lower().strip()  # Lowercase and strip whitespace
    text = re.sub(r'\b(ref|payment|purchase|transaction|debit|credit)\b', '', text)  # Remove common transaction terms
    text = re.sub(r'\b\d{4,}\b', '', text)  # Remove long digit sequences
    text = re.sub(r'[^a-z0-9 ]', '', text)  # Remove special characters
    text = re.sub(r'\s+', ' ', text)  # Normalise multiple spaces

    return text.strip()  # Return cleaned string

def basic_clean_description(text: str) -> str:
    """Basic cleaning function (fallback)"""
    if not isinstance(text, str):  # Handle non-string input
        return ""
    text = text.lower()  # Lowercase
    text = re.sub(r"[^a-z0-9 ]", "", text)  # Remove non-alphanumerics
    text = re.sub(r"\s+", " ", text)  # Normalise spaces
    return text.strip()  # Return cleaned string

# === HYBRID SCORER ===
def hybrid_score(a: str, b: str, **kwargs) -> float:
    """Weighted combo of token_set_ratio (structure) and partial_ratio (substring)"""
    return 0.6 * fuzz.token_set_ratio(a, b) + 0.4 * fuzz.partial_ratio(a, b)  # Weighted scoring

# === MAIN CATEGORIZER CLASS ===
class TransactionCategorizer:
    """
    Main class for categorizing bank transactions using fuzzy matching
    """

    def __init__(self, config: Config):
        self.config = config  # Configuration object
        self.logger = setup_logging()  # Logger instance
        self.rule_map: Dict[str, str] = {}  # Cleaned descriptions → category
        self.rule_keys: List[str] = []  # List of cleaned descriptions
        self._match_cache = {}  # Placeholder; not used as lru_cache replaces it

    def load_rules(self, rules_file: str) -> bool:
        """Load and preprocess categorization rules"""
        try:
            self.logger.info(f"Loading rules from {rules_file}")
            if not Path(rules_file).exists():  # Validate file existence
                raise FileNotFoundError(f"Rules file not found: {rules_file}")
            
            rules_df = pd.read_csv(rules_file)  # Load rules into DataFrame

            required_cols = ["Description", "Category"]
            missing_cols = [col for col in required_cols if col not in rules_df.columns]  # Check required columns
            if missing_cols:
                raise ValueError(f"Missing columns in rules file: {missing_cols}")
            if rules_df.empty:
                raise ValueError("Rules file is empty")  # Check for empty file

            rules_df = rules_df.dropna(subset=["Description", "Category"])  # Drop rows with missing values
            rules_df["Description_Clean"] = rules_df["Description"].apply(enhanced_clean_description)  # Clean descriptions
            rules_df = rules_df[rules_df["Description_Clean"] != ""]  # Filter out empty cleaned values

            self.rule_map = rules_df.set_index("Description_Clean")["Category"].to_dict()  # Map cleaned to category
            self.rule_keys = list(self.rule_map.keys())  # Store cleaned keys
            self.logger.info(f"Successfully loaded {len(self.rule_keys)} rules")
            return True

        except Exception as e:
            self.logger.error(f"Error loading rules file: {e}")
            return False

    def load_bank_statement(self, bank_file: str) -> Optional[pd.DataFrame]:
        """Load and validate bank statement"""
        try:
            self.logger.info(f"Loading bank statement from {bank_file}")
            if not Path(bank_file).exists():  # Validate file existence
                raise FileNotFoundError(f"Bank statement file not found: {bank_file}")
            
            bank_df = pd.read_csv(bank_file)  # Load bank data
            if "Description" not in bank_df.columns:
                raise ValueError("Missing 'Description' column in bank statement file")  # Check for required column

            bank_df["Description_Clean"] = bank_df["Description"].apply(enhanced_clean_description)  # Clean descriptions
            self.logger.info(f"Successfully loaded {len(bank_df)} transactions")
            return bank_df

        except Exception as e:
            self.logger.error(f"Error loading bank statement: {e}")
            return None

    @lru_cache(maxsize=1000)
    def _cached_match(self, desc_clean: str) -> Tuple[str, float, str]:
        """Cached version of get_best_match for performance"""
        return self._get_best_match_internal(desc_clean)  # Delegate to internal logic

    def _get_best_match_internal(self, desc_clean: str) -> Tuple[str, float, str]:
        """Internal matching logic"""
        if not desc_clean or not self.rule_keys:  # Early exit if no rules or input
            return ("Uncategorised", 0.0, "")
        
        if desc_clean in self.rule_map:  # Exact match
            return (self.rule_map[desc_clean], 100.0, desc_clean)

        try:
            result = process.extractOne(desc_clean, self.rule_keys, scorer=hybrid_score)  # Fuzzy match
            if result is None:
                return ("Uncategorised", 0.0, "")

            best_match, score, _ = result  # Unpack result
            if score >= self.config.match_threshold:  # Threshold check
                return (self.rule_map[best_match], score, best_match)
            else:
                return ("Uncategorised", score, best_match)

        except Exception as e:
            self.logger.warning(f"Error in fuzzy matching for '{desc_clean}': {e}")
            return ("Uncategorised", 0.0, "")

    def get_best_match(self, desc: str) -> Tuple[str, float, str]:
        """Get the best category match for a description"""
        desc_clean = enhanced_clean_description(desc)  # Clean input
        return self._cached_match(desc_clean)  # Use cached matcher

    def get_top_suggestions(self, desc: str, num: int = None) -> Tuple[List[str], List[float]]:
        """Get top N category suggestions for uncategorized transactions"""
        if num is None:
            num = self.config.num_suggestions  # Default if not provided

        desc_clean = enhanced_clean_description(desc)  # Clean input
        if not desc_clean or not self.rule_keys:  # Handle empty or missing rules
            return (["No Match"] * num, [0.0] * num)

        try:
            matches = process.extract(desc_clean, self.rule_keys, scorer=hybrid_score, score_cutoff=50, limit=num)  # Top matches
            suggestions = [self.rule_map[match[0]] for match in matches]  # Map to categories
            confidences = [round(match[1], 2) for match in matches]  # Get scores

            while len(suggestions) < num:  # Pad if less than required
                suggestions.append("No Match")
                confidences.append(0.0)

            return suggestions, confidences

        except Exception as e:
            self.logger.warning(f"Error getting suggestions for '{desc}': {e}")
            return (["No Match"] * num, [0.0] * num)

    def should_auto_approve(self, category: str, score: float) -> bool:
        """Determine if a match should be auto-approved"""
        return (score >= self.config.auto_approve_threshold and category != "Uncategorised")

    def categorize_transactions(self, bank_df: pd.DataFrame) -> pd.DataFrame:
        """Main categorization function"""
        self.logger.info("Starting transaction categorization...")
        start_time = time.time()  # Start timer

        # Initialise result containers
        categories = []
        match_scores = []
        matched_rules = []
        auto_approved = []
        suggestion_cols = [[] for _ in range(self.config.num_suggestions)]

        total_transactions = len(bank_df)
        processed = 0  # Progress counter

        try:
            for idx, row in bank_df.iterrows():  # Iterate transactions
                desc = row["Description"]
                category, score, matched_rule = self.get_best_match(desc)  # Fuzzy match

                categories.append(category)
                match_scores.append(round(score, 2))
                matched_rules.append(matched_rule)
                auto_approved.append(self.should_auto_approve(category, score))

                if category == "Uncategorised":
                    suggestions, confidences = self.get_top_suggestions(desc)
                    for i, (sugg, conf) in enumerate(zip(suggestions, confidences)):
                        suggestion_cols[i].append(f"{sugg} ({conf}%)")  # Add suggestion with confidence
                else:
                    for i in range(self.config.num_suggestions):
                        suggestion_cols[i].append("")  # No suggestions needed

                processed += 1
                if processed % 100 == 0:
                    self.logger.info(f"Processed {processed}/{total_transactions} transactions")

            # Compile final DataFrame
            bank_df = bank_df.copy()
            bank_df["Category"] = categories
            bank_df["Match_Score"] = match_scores
            bank_df["Matched_Rule"] = matched_rules
            bank_df["Auto_Approved"] = auto_approved

            for i in range(self.config.num_suggestions):
                bank_df[f"Suggestion_{i+1}"] = suggestion_cols[i]

            elapsed_time = time.time() - start_time  # End timer
            self.logger.info(f"Categorization completed in {elapsed_time:.2f} seconds")
            return bank_df

        except Exception as e:
            self.logger.error(f"Error during categorization: {e}")
            raise

    def generate_report(self, results_df: pd.DataFrame) -> Dict:
        """Generate categorization statistics"""
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

        return report  # Return statistics dictionary

    def save_results(self, results_df: pd.DataFrame, output_file: str) -> bool:
        """Save categorization results to CSV"""
        try:
            results_df.to_csv(output_file, index=False)  # Write to CSV
            self.logger.info(f"[SUCCESS] Results saved to {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving results to {output_file}: {e}")
            return False

    def run_categorization(self) -> bool:
        """Main execution function"""
        self.logger.info("Starting bank statement categorization process")
        if not self.load_rules(self.config.rules_file):  # Load rules
            return False

        bank_df = self.load_bank_statement(self.config.bank_statement_file)  # Load transactions
        if bank_df is None:
            return False

        try:
            results_df = self.categorize_transactions(bank_df)  # Categorize
        except Exception as e:
            self.logger.error(f"Categorization failed: {e}")
            return False

        report = self.generate_report(results_df)  # Generate report
        self.logger.info("=== CATEGORIZATION REPORT ===")
        for key, value in report.items():  # Print stats
            self.logger.info(f"{key.replace('_', ' ').title()}: {value}")

        if not self.save_results(results_df, self.config.output_file):  # Save to CSV
            return False

        self.logger.info("[SUCCESS] Categorization process completed successfully")
        return True

# === MAIN EXECUTION ===
def main():
    """Main entry point"""
    config = Config()  # Create empty config (set values before running)
    categorizer = TransactionCategorizer(config)  # Instantiate categorizer
    success = categorizer.run_categorization()  # Run main logic
    sys.exit(0 if success else 1)  # Exit with status

if __name__ == "__main__":
    main()  # Run main
