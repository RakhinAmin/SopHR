# app.py  – Streamlit UI for semantic_categoriser.py
import streamlit as st
import pandas as pd
from pathlib import Path
import tempfile

# ───── backend helpers ─────
from categorize_transactions import (
    load_model,
    read_statement,
    read_categories,
    semantic_match,
    THRESHOLD as DEFAULT_THRESHOLD,
)

# cache model (only loads once per session)
model = load_model()

st.set_page_config(page_title="Semantic Categoriser", layout="wide")
st.title("📊 Semantic Bank-Statement Categoriser")

# ─────────────────────────  File inputs  ─────────────────────────
st.markdown("### 1️⃣  Upload your statement file")
statement_file = st.file_uploader(
    "Accepted formats: CSV, XLS, XLSX, XLSM, XLSB",
    type=["csv", "xls", "xlsx", "xlsm", "xlsb"],
)

st.markdown("### 2️⃣  (Optional) Upload a categories file")
cat_file = st.file_uploader(
    "If omitted, the app will look for a **'Categories'** sheet inside the statement workbook.",
    type=["csv", "xls", "xlsx", "xlsm", "xlsb"],
)

# sheet pickers (shown only for Excel uploads)
data_sheet = None
cat_sheet  = "Categories"

if statement_file and statement_file.type != "text/csv":
    with pd.ExcelFile(statement_file) as xls:
        sheet_names = xls.sheet_names
    data_sheet = st.selectbox("Select statement sheet", sheet_names)
    statement_file.seek(0)              # ★ rewind after peek

if cat_file and cat_file.type != "text/csv":
    with pd.ExcelFile(cat_file) as xls:
        cat_sheet = st.selectbox(
            "Select categories sheet",
            xls.sheet_names,
            index=xls.sheet_names.index("Categories")
            if "Categories" in xls.sheet_names else 0,
        )
    cat_file.seek(0)                    # ★ rewind after peek

threshold = st.slider(
    "Similarity threshold (higher → fewer but safer matches)",
    0.0, 1.0, float(DEFAULT_THRESHOLD), 0.01,
)

# ─────────────────────────  Process  ─────────────────────────
if st.button("🚀 Categorise") and statement_file:
    try:
        # 1  materialise uploads to temp files
        with tempfile.NamedTemporaryFile(delete=False,
                                         suffix=Path(statement_file.name).suffix) as tmp:
            tmp.write(statement_file.read())
            stmt_path = Path(tmp.name)

        cat_path = None
        if cat_file:
            with tempfile.NamedTemporaryFile(delete=False,
                                             suffix=Path(cat_file.name).suffix) as tmp:
                tmp.write(cat_file.read())
                cat_path = Path(tmp.name)

        # 2  load dataframes
        df = read_statement(stmt_path, data_sheet)
        cat_df = (
            read_categories(cat_path, cat_sheet)
            if cat_path
            else read_categories(stmt_path, cat_sheet)
        )

        categories = cat_df["Category"].dropna().astype(str).str.strip().tolist()
        if "Description" not in df.columns or not categories:
            st.error("Statement must contain **Description** column and Categories list cannot be empty.")
            st.stop()

        # 3  run model
        with st.spinner("Embedding & matching…"):
            df["Category"], df["Similarity"] = semantic_match(
                df["Description"].fillna("").astype(str).tolist(),
                categories,
                model,
                threshold,
            )

        # 4  show summary + preview
        st.success("Done!")
        st.caption(
            f"Mean sim = {df['Similarity'].mean():.3f} • "
            f"Uncategorised = {(df['Category']=='Uncategorised').sum()} /"
            f"{len(df)} rows"
        )
        st.dataframe(df.head(30), use_container_width=True)

        # 5  save to a temp Excel
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_out:
            out_path = Path(tmp_out.name)
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Categorised_Data", index=False)
            pd.DataFrame({"Category": categories}).to_excel(
                writer, sheet_name="Categories", index=False
            )

        # 6  download button
        with open(out_path, "rb") as f:
            st.download_button(
                "📥 Download categorised file",
                data=f.read(),
                file_name="auto_categorised.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    except Exception as e:
        st.error(f"❌ {e}")
