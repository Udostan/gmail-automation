import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import traceback
from urllib.parse import urlparse, parse_qs

# Force the port to be 8501
os.environ['PORT'] = '8501'
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Basic page configuration
st.set_page_config(
    page_title="Gmail Automation",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Debug information
st.sidebar.write("Debug Information:")
st.sidebar.write("Current URL Parameters:", st.experimental_get_query_params())

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
    
    # Show configured redirect URI
    st.sidebar.write("Configured Redirect URI:", st.secrets["OAUTH_REDIRECT_URI"])
        
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
    if 'flow' not in st.session_state:
        st.session_state.flow = None
    
    # Show session state
    st.sidebar.write("Session State:")
    st.sidebar.write("Has Credentials:", st.session_state.credentials is not None)
    st.sidebar.write("Has Flow:", st.session_state.flow is not None)
    
    # Main app
    st.title("Gmail Automation")
    
    # Check if we're in the OAuth callback
    query_params = st.experimental_get_query_params()
    if "code" in query_params:
        st.sidebar.write("Received OAuth Code")
        try:
            if st.session_state.flow:
                st.sidebar.write("Processing OAuth Callback")
                # Exchange code for credentials
                st.session_state.flow.fetch_token(code=query_params["code"][0])
                st.session_state.credentials = st.session_state.flow.credentials
                st.session_state.flow = None
                st.experimental_set_query_params()
                st.rerun()
            else:
                st.sidebar.error("No flow found in session state during callback")
        except Exception as e:
            st.sidebar.error(f"OAuth Callback Error: {str(e)}")
            st.error(f"Error during OAuth callback: {str(e)}")
            st.code(traceback.format_exc())
            st.session_state.flow = None
            st.session_state.credentials = None
    
    if not st.session_state.credentials:
        st.write("Please login with your Google account to get started")
        if st.button("Login with Google"):
            try:
                st.sidebar.write("Initiating OAuth Flow")
                flow = Flow.from_client_config(
                    CLIENT_CONFIG,
                    scopes=SCOPES,
                    redirect_uri=st.secrets["OAUTH_REDIRECT_URI"]
                )
                st.session_state.flow = flow
                authorization_url, _ = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true'
                )
                st.sidebar.write("Generated Auth URL")
                st.markdown(f'[Click here to authorize with Google]({authorization_url})')
            except Exception as e:
                st.sidebar.error(f"OAuth Flow Error: {str(e)}")
                st.error(f"Error initiating OAuth flow: {str(e)}")
                st.code(traceback.format_exc())
    else:
        try:
            # Test the credentials by getting user info
            service = build('gmail', 'v1', credentials=st.session_state.credentials)
            user_info = service.users().getProfile(userId='me').execute()
            st.success(f"Successfully logged in as: {user_info['emailAddress']}")
            
            if st.button("Logout"):
                st.session_state.credentials = None
                st.session_state.flow = None
                st.rerun()
                
        except Exception as e:
            st.sidebar.error(f"Gmail API Error: {str(e)}")
            st.error("Error accessing Gmail API. Please try logging in again.")
            st.code(traceback.format_exc())
            st.session_state.credentials = None
            st.rerun()

except Exception as e:
    st.error("An error occurred during initialization:")
    st.error(str(e))
    st.code(traceback.format_exc())