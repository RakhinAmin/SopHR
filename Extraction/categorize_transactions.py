"""
semantic_categoriser.py
----------------------

• Loads a bank-statement Excel file.
• Uses SBERT embeddings to match each Description to the closest Category
  (from the Categories sheet) via cosine similarity.
• Falls back to 'Uncategorised' when no label exceeds a configurable threshold.
"""

import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import logging
from functools import lru_cache
from pathlib import Path

# ───────────────────────────  CONFIG  ────────────────────────────
MODEL_NAME   = "all-MiniLM-L6-v2"
BATCH_SIZE   = 32
THRESHOLD    = 0.70          # min cosine similarity to accept a label
INPUT_FILE   = "bank_statement.xlsx"
DATA_SHEET   = "Transactions"  # rename to your sheet tab
CAT_SHEET    = "Categories"
OUTPUT_FILE  = "auto_categorized_semantic.xlsx"
# ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
)

# ─────────────────────────  UTILITIES  ──────────────────────────
@lru_cache(maxsize=1)
def load_model(name: str = MODEL_NAME) -> SentenceTransformer:
    logging.info("Loading SBERT model…")
    return SentenceTransformer(name, device="cpu")        # switch to cuda if available

def load_data(file_path: str,
              data_sheet: str = DATA_SHEET,
              cat_sheet: str = CAT_SHEET):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file '{file_path}' not found.")

    with pd.ExcelFile(path) as xls:
        logging.info("Sheets found: %s", ", ".join(xls.sheet_names))
        df            = xls.parse(data_sheet)
        categories_df = xls.parse(cat_sheet)

    # basic validation
    if "Description" not in df.columns:
        raise ValueError("Data sheet must contain a 'Description' column.")
    if "Category" not in categories_df.columns:
        raise ValueError("Categories sheet must contain a 'Category' column.")

    df["Description"] = df["Description"].fillna("").astype(str).str.strip()
    categories_df["Category"] = (
        categories_df["Category"].fillna("").astype(str).str.strip()
    )
    category_labels = categories_df["Category"].drop_duplicates().tolist()
    if not category_labels:
        raise ValueError("No categories provided in the Categories sheet.")

    return df, category_labels

def semantic_match(descriptions, category_labels, model, threshold=THRESHOLD):
    """Return best category & similarity for each description."""
    logging.info("Encoding %d descriptions…", len(descriptions))
    desc_vecs = model.encode(descriptions, batch_size=BATCH_SIZE, show_progress_bar=True)

    logging.info("Encoding %d category labels…", len(category_labels))
    cat_vecs  = model.encode(category_labels, batch_size=BATCH_SIZE, show_progress_bar=True)

    sims      = cosine_similarity(desc_vecs, cat_vecs)          # shape: [n_txn, n_cat]
    best_idx  = np.argmax(sims, axis=1)
    best_sim  = sims[np.arange(len(descriptions)), best_idx]

    chosen    = [
        category_labels[i] if sim >= threshold else "Uncategorised"
        for i, sim in zip(best_idx, best_sim)
    ]
    return chosen, best_sim

def categorise_file():
    # Load
    df, category_labels = load_data(INPUT_FILE)

    # Model + semantic k-NN
    model = load_model()
    df["Category"], df["Similarity"] = semantic_match(
        df["Description"].tolist(),
        category_labels,
        model,
        threshold=THRESHOLD,
    )

    # Save
    try:
        df.to_excel(OUTPUT_FILE, index=False)
        logging.info("✅ Categorised file written to '%s'", OUTPUT_FILE)
    except PermissionError:
        logging.error("Cannot write to '%s' (permission denied).", OUTPUT_FILE)

# ──────────────────────────────  MAIN  ──────────────────────────
if __name__ == "__main__":
    categorise_file()
