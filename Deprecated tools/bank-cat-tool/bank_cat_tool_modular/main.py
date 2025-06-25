import streamlit as st
from ui.routes import route_page
from ui_layout.styles import apply_custom_styles

st.set_page_config(page_title="Transaction Categorisation Tool", layout="wide")
apply_custom_styles()
route_page()
