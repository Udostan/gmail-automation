import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
import requests
from datetime import datetime, timedelta
import base64
from supabase import create_client
import PyPDF2
import pandas as pd
from email.mime.text import MIMEText
import time

# Page configuration
st.set_page_config(page_title="Gmail Automation", layout="wide")

# Initialize session state
if 'credentials' not in st.session_state:
    st.session_state.credentials = None
if 'auto_reply_enabled' not in st.session_state:
    st.session_state.auto_reply_enabled = False
if 'last_email_check' not in st.session_state:
    st.session_state.last_email_check = None

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

def get_ai_response(prompt, context=""):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mixtral-8x7b-32768",
            "messages": [
                {"role": "system", "content": "You are an AI assistant helping to compose email responses."},
                {"role": "user", "content": f"Context: {context}\n\nPrompt: {prompt}"}
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        st.error(f"Error getting AI response: {str(e)}")
        return None

def main():
    st.title("Gmail Automation")
    
    # Sidebar
    with st.sidebar:
        st.title("Navigation")
        page = st.radio("Go to", ["Home", "Auto-Reply", "Email Templates", "Knowledge Base", "Settings"])

    if not st.session_state.credentials:
        st.write("Please login with your Google account to get started")
        if st.button("Login with Google"):
            handle_auth()
    else:
        if page == "Home":
            show_home_page()
        elif page == "Auto-Reply":
            show_auto_reply_page()
        elif page == "Email Templates":
            show_templates_page()
        elif page == "Knowledge Base":
            show_knowledge_base_page()
        elif page == "Settings":
            show_settings_page()

def handle_auth():
    try:
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
        st.info('After authorization, you will be redirected back to this app.')
    except Exception as e:
        st.error(f"Authentication error: {str(e)}")

def create_message(sender, to, subject, message_text):
    try:
        message = MIMEText(message_text)
        message['to'] = ', '.join(to) if isinstance(to, list) else to
        message['from'] = sender
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        return {'raw': raw_message}
    except Exception as e:
        st.error(f"Error creating message: {str(e)}")
        return None

def check_new_emails(service, last_check_time):
    try:
        query = f'after:{int(last_check_time.timestamp())}'
        results = service.users().messages().list(userId='me', q=query).execute()
        return results.get('messages', [])
    except Exception as e:
        st.error(f"Error checking emails: {str(e)}")
        return []

def process_auto_replies(service, new_messages):
    try:
        for msg in new_messages:
            email = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = email['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            # Get email body
            if 'parts' in email['payload']:
                body = base64.urlsafe_b64decode(email['payload']['parts'][0]['body']['data']).decode()
            else:
                body = base64.urlsafe_b64decode(email['payload']['body']['data']).decode()
            
            # Generate AI response
            context = f"This is a reply to an email with subject: {subject}"
            prompt = f"Generate a professional response to this email:\n\n{body}"
            ai_response = get_ai_response(prompt, context)
            
            if ai_response:
                reply = create_message(
                    'me',
                    sender,
                    f"Re: {subject}",
                    ai_response
                )
                service.users().messages().send(userId='me', body=reply).execute()
    except Exception as e:
        st.error(f"Error processing auto-replies: {str(e)}")

def show_auto_reply_page():
    st.header("Auto-Reply Settings")
    
    auto_reply_enabled = st.toggle("Enable Auto-Reply", st.session_state.auto_reply_enabled)
    
    if auto_reply_enabled != st.session_state.auto_reply_enabled:
        st.session_state.auto_reply_enabled = auto_reply_enabled
        if auto_reply_enabled:
            st.session_state.last_email_check = datetime.now()
            st.success("Auto-reply enabled!")
        else:
            st.info("Auto-reply disabled")
    
    if st.session_state.auto_reply_enabled:
        try:
            credentials = Credentials(**st.session_state.credentials)
            service = build('gmail', 'v1', credentials=credentials)
            
            # Check for new emails every minute
            current_time = datetime.now()
            if (st.session_state.last_email_check is None or 
                (current_time - st.session_state.last_email_check) > timedelta(minutes=1)):
                
                new_messages = check_new_emails(service, st.session_state.last_email_check)
                if new_messages:
                    process_auto_replies(service, new_messages)
                
                st.session_state.last_email_check = current_time
        except Exception as e:
            st.error(f"Error in auto-reply: {str(e)}")
            st.session_state.auto_reply_enabled = False

def show_home_page():
    st.header("Dashboard")
    
    # Email composition with AI assistance
    with st.expander("Compose Email"):
        to = st.text_input("To (separate multiple emails with commas)")
        subject = st.text_input("Subject")
        message = st.text_area("Message")
        
        if st.button("Get AI Suggestions"):
            prompt = f"Suggest improvements for this email:\n\nSubject: {subject}\n\n{message}"
            suggestions = get_ai_response(prompt)
            if suggestions:
                st.info("AI Suggestions:")
                st.write(suggestions)
        
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
                
                if email_msg:
                    service.users().messages().send(userId='me', body=email_msg).execute()
                    st.success("Email sent successfully!")
            except Exception as e:
                st.error(f"Error sending email: {str(e)}")

def show_knowledge_base_page():
    st.header("Knowledge Base")
    
    # Search functionality
    search_query = st.text_input("Search Knowledge Base")
    if search_query:
        try:
            # Use AI to enhance search
            search_prompt = f"Extract key terms and concepts from this search query: {search_query}"
            enhanced_terms = get_ai_response(search_prompt)
            
            if enhanced_terms:
                response = supabase.table('knowledge_base').select("*").textSearch('content', enhanced_terms).execute()
                entries = response.data
                
                if entries:
                    st.write(f"Found {len(entries)} relevant entries:")
                    for entry in entries:
                        st.write(f"Source: {entry['source']}")
                        st.write(f"Added: {entry['date_added']}")
                        st.text_area("Content", entry['content'], key=f"kb_search_{entry['id']}", disabled=True)
                        st.divider()
                else:
                    st.info("No matching entries found")
        except Exception as e:
            st.error(f"Error searching knowledge base: {str(e)}")
    
    # Text input
    with st.expander("Add Text"):
        text = st.text_area("Enter text to add to knowledge base")
        if st.button("Add Text"):
            try:
                data = supabase.table('knowledge_base').insert({
                    "content": text,
                    "source": "text_input",
                    "date_added": datetime.now().isoformat()
                }).execute()
                st.success("Text added to knowledge base!")
            except Exception as e:
                st.error(f"Error adding text: {str(e)}")
    
    # File upload with progress
    with st.expander("Upload File"):
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'csv', 'txt'])
        if uploaded_file is not None:
            try:
                progress_bar = st.progress(0)
                content = ""
                
                if uploaded_file.type == "application/pdf":
                    pdf_reader = PyPDF2.PdfReader(uploaded_file)
                    total_pages = len(pdf_reader.pages)
                    for i, page in enumerate(pdf_reader.pages):
                        content += page.extract_text()
                        progress_bar.progress((i + 1) / total_pages)
                elif uploaded_file.type == "text/csv":
                    df = pd.read_csv(uploaded_file)
                    content = df.to_string()
                    progress_bar.progress(1.0)
                else:  # txt file
                    content = uploaded_file.getvalue().decode()
                    progress_bar.progress(1.0)
                
                data = supabase.table('knowledge_base').insert({
                    "content": content,
                    "source": uploaded_file.name,
                    "date_added": datetime.now().isoformat()
                }).execute()
                st.success("File processed and added to knowledge base!")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")

def show_settings_page():
    st.header("Settings")
    
    # Auto-reply settings
    with st.expander("Auto-Reply Settings"):
        st.checkbox("Send notification when auto-reply is triggered")
        st.number_input("Minimum time between auto-replies (minutes)", min_value=1, value=5)
    
    # Knowledge base settings
    with st.expander("Knowledge Base Settings"):
        st.number_input("Maximum file size (MB)", min_value=1, value=10)
        st.multiselect("Allowed file types", ['pdf', 'csv', 'txt', 'doc', 'docx'], default=['pdf', 'csv', 'txt'])
    
    # Account settings
    with st.expander("Account Settings"):
        st.text_input("Default email signature")
        st.selectbox("Default email format", ["Plain text", "HTML"])
    
    if st.button("Save Settings"):
        st.success("Settings saved successfully!")
    
    if st.button("Logout"):
        st.session_state.credentials = None
        st.session_state.auto_reply_enabled = False
        st.experimental_rerun()

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

if __name__ == "__main__":
    main()
