import sys
import traceback
import streamlit as st

try:
    # Basic page configuration
    st.set_page_config(page_title="Gmail Automation Test", layout="wide")
    
    # Display version information
    st.write(f"Python version: {sys.version}")
    st.write(f"Streamlit version: {st.__version__}")
    
    # Basic content
    st.title("Gmail Automation")
    st.write("Basic test page")
    
except Exception as e:
    st.write("Error during initialization:")
    st.error(str(e))
    st.code(traceback.format_exc())