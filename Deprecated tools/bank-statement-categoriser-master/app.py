import streamlit as st
import pandas as pd
import os
import chardet  # Add this for encoding detection
from main import Train, Categorise

st.set_page_config(page_title="Bank Categorizer", layout="centered")
st.title("🏦 Bank Statement Categorizer")

mode = st.radio("Choose an action:", ["Train a Model", "Categorise Transactions"])

uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])

def save_and_detect_encoding(uploaded_file):
    temp_path = os.path.join("uploads", uploaded_file.name)
    os.makedirs("uploads", exist_ok=True)

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    with open(temp_path, "rb") as f:
        encoding = chardet.detect(f.read())['encoding'] or 'utf-8'

    return temp_path, encoding

if uploaded_file:
    temp_path, detected_encoding = save_and_detect_encoding(uploaded_file)

    # Display the encoding to the user
    st.info(f"Detected Encoding: `{detected_encoding}`")

    if mode == "Train a Model":
        if st.button("Train"):
            try:
                Train(temp_path)
                st.success("✅ Model trained successfully.")
            except Exception as e:
                st.error(f"❌ Training failed: {e}")

    elif mode == "Categorise Transactions":
        if st.button("Categorise"):
            try:
                Categorise(temp_path)
                st.success("✅ Categorization complete.")
                result_path = "data/test_results.csv"
                if os.path.exists(result_path):
                    df = pd.read_csv(result_path)
                    st.dataframe(df.head(30))
                    st.download_button("Download Results", data=df.to_csv(index=False), file_name="categorized.csv")
                else:
                    st.warning("No results file found.")
            except Exception as e:
                st.error(f"❌ Categorization failed: {e}")
