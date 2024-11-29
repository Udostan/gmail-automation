import streamlit as st
import os

# Configure Streamlit page
st.set_page_config(
    page_title="Gmail Automation Test",
    page_icon="✉️",
    layout="wide"
)

# Basic test content
st.title("Gmail Automation Test")
st.write("If you can see this, Streamlit is working correctly!")

# Add a simple button
if st.button("Click me!"):
    st.success("Button clicked!")
