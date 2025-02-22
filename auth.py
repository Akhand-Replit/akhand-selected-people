import streamlit as st
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_auth():
    """Initialize authentication in session state"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

def login_form():
    """Display login form and handle authentication"""
    if st.session_state.authenticated:
        return True

    st.markdown("""
        <div style="background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
        <h1 style="text-align: center; margin-bottom: 2rem;">Data Management System</h1>
            <h2 style="text-align: center; margin-bottom: 2rem;">🔐 Login Required</h2>
        </div>
    """, unsafe_allow_html=True)

    password = st.text_input("Password", type="password")

    if st.button("Login", type="primary"):
        if password == st.secrets["WEB_PASS"]:
            st.session_state.authenticated = True
            st.success("Successfully logged in!")
            st.rerun()
        else:
            st.error("Incorrect password")
            logger.warning("Failed login attempt")

    return st.session_state.authenticated

def logout():
    """Handle logout"""
    if st.session_state.authenticated:
        st.session_state.authenticated = False
        logger.info("User logged out successfully")
