import streamlit as st
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Static password
ADMIN_PASSWORD =st.secrets["WEB_PASS"]

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
        <h1 style="text-align: center; margin-bottom: 2rem;font-family: "Times New Roman">Akhand Data</h1>
            <h2 style="text-align: center; margin-bottom: 2rem;">🔐 প্রবেশ করুন</h2>
        </div>
    """, unsafe_allow_html=True)

    password = st.text_input("পাসওয়ার্ড", type="password")

    if st.button("প্রবেশ করুন", type="primary"):
        if password == ADMIN_PASSWORD:
            st.session_state.authenticated = True
            st.success("সফলভাবে প্রবেশ করা হয়েছে!")
            st.rerun()
        else:
            st.error("ভুল পাসওয়ার্ড")
            logger.warning("Failed login attempt")

    return st.session_state.authenticated

def logout():
    """Handle logout"""
    if st.session_state.authenticated:
        st.session_state.authenticated = False
        logger.info("User logged out successfully")
