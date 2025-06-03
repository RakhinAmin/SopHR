#!/usr/bin/env python3
"""
Accepts CSV and Excel inputs.
"""

import argparse, logging, re
from pathlib import Path
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from functools import lru_cache

# ────────────────── config ──────────────────
MODEL_NAME   = "sentence-transformers/all-mpnet-base-v2"
BATCH_SIZE   = 32
THRESHOLD    = 0.75
# ────────────────────────────────────────────

# ---------- SBERT loader ----------
@lru_cache(maxsize=1)
def load_model() -> SentenceTransformer:
    device = "cuda" if SentenceTransformer(MODEL_NAME).device.type == "cuda" else "cpu"
    logging.info("Loading SBERT (%s) on %s", MODEL_NAME, device.upper())
    return SentenceTransformer(MODEL_NAME, device=device)

# ---------- IO helpers ----------
EXCEL_SUFX = {".xls", ".xlsx", ".xlsm", ".xlsb"}

def read_statement(path: Path, sheet: str | None):
    if path.suffix.lower() in EXCEL_SUFX:
        return pd.read_excel(path, sheet_name=sheet)
    if path.suffix.lower() == ".csv":
        if sheet:
            logging.warning("Ignoring --data-sheet for CSV input.")
        return pd.read_csv(path)
    raise ValueError("Unsupported statement file type.")

def read_categories(path: Path, sheet: str | None):
    if path.suffix.lower() in EXCEL_SUFX:
        return pd.read_excel(path, sheet_name=sheet or "Categories")
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError("Unsupported categories file type.")

# ---------- semantic matcher ----------
def semantic_match(descs, cat_labels, model, threshold):
    desc_vecs = model.encode(descs, batch_size=BATCH_SIZE, show_progress_bar=True)
    cat_vecs  = model.encode(cat_labels, batch_size=BATCH_SIZE, show_progress_bar=False)

    sims      = cosine_similarity(desc_vecs, cat_vecs)
    idx       = np.argmax(sims, axis=1)
    best_sim  = sims[np.arange(len(descs)), idx]

    chosen = [cat_labels[i] if s >= threshold else "Uncategorised"
              for i, s in zip(idx, best_sim)]
    return chosen, best_sim

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--statement", required=True,
                    help="Bank statement file (.csv, .xls[x/m/b])")
    ap.add_argument("--data-sheet", default=None,
                    help="Sheet name for the statement (Excel only)")
    ap.add_argument("--cat-file",   default=None,
                    help="Separate file holding categories list (CSV/Excel). "
                         "If omitted, script looks for a 'Categories' sheet in the statement workbook.")
    ap.add_argument("--cat-sheet",  default="Categories",
                    help="Sheet name for the categories list when --cat-file is Excel")
    ap.add_argument("--output",     default="auto_categorised.xlsx")
    ap.add_argument("--threshold",  type=float, default=THRESHOLD)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s  %(levelname)s  %(message)s")

    st_path  = Path(args.statement)
    cat_path = Path(args.cat_file) if args.cat_file else None

    # 1️ Load data
    df = read_statement(st_path, args.data_sheet)
    if "Description" not in df.columns:
        raise ValueError("Statement must contain a 'Description' column.")

    if cat_path:
        cat_df = read_categories(cat_path, args.cat_sheet)
    else:
        if st_path.suffix.lower() not in EXCEL_SUFX:
            raise ValueError("For CSV statements you must supply --cat-file.")
        cat_df = read_categories(st_path, args.cat_sheet)

    if "Category" not in cat_df.columns:
        raise ValueError("Categories file/sheet must contain a 'Category' column.")
    categories = cat_df["Category"].dropna().astype(str).str.strip().tolist()
    if not categories:
        raise ValueError("No categories provided.")

    df["Description"] = df["Description"].fillna("").astype(str).str.strip()

    # 2️ SBERT + cosine match
    model = load_model()
    df["Category"], df["Similarity"] = semantic_match(
        df["Description"].tolist(),
        categories,
        model,
        args.threshold
    )

    # 3️ Save (always writes Excel so both sheets can live together)
    with pd.ExcelWriter(args.output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Categorised_Data", index=False)
        pd.DataFrame({"Category": categories}).to_excel(
            writer, sheet_name="Categories", index=False)

    logging.info("Written %s", args.output)


if __name__ == "__main__":
    main()
