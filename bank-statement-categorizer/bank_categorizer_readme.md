# Bank Statement Categoriser

A powerful Python tool for automatically categorizing bank transactions using fuzzy logic matching. This system uses advanced string matching algorithms to intelligently classify financial transactions based on customizable rules. Created by Ali Ladak.

## Features

- 🚀 **Fast Processing**: Efficiently handles large transaction datasets
- 🧠 **Smart Matching**: Uses hybrid fuzzy logic combining token-set and partial ratio matching
- 📊 **Detailed Reporting**: Comprehensive statistics and confidence scores
- 🔧 **Configurable**: Customizable thresholds and parameters
- 💾 **Caching**: Built-in LRU cache for improved performance
- 📝 **Logging**: Detailed logging with both console and file output
- 🎯 **Auto-Approval**: Automatic categorization for high-confidence matches
- 💡 **Smart Suggestions**: Multiple category suggestions for unmatched transactions

## Requirements

### Python Version
- Python 3.7 or higher

### Dependencies
```
pandas>=1.3.0
rapidfuzz>=2.0.0
```

## Installation

1. **Clone or download the repository**
```bash
git clone <repository-url>
cd bank-statement-categoriser
```

2. **Install required packages**
```bash
pip install pandas rapidfuzz
```

## File Structure

```
bank-statement-categoriser/
├── fuzzy_logic_improved.py    # Main application file
├── README.md                  # This file
├── rules.csv                  # Category rules file
├── bank_statement.csv         # Your bank statement data
└── categorized_output.csv     # Generated results (after running)
```

## Input File Formats

### Bank Statement File (CSV)
Your bank statement CSV must contain at least a `Description` column:

```csv
Date,Description,Amount,Balance
2024-01-01,TESCO STORE 1234,25.50,1000.00
2024-01-02,SHELL PETROL STATION,45.00,955.00
2024-01-03,AMAZON PRIME MEMBERSHIP,7.99,947.01
```

**Required columns:**
- `Description`: Transaction description text

**Optional columns:**
- Any additional columns (Date, Amount, Balance, etc.) will be preserved in the output

### Rules File (CSV)
Create a rules file that maps transaction patterns to categories:

```csv
Description,Category
tesco,Groceries
shell,Transport
amazon,Shopping
starbucks,Food & Drink
salary,Income
mortgage,Housing
```

**Required columns:**
- `Description`: Pattern to match against transaction descriptions
- `Category`: Category to assign when pattern matches

## Configuration

### Method 1: Edit Configuration in Code
Modify the `Config` class in `fuzzy_logic_improved.py`:

```python
@dataclass
class Config:
    bank_statement_file: str = "your_bank_statement.csv"
    rules_file: str = "your_rules.csv"
    output_file: str = "categorized_output.csv"
    match_threshold: int = 70          # Minimum score for categorization
    num_suggestions: int = 3           # Number of suggestions for unmatched
    auto_approve_threshold: int = 80   # Score for auto-approval
    chunk_size: int = 1000            # Processing chunk size
    cache_size: int = 1000            # LRU cache size
```

### Method 2: Update File Paths
Simply update the file paths in the configuration:

```python
bank_statement_file: str = r"C:\path\to\your\bank_statement.csv"
rules_file: str = r"C:\path\to\your\rules.csv"
```

## Usage

### Basic Usage
```bash
python fuzzy_logic_improved.py
```

### What Happens During Execution

1. **Loading**: Reads your bank statement and rules files
2. **Preprocessing**: Cleans transaction descriptions for better matching
3. **Matching**: Uses fuzzy logic to find best category matches
4. **Scoring**: Assigns confidence scores to each match
5. **Suggestions**: Provides alternative categories for unmatched transactions
6. **Output**: Saves results to CSV with detailed categorization data

## Understanding the Output

The generated CSV file contains these additional columns:

