import pandas as pd
from rapidfuzz import process, fuzz
import re
import sys
import logging
from functools import lru_cache
from dataclasses import dataclass
from typing import Tuple, List, Dict, Optional
import time
from pathlib import Path

# === CONFIGURATION ===
@dataclass
class Config:
    """Configuration settings for the categorizer"""
    bank_statement_file: str = r"C:\Users\Sopher.Intern\Downloads\Testing\bank_statement_2.csv"
    rules_file: str = r"C:\Users\Sopher.Intern\Downloads\Testing\rules.csv"
    output_file: str = r"C:\Users\Sopher.Intern\Downloads\Testing\categorised_output.csv"
    match_threshold: int = 90
    num_suggestions: int = 3
    auto_approve_threshold: int = 95
    chunk_size: int = 1000
    cache_size: int = 1000

# === LOGGING SETUP ===
def setup_logging():
    """Configure logging for the application"""
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Console handler with UTF-8 encoding
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler('categorizer.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Configure logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# === ENHANCED CLEANING FUNCTIONS ===
def enhanced_clean_description(text: str) -> str:
    """
    Enhanced cleaning with financial-specific preprocessing
    """
    if not isinstance(text, str) or not text.strip():
        return ""
    
    text = text.lower().strip()
    
    # Remove common financial prefixes/suffixes
    text = re.sub(r'\b(ref|payment|purchase|transaction|debit|credit)\b', '', text)
    
    # Remove card numbers, reference codes, and long digit sequences
    text = re.sub(r'\b\d{4,}\b', '', text)
    
    # Remove special characters but keep spaces
    text = re.sub(r'[^a-z0-9 ]', '', text)
    
    # Normalize spaces
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
    """Weighted combo of token_set_ratio (structure) and partial_ratio (substring)"""
    return 0.6 * fuzz.token_set_ratio(a, b) + 0.4 * fuzz.partial_ratio(a, b)

# === MAIN CATEGORIZER CLASS ===
class TransactionCategorizer:
    """
    Main class for categorizing bank transactions using fuzzy matching
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logging()
        self.rule_map: Dict[str, str] = {}
        self.rule_keys: List[str] = []
        self._match_cache = {}
        
    def load_rules(self, rules_file: str) -> bool:
        """Load and preprocess categorization rules"""
        try:
            self.logger.info(f"Loading rules from {rules_file}")
            
            if not Path(rules_file).exists():
                raise FileNotFoundError(f"Rules file not found: {rules_file}")
            
            rules_df = pd.read_csv(rules_file)
            
            # Validate required columns
            required_cols = ["Description", "Category"]
            missing_cols = [col for col in required_cols if col not in rules_df.columns]
            if missing_cols:
                raise ValueError(f"Missing columns in rules file: {missing_cols}")
            
            if rules_df.empty:
                raise ValueError("Rules file is empty")
            
            # Remove any rows with empty descriptions or categories
            rules_df = rules_df.dropna(subset=["Description", "Category"])
            
            # Clean descriptions and create mapping
            rules_df["Description_Clean"] = rules_df["Description"].apply(enhanced_clean_description)
            
            # Remove empty cleaned descriptions
            rules_df = rules_df[rules_df["Description_Clean"] != ""]
            
            # Create rule mapping
            self.rule_map = rules_df.set_index("Description_Clean")["Category"].to_dict()
            self.rule_keys = list(self.rule_map.keys())
            
            self.logger.info(f"Successfully loaded {len(self.rule_keys)} rules")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading rules file: {e}")
            return False
    
    def load_bank_statement(self, bank_file: str) -> Optional[pd.DataFrame]:
        """Load and validate bank statement"""
        try:
            self.logger.info(f"Loading bank statement from {bank_file}")
            
            if not Path(bank_file).exists():
                raise FileNotFoundError(f"Bank statement file not found: {bank_file}")
            
            bank_df = pd.read_csv(bank_file)
            
            if "Description" not in bank_df.columns:
                raise ValueError("Missing 'Description' column in bank statement file")
            
            # Precompute cleaned descriptions
            bank_df["Description_Clean"] = bank_df["Description"].apply(enhanced_clean_description)
            
            self.logger.info(f"Successfully loaded {len(bank_df)} transactions")
            return bank_df
            
        except Exception as e:
            self.logger.error(f"Error loading bank statement: {e}")
            return None
    
    @lru_cache(maxsize=1000)
    def _cached_match(self, desc_clean: str) -> Tuple[str, float, str]:
        """Cached version of get_best_match for performance"""
        return self._get_best_match_internal(desc_clean)
    
    def _get_best_match_internal(self, desc_clean: str) -> Tuple[str, float, str]:
        """Internal matching logic"""
        if not desc_clean or not self.rule_keys:
            return ("Uncategorised", 0.0, "")
        
        # Check for exact match first
        if desc_clean in self.rule_map:
            return (self.rule_map[desc_clean], 100.0, desc_clean)
        
        # Fuzzy matching
        try:
            result = process.extractOne(
                desc_clean, 
                self.rule_keys, 
                scorer=hybrid_score
            )
            
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
        """Get the best category match for a description"""
        desc_clean = enhanced_clean_description(desc)
        return self._cached_match(desc_clean)
    
    def get_top_suggestions(self, desc: str, num: int = None) -> Tuple[List[str], List[float]]:
        """Get top N category suggestions for uncategorized transactions"""
        if num is None:
            num = self.config.num_suggestions
            
        desc_clean = enhanced_clean_description(desc)
        
        if not desc_clean or not self.rule_keys:
            return (["No Match"] * num, [0.0] * num)
        
        try:
            matches = process.extract(
                desc_clean, 
                self.rule_keys, 
                scorer=hybrid_score, 
                score_cutoff=50, 
                limit=num
            )
            
            suggestions = [self.rule_map[match[0]] for match in matches]
            confidences = [round(match[1], 2) for match in matches]
            
            # Pad with "No Match" if needed
            while len(suggestions) < num:
                suggestions.append("No Match")
                confidences.append(0.0)
                
            return suggestions, confidences
            
        except Exception as e:
            self.logger.warning(f"Error getting suggestions for '{desc}': {e}")
            return (["No Match"] * num, [0.0] * num)
    
    def should_auto_approve(self, category: str, score: float) -> bool:
        """Determine if a match should be auto-approved"""
        return (score >= self.config.auto_approve_threshold and 
                category != "Uncategorised")
    
    def categorize_transactions(self, bank_df: pd.DataFrame) -> pd.DataFrame:
        """Main categorization function"""
        self.logger.info("Starting transaction categorization...")
        start_time = time.time()
        
        # Initialize result columns
        categories = []
        match_scores = []
        matched_rules = []
        auto_approved = []
        suggestion_cols = [[] for _ in range(self.config.num_suggestions)]
        
        total_transactions = len(bank_df)
        processed = 0
        
        try:
            for idx, row in bank_df.iterrows():
                desc = row["Description"]
                
                # Get best match
                category, score, matched_rule = self.get_best_match(desc)
                
                categories.append(category)
                match_scores.append(round(score, 2))
                matched_rules.append(matched_rule)
                auto_approved.append(self.should_auto_approve(category, score))
                
                # Get suggestions for uncategorized transactions
                if category == "Uncategorised":
                    suggestions, confidences = self.get_top_suggestions(desc)
                    for i, (sugg, conf) in enumerate(zip(suggestions, confidences)):
                        suggestion_cols[i].append(f"{sugg} ({conf}%)")
                else:
                    for i in range(self.config.num_suggestions):
                        suggestion_cols[i].append("")
                
                processed += 1
                if processed % 100 == 0:
                    self.logger.info(f"Processed {processed}/{total_transactions} transactions")
            
            # Add results to dataframe
            bank_df = bank_df.copy()
            bank_df["Category"] = categories
            bank_df["Match_Score"] = match_scores
            bank_df["Matched_Rule"] = matched_rules
            bank_df["Auto_Approved"] = auto_approved
            
            for i in range(self.config.num_suggestions):
                bank_df[f"Suggestion_{i+1}"] = suggestion_cols[i]
            
            elapsed_time = time.time() - start_time
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
        
        # Calculate average confidence for categorised transactions
        categorised_scores = results_df[results_df["Category"] != "Uncategorised"]["Match_Score"]
        avg_confidence = categorised_scores.mean() if len(categorised_scores) > 0 else 0
        
        # High confidence matches
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
        """Save categorization results to CSV"""
        try:
            results_df.to_csv(output_file, index=False)
            self.logger.info(f"[SUCCESS] Results saved to {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving results to {output_file}: {e}")
            return False
    
    def run_categorization(self) -> bool:
        """Main execution function"""
        self.logger.info("Starting bank statement categorization process")
        
        # Load rules
        if not self.load_rules(self.config.rules_file):
            return False
        
        # Load bank statement
        bank_df = self.load_bank_statement(self.config.bank_statement_file)
        if bank_df is None:
            return False
        
        # Categorize transactions
        try:
            results_df = self.categorize_transactions(bank_df)
        except Exception as e:
            self.logger.error(f"Categorization failed: {e}")
            return False
        
        # Generate and log report
        report = self.generate_report(results_df)
        self.logger.info("=== CATEGORIZATION REPORT ===")
        for key, value in report.items():
            self.logger.info(f"{key.replace('_', ' ').title()}: {value}")
        
        # Save results
        if not self.save_results(results_df, self.config.output_file):
            return False
        
        self.logger.info("[SUCCESS] Categorization process completed successfully")
        return True

# === MAIN EXECUTION ===
def main():
    """Main entry point"""
    config = Config()
    categorizer = TransactionCategorizer(config)
    
    success = categorizer.run_categorization()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()