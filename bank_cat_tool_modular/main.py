import streamlit as st
from ui.routes import route_page
from ui_layout.styles import apply_custom_styles

st.set_page_config(page_title="BA Tool", layout="wide")

st.markdown("""
    <style>
      /* Remove the big top padding Streamlit adds by default */
      .block-container {
        padding-top: 0.5rem !important;
      }
      /* And if you need absolutely none: */
      /* .block-container { padding-top: 0 !important; } */
    </style>
""", unsafe_allow_html=True)


apply_custom_styles()
route_page()
