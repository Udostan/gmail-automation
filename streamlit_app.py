import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import requests
from datetime import datetime
import base64
from supabase import create_client
import PyPDF2
import pandas as pd

# Page configuration
st.set_page_config(page_title="Gmail Automation", layout="wide")

# Initialize session state
if 'credentials' not in st.session_state:
    st.session_state.credentials = None

# Supabase configuration
supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

# Groq API configuration
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# OAuth 2.0 configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CLIENT_SECRETS_FILE = "credentials.json"

def main():
    st.title("Gmail Automation")
    
    # Sidebar
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("Go to", ["Home", "Email Templates", "Knowledge Base", "Settings"])

    if not st.session_state.credentials:
        st.write("Please login with your Google account to get started")
        if st.button("Login with Google"):
            handle_auth()
    else:
        if page == "Home":
            show_home_page()
        elif page == "Email Templates":
            show_templates_page()
        elif page == "Knowledge Base":
            show_knowledge_base_page()
        elif page == "Settings":
            show_settings_page()

def handle_auth():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=st.secrets["OAUTH_REDIRECT_URI"]
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    st.markdown(f'[Authorize with Google]({authorization_url})')

def create_message(sender, to, subject, message_text):
    from email.mime.text import MIMEText
    message = MIMEText(message_text)
    message['to'] = ', '.join(to) if isinstance(to, list) else to
    message['from'] = sender
    message['subject'] = subject
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}

def show_home_page():
    st.header("Dashboard")
    
    # Email composition
    with st.expander("Compose Email"):
        to = st.text_input("To (separate multiple emails with commas)")
        subject = st.text_input("Subject")
        message = st.text_area("Message")
        
        if st.button("Send Email"):
            try:
                credentials = Credentials(**st.session_state.credentials)
                service = build('gmail', 'v1', credentials=credentials)
                
                email_msg = create_message(
                    'me',
                    [email.strip() for email in to.split(',')],
                    subject,
                    message
                )
                
                service.users().messages().send(userId='me', body=email_msg).execute()
                st.success("Email sent successfully!")
            except Exception as e:
                st.error(f"Error sending email: {str(e)}")
    
    # Recent emails
    with st.expander("Recent Emails"):
        if st.button("Refresh Emails"):
            try:
                credentials = Credentials(**st.session_state.credentials)
                service = build('gmail', 'v1', credentials=credentials)
                
                results = service.users().messages().list(userId='me', maxResults=10).execute()
                messages = results.get('messages', [])
                
                for msg in messages:
                    email = service.users().messages().get(userId='me', id=msg['id']).execute()
                    headers = email['payload']['headers']
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                    st.write(f"From: {sender}")
                    st.write(f"Subject: {subject}")
                    st.divider()
            except Exception as e:
                st.error(f"Error loading emails: {str(e)}")

def show_templates_page():
    st.header("Email Templates")
    
    # Template creation
    with st.expander("Create New Template"):
        name = st.text_input("Template Name")
        subject = st.text_input("Subject Template")
        body = st.text_area("Body Template")
        
        if st.button("Save Template"):
            try:
                data = supabase.table('email_templates').insert({
                    "name": name,
                    "subject": subject,
                    "body": body
                }).execute()
                st.success("Template saved successfully!")
            except Exception as e:
                st.error(f"Error saving template: {str(e)}")
    
    # Display existing templates
    with st.expander("View Templates"):
        if st.button("Refresh Templates"):
            try:
                response = supabase.table('email_templates').select("*").execute()
                templates = response.data
                
                for template in templates:
                    st.subheader(template['name'])
                    st.write(f"Subject: {template['subject']}")
                    st.text_area("Body", template['body'], key=f"template_{template['id']}", disabled=True)
                    st.divider()
            except Exception as e:
                st.error(f"Error loading templates: {str(e)}")

def show_knowledge_base_page():
    st.header("Knowledge Base")
    
    # Text input
    with st.expander("Add Text"):
        text = st.text_area("Enter text to add to knowledge base")
        if st.button("Add Text"):
            try:
                data = supabase.table('knowledge_base').insert({
                    "content": text,
                    "source": "text_input"
                }).execute()
                st.success("Text added to knowledge base!")
            except Exception as e:
                st.error(f"Error adding text: {str(e)}")
    
    # File upload
    with st.expander("Upload File"):
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'csv', 'txt'])
        if uploaded_file is not None:
            try:
                content = ""
                if uploaded_file.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    for page in pdf_reader.pages:
                        content += page.extract_text()
                elif uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file)
                    content = df.to_string()
                else:  # txt file
                    content = uploaded_file.getvalue().decode()
                
                data = supabase.table('knowledge_base').insert({
                    "content": content,
                    "source": uploaded_file.name
                }).execute()
                st.success("File processed and added to knowledge base!")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
    
    # View Knowledge Base
    with st.expander("View Knowledge Base"):
        if st.button("Refresh Knowledge Base"):
            try:
                response = supabase.table('knowledge_base').select("*").execute()
                entries = response.data
                
                for entry in entries:
                    st.write(f"Source: {entry['source']}")
                    st.write(f"Added: {entry['date_added']}")
                    st.text_area("Content", entry['content'], key=f"kb_{entry['id']}", disabled=True)
                    st.divider()
            except Exception as e:
                st.error(f"Error loading knowledge base: {str(e)}")

def show_settings_page():
    st.header("Settings")
    
    if st.button("Logout"):
        st.session_state.credentials = None
        st.experimental_rerun()

if __name__ == "__main__":
    main()