| Column | Description |
|--------|-------------|
| `Category` | Assigned category or "Uncategorised" |
| `Match_Score` | Confidence score (0-100) |
| `Matched_Rule` | The rule pattern that matched |
| `Auto_Approved` | Whether match was auto-approved |
| `Suggestion_1` | First alternative category |
| `Suggestion_2` | Second alternative category |
| `Suggestion_3` | Third alternative category |

### Example Output
```csv
Date,Description,Amount,Category,Match_Score,Auto_Approved,Suggestion_1
2024-01-01,TESCO STORE 1234,25.50,Groceries,95.0,true,
2024-01-02,UNKNOWN MERCHANT,30.00,Uncategorised,45.0,false,Shopping (60%)
```

## Configuration Parameters Explained

### `match_threshold` (Default: 70)
- Minimum score required for automatic categorization
- Higher values = more strict matching
- Lower values = more lenient matching

### `auto_approve_threshold` (Default: 80)
- Score threshold for automatic approval without manual review
- Transactions above this score are marked as `Auto_Approved: true`

### `num_suggestions` (Default: 3)
- Number of alternative category suggestions for unmatched transactions
- Helps with manual categorization of difficult cases

## Tips for Better Results

### 1. Create Comprehensive Rules
```csv
Description,Category
tesco,Groceries
sainsbury,Groceries
shell,Transport
bp,Transport
exxon,Transport
amazon,Shopping
ebay,Shopping
```

### 2. Use Broad Patterns
Instead of exact matches, use key identifying words:
- ✅ "shell" matches "SHELL PETROL STATION 1234"
- ❌ "shell petrol station 1234" only matches exact text

### 3. Handle Common Variations
```csv
Description,Category
mcdonalds,Food & Drink
mcdonald,Food & Drink
mcd,Food & Drink
```

### 4. Regular Maintenance
- Review uncategorized transactions periodically
- Add new rules based on unmatched patterns
- Update existing rules for better coverage

## Troubleshooting

### Common Issues

**File Not Found Error**
```
FileNotFoundError: Rules file not found
```
- Check file paths in the configuration
- Ensure files exist in the specified locations
- Use absolute paths if relative paths don't work

**Empty Results**
```
ValueError: Rules file is empty
```
- Verify your rules.csv has content
- Check for proper CSV formatting
- Ensure Description and Category columns exist

**Low Match Rates**
- Lower the `match_threshold` value
- Review and expand your rules file
- Check transaction description patterns

**Performance Issues**
- Reduce `cache_size` if memory is limited
- Increase `chunk_size` for large datasets
- Consider breaking large files into smaller batches

### Debugging

Enable detailed logging by checking the generated `categoriser.log` file:
```
2024-01-01 10:00:00 - INFO - Loading rules from rules.csv
2024-01-01 10:00:01 - INFO - Successfully loaded 150 rules
2024-01-01 10:00:02 - INFO - Processing 1000 transactions
```

## Advanced Usage

### Custom Cleaning Functions
The tool includes advanced text preprocessing:
- Removes common financial terms (ref, payment, purchase)
- Strips card numbers and reference codes
- Normalizes spacing and capitalization

### Scoring Algorithm
Uses a hybrid approach:
- 60% Token Set Ratio (handles word order variations)
- 40% Partial Ratio (finds substring matches)

## Performance Benchmarks

Typical performance on a standard laptop:
- **Small datasets** (< 1,000 transactions): < 5 seconds
- **Medium datasets** (1,000 - 10,000 transactions): 10-30 seconds
- **Large datasets** (> 10,000 transactions): 1-5 minutes

## Contributing

To improve the categoriser:
1. Test with your own transaction data
2. Suggest improvements to matching algorithms
3. Report bugs or edge cases
4. Share effective rule patterns

## License

This project is available under the MIT License.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the generated log files
3. Ensure your input files match the required format
4. Test with a small sample dataset first

---

**Happy Categorizing! 🏦📊**