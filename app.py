import streamlit as st
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import requests
from urllib.parse import urlparse, parse_qs
from google.auth.transport.requests import Request
from supabase import create_client
from datetime import datetime, timezone
import time
import json
import threading

# Page configuration
st.set_page_config(
    page_title="Gmail Automation",
    page_icon="✉️",
    layout="wide"
)

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = "Home"
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'credentials' not in st.session_state:
    st.session_state.credentials = None
if 'oauth_state' not in st.session_state:
    st.session_state.oauth_state = None

# Gmail API scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/'
]

# API configurations
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Initialize Supabase
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

def get_redirect_uri():
    """Get the appropriate redirect URI based on the environment"""
    if 'STREAMLIT_SHARING_MODE' in os.environ:
        return st.secrets.get("GOOGLE_REDIRECT_URI", "https://gmail-automation-streamlit.streamlit.app")
    return "http://localhost:8501"

def initialize_oauth_flow():
    """Initialize OAuth flow and generate authorization URL"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uri": get_redirect_uri()
            }
        },
        scopes=GMAIL_SCOPES
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    
    st.session_state.oauth_state = state
    return authorization_url

def handle_oauth_callback():
    """Handle the OAuth callback and token exchange"""
    try:
        code = st.experimental_get_query_params().get("code", [None])[0]
        state = st.experimental_get_query_params().get("state", [None])[0]
        
        if code and state and state == st.session_state.oauth_state:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": st.secrets["GOOGLE_CLIENT_ID"],
                        "client_secret": st.secrets["GOOGLE_CLIENT_SECRET"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uri": get_redirect_uri()
                    }
                },
                scopes=GMAIL_SCOPES
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            st.session_state.credentials = credentials
            st.session_state.authenticated = True
            
            # Clear URL parameters
            st.experimental_set_query_params()
            st.success("Successfully authenticated with Gmail!")
            return True
            
    except Exception as e:
        st.error(f"Error during authentication: {str(e)}")
        st.session_state.authenticated = False
        return False

def create_email_message(sender, to, subject, message_text):
    """Create email message"""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}

def send_email(service, message):
    """Send email using Gmail API"""
    try:
        message = service.users().messages().send(userId="me", body=message).execute()
        return message
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return None

def generate_ai_response(email_content, subject, knowledge_context):
    """Generate AI response using Groq API"""
    try:
        prompt = f"""You are an AI email assistant. Generate a brief, professional response to this email using the company's knowledge base information.
        
Subject: {subject}

Email Content:
{email_content}

Company Knowledge Base Context:
{knowledge_context}

Generate a response that is:
1. Brief and to the point (2-3 sentences maximum)
2. Aligned with the company's knowledge base information
3. Professional and courteous
4. Generic enough to be an automatic reply

Response:"""

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an AI email assistant. Generate professional and contextually appropriate email responses."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 300,
            "top_p": 1
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data['choices'][0]['message']['content']
        
        st.error(f"Error generating response: {response.text}")
        return None
            
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return None

def get_knowledge_base_context(email_content):
    """Get relevant knowledge base entries"""
    try:
        response = supabase.table('knowledge_base').select('*').execute()
        if response.data:
            # Simple keyword matching for now
            relevant_entries = [
                entry['content'] for entry in response.data
                if any(keyword.lower() in email_content.lower() 
                      for keyword in entry.get('keywords', []))
            ]
            return "\n".join(relevant_entries)
        return ""
    except Exception as e:
        st.error(f"Error accessing knowledge base: {str(e)}")
        return ""

def compose_email_page():
    """Compose Email Page"""
    st.header("Compose Email")
    
    if not st.session_state.authenticated:
        st.warning("Please authenticate with Gmail first.")
        return
    
    with st.form("email_form"):
        to_email = st.text_input("To:")
        subject = st.text_input("Subject:")
        message = st.text_area("Message:")
        
        col1, col2 = st.columns([1, 5])
        with col1:
            submitted = st.form_submit_button("Send")
        
        if submitted and to_email and subject and message:
            try:
                credentials = st.session_state.credentials
                service = build('gmail', 'v1', credentials=credentials)
                
                email_message = create_email_message(
                    sender="me",
                    to=to_email,
                    subject=subject,
                    message_text=message
                )
                
                if send_email(service, email_message):
                    st.success("Email sent successfully!")
                else:
                    st.error("Failed to send email.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

def main():
    """Main application"""
    st.title("Gmail Automation with AI")
    
    # Sidebar navigation
    with st.sidebar:
        st.title("Navigation")
        if st.session_state.authenticated:
            selected = st.radio(
                "Go to",
                ["Home", "Compose Email", "Auto Reply", "Settings"]
            )
            st.session_state.page = selected
            
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.credentials = None
                st.experimental_rerun()
        else:
            selected = "Home"
            st.session_state.page = selected
    
    # Handle OAuth flow
    if not st.session_state.authenticated:
        auth_url = initialize_oauth_flow()
        st.write("Please authenticate with Gmail to continue:")
        st.markdown(f"[Authenticate with Gmail]({auth_url})")
    
    # Check for OAuth callback
    if not st.session_state.authenticated:
        handle_oauth_callback()
    
    # Display selected page
    if st.session_state.page == "Compose Email":
        compose_email_page()
    elif st.session_state.page == "Auto Reply":
        st.header("Auto Reply")
        st.write("Auto reply feature coming soon!")
    elif st.session_state.page == "Settings":
        st.header("Settings")
        st.write("Settings page coming soon!")
    else:  # Home page
        st.header("Welcome to Gmail Automation")
        st.write("""
        This application helps you manage your emails with AI-powered features:
        - Compose and send emails
        - Auto-reply to emails (coming soon)
        - Email templates (coming soon)
        - Knowledge base integration (coming soon)
        """)

if __name__ == "__main__":
    main()
