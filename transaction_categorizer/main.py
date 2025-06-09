# main.py
import sys
from config import Config
from logger_manager import LoggerManager
from rule_loader import RuleLoader
from bank_loader import BankStatementLoader
from fuzzy_matcher import FuzzyMatcher
from transaction_categorizer import TransactionCategorizer

def main():
    config = Config(
        bank_statement_file="...",
        rules_file="...",
        output_file="..."
    )

    logger = LoggerManager.setup_logger()
    rule_loader = RuleLoader(logger)
    bank_loader = BankStatementLoader(logger)

    try:
        rule_map = rule_loader.load_rules(config.rules_file)
        matcher = FuzzyMatcher(rule_map, config, logger)
        bank_df = bank_loader.load(config.bank_statement_file)
        categorizer = TransactionCategorizer(config, logger, rule_loader, bank_loader, matcher)
        results = categorizer.categorize(bank_df)
        results.to_csv(config.output_file, index=False)
        logger.info("Done.")
    except Exception as e:
        logger.error(f"Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
