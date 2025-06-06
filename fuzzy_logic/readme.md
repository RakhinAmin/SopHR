# 🧾 Transaction Categorizer

A powerful Python script that automatically categorizes bank transactions using fuzzy matching against a rulebook. Ideal for accountants, finance teams, and auditors needing quick and accurate classification of bank statement data.

---

## 📌 Features

- ✅ Rule-based categorization with fuzzy matching
- 🚀 Hybrid scoring using RapidFuzz's `token_set_ratio` and `partial_ratio`
- 🔍 Auto-approval for high-confidence matches
- 🧹 Advanced text cleaning tailored for financial descriptions
- 💡 Up to 3 category suggestions for uncategorized transactions
- 🧠 LRU cache for performance boosts
- 📊 Summary report generation
- 📁 Output saved to CSV with full match metadata
- 🧾 Logging to both console and file (`categorizer.log`)

---

## 🧠 How It Works

1. **Input**
   - A bank statement CSV file with at least a `Description` column.
   - A rules CSV with two columns: `Description` and `Category`.

2. **Processing**
   - Descriptions are cleaned using custom regex rules.
   - Matches are looked up from a rule map; if not found, fuzzy matching is applied.
   - The best match, confidence score, and top suggestions are recorded.
   - Auto-approval is applied for high-confidence matches.

3. **Output**
   - A categorized CSV (`categorised_output.csv`)
   - Log of progress in `categorizer.log`
   - Summary stats printed to console

---

## 🛠 Requirements

- Python 3.8+
- pandas
- rapidfuzz

```bash
pip install pandas rapidfuzz
````

---

## 📂 File Structure

```text
├── categorizer.py           # Main script
├── bank_statement_test.csv  # Input file with bank transactions
├── improved_rules.csv       # Categorization rulebook
├── categorised_output.csv   # Output file with matched results
├── categorizer.log          # Runtime logs
```

---

## 🔧 Configuration

Modify the `Config` class to change file paths, thresholds, and suggestion limits:

```python
@dataclass
class Config:
    bank_statement_file: str = "path/to/bank_statement.csv"
    rules_file: str = "path/to/rules.csv"
    output_file: str = "categorised_output.csv"
    match_threshold: int = 90
    num_suggestions: int = 3
    auto_approve_threshold: int = 95
    chunk_size: int = 1000
    cache_size: int = 1000
```

---

## 🚀 Running the Script

Simply run:

```bash
python categorizer.py
```

Exit code `0` indicates success, `1` indicates failure.

---

## 📊 Sample Output Columns

| Description       | Category      | Match\_Score | Matched\_Rule | Auto\_Approved | Suggestion\_1  | Suggestion\_2  | Suggestion\_3 |
| ----------------- | ------------- | ------------ | ------------- | -------------- | -------------- | -------------- | ------------- |
| "TESCO STORE 123" | Groceries     | 96.0         | "tesco store" | True           |                |                |               |
| "XZY INC PAYROLL" | Uncategorized | 72.5         | "xyz payroll" | False          | Salary (72.5%) | Income (66.4%) | Misc (55.2%)  |

---

## 📈 Example Report

```
=== CATEGORIZATION REPORT ===
Total Transactions: 5000
Categorised: 4682
Uncategorised: 318
Categorisation Rate: 93.64%
Auto Approved: 4521
Avg Confidence: 91.82
High Confidence Matches: 4673
```

---

## 🧠 Limitations

* Only works with CSV input
* Matching relies heavily on clean, consistent rule descriptions
* May struggle with abbreviations or non-standard input without rule tuning

---

## 📄 License

MIT License

---

## 👤 Author

Created by \Ali Ladak — feel free to use, adapt, or extend this script as needed.

