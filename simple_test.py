import streamlit as st

st.title("Simple Test App")
st.write("If you can see this, Streamlit is working!")

name = st.text_input("Enter your name")
if name:
    st.write(f"Hello, {name}!")
