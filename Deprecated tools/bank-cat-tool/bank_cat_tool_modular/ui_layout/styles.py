# === ui_layout/styles.py ===
import streamlit as st

def apply_custom_styles():
    st.markdown("""
    <style>
    label > div:first-child {
        display: flex;
        align-items: center;
        gap: 4px !important;
    }
    svg[data-testid="icon-help"] {
        width: 14px !important;
        height: 14px !important;
        margin-left: 2px !important;
        margin-top: 0 !important;
    }
    [data-testid="stTextInput"] {
        margin-bottom: 1rem;
    }
    .block-container .stTextInput {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }
    div[data-testid="stTextInput"] {
        margin-top: -6px !important;
        margin-bottom: 10px !important;
    }
    button:hover {
        background-color: #d4af37 !important;
        color: white !important;
        border: none !important;
        transition: background-color 0.3s ease;
    }
    </style>
    """, unsafe_allow_html=True)
