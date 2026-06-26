import streamlit as st

def login_page():
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username and password:
            st.success("Login successful (demo only)")
            st.session_state["logged_in"] = True
        else:
            st.error("Please fill in all fields")