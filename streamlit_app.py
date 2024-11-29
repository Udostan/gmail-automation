import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import traceback

# Force the port to be 8501
os.environ['PORT'] = '8501'

# Basic page configuration
st.set_page_config(
    page_title="Gmail Automation",
    layout="wide",
    initial_sidebar_state="collapsed"
)

try:
    # Verify secrets first
    required_secrets = [
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "OAUTH_REDIRECT_URI"
    ]
    
    missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
    if missing_secrets:
        st.error(f"Missing required secrets: {', '.join(missing_secrets)}")
        st.stop()
        
    # OAuth 2.0 configuration
    CLIENT_CONFIG = {
        "web": {
            "client_id": st.secrets["GOOGLE_CLIENT_ID"],
            "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets["OAUTH_REDIRECT_URI"]],
        }
    }
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
    
    # Initialize session state
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None
    
    # Main app
    st.title("Gmail Automation")
    
    if not st.session_state.credentials:
        st.write("Please login with your Google account to get started")
        if st.button("Login with Google"):
            flow = Flow.from_client_config(
                CLIENT_CONFIG,
                scopes=SCOPES,
                redirect_uri=st.secrets["OAUTH_REDIRECT_URI"]
            )
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true'
            )
            st.markdown(f'[Click here to authorize]({authorization_url})')
    else:
        st.success("Successfully logged in!")
        st.write("You can now use the Gmail Automation features")
        
        if st.button("Logout"):
            st.session_state.credentials = None
            st.experimental_rerun()

except Exception as e:
    st.error("An error occurred during initialization:")
    st.error(str(e))
    st.code(traceback.format_exc())