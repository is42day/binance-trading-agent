import streamlit as st
from streamlit_option_menu import option_menu

st.set_page_config(layout="wide")

selected = option_menu(
    menu_title=None,
    options=["Home", "About", "Contact"],
    icons=["🏠", "ℹ️", "📧"],
    default_index=0,
    orientation="horizontal",
)

if selected == "Home":
    st.write("# 🏠 Home Page")
    st.write("This is the home page!")
elif selected == "About":
    st.write("# ℹ️ About Page")
    st.write("This is the about page!")
else:
    st.write("# 📧 Contact Page")
    st.write("This is the contact page!")
