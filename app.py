# Required imports
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
import secrets

# Disable HTTPS requirement for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Gmail API scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://mail.google.com/'
]

# Constants
STATE_FILE = 'oauth_state.json'
CREDENTIALS_FILE = 'gmail_token.json'

def save_state(state):
    """Save OAuth state to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({'state': state}, f)
    except Exception as e:
        print(f"Error saving state: {e}")

def load_state():
    """Load OAuth state from file"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('state')
    except Exception as e:
        print(f"Error loading state: {e}")
    return None

def save_credentials(creds_dict):
    """Save credentials to file"""
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds_dict, f)

def load_credentials():
    """Load credentials from file"""
    try:
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def initialize_oauth_flow():
    """Initialize OAuth flow and generate authorization URL"""
    try:
        # Load client configuration
        client_config = load_client_config()
        if not client_config:
            st.error("Failed to load client configuration")
            return None

        # Create flow instance with direct parameters
        flow = Flow.from_client_config(
            client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri='http://localhost:8501'  # Remove trailing slash
        )

        # Generate state
        state = secrets.token_urlsafe(32)
        save_state(state)

        # Generate authorization URL with all required parameters
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'  # Force consent screen
        )

        return auth_url

    except Exception as e:
        print(f"Error initializing OAuth flow: {e}")
        st.error("Error initializing OAuth flow")
        return None

def handle_oauth_callback():
    """Handle the OAuth callback and token exchange"""
    try:
        # Get the authorization code and state from URL parameters
        query_params = st.experimental_get_query_params()
        code = query_params.get("code", [None])[0]
        received_state = query_params.get("state", [None])[0]

        if not code:
            st.error("No authorization code received")
            return

        # Load and verify saved state
        saved_state = load_state()
        if not saved_state:
            st.error("No saved authorization state found")
            return

        if received_state != saved_state:
            st.error("Authorization state mismatch")
            return

        # Load client configuration
        client_config = load_client_config()
        if not client_config:
            st.error("Failed to load client configuration")
            return

        # Create flow instance
        flow = Flow.from_client_config(
            client_config,
            scopes=GMAIL_SCOPES,
            redirect_uri='http://localhost:8501'  # Remove trailing slash
        )

        try:
            # Exchange code for token
            flow.fetch_token(code=code)
            credentials = flow.credentials

            # Store credentials
            creds_dict = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }

            # Save credentials and update session state
            save_credentials(creds_dict)
            st.session_state.token = creds_dict
            st.session_state.authenticated = True

            # Clean up state file
            if os.path.exists(STATE_FILE):
                os.remove(STATE_FILE)

            # Clear URL parameters and show success message
            st.experimental_set_query_params()
            st.success("Successfully connected to Gmail!")
            st.experimental_rerun()

        except Exception as e:
            print(f"Error in token exchange: {e}")
            st.error(f"Authentication failed: {str(e)}")

    except Exception as e:
        print(f"Error in OAuth callback: {e}")
        st.error(f"Authentication error: {str(e)}")

def verify_oauth_token():
    """Verify and refresh OAuth token if needed"""
    try:
        if not st.session_state.get('token'):
            return False

        creds = Credentials.from_authorized_user_info(st.session_state.token)
        
        if creds.valid:
            return True
            
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Update stored credentials
            st.session_state.token.update({
                'token': creds.token,
                'refresh_token': creds.refresh_token
            })
            save_credentials(st.session_state.token)
            return True
            
        return False
    except Exception as e:
        print(f"Error verifying token: {e}")
        return False

def load_client_config():
    """Load OAuth client configuration from client_secrets.json"""
    try:
        with open('client_secrets.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading client configuration: {str(e)}")
        return None

def initialize_supabase():
    """Initialize Supabase client"""
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Error initializing Supabase: {str(e)}")
        return None

def get_redirect_uri():
    """Get the appropriate redirect URI based on the current environment"""
    return 'http://localhost:8501/'  # With trailing slash for OAuth callback

def clear_oauth_error():
    """Clear OAuth error from session state"""
    if 'oauth_error' in st.session_state:
        st.session_state.oauth_error = None

def create_email_message(sender, to, subject, message_text):
    """Create email message"""
    try:
        message = MIMEText(message_text)
        message['to'] = to
        message['from'] = sender
        message['subject'] = subject
        return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    except Exception as e:
        st.error(f"Error creating email message: {str(e)}")
        return None

def send_email(service, message):
    """Send email using Gmail API"""
    try:
        sent_message = service.users().messages().send(userId='me', body=message).execute()
        return sent_message
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return None

def generate_ai_response(prompt):
    """Generate AI response using Groq API"""
    try:
        if not GROQ_API_KEY:
            st.error("Groq API key is not set. Please check your secrets configuration.")
            return None

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
                    "content": f"Generate a professional email response for: {prompt}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        
        # Print response for debugging
        print(f"Groq API Response Status: {response.status_code}")
        print(f"Groq API Response: {response.text}")
        
        response.raise_for_status()
        
        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            st.error("No response generated from AI")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error generating AI response: {str(e)}")
        return None

def get_knowledge_base_context(supabase, email_content):
    """Get relevant knowledge base entries for the email context"""
    try:
        # Extract key terms from email
        # doc = nlp(email_content.lower())
        # keywords = [token.text for token in doc if not token.is_stop and token.is_alpha]
        
        # Query knowledge base for relevant entries
        response = supabase.table('knowledge_base').select('*').execute()
        if not response.data:
            return "No knowledge base entries found."
            
        # Score entries based on relevance
        relevant_entries = []
        for entry in response.data:
            entry_text = f"{entry.get('title', '')} {entry.get('content', '')}".lower()
            # relevance_score = sum(1 for keyword in keywords if keyword in entry_text)
            # if relevance_score > 0:
            relevant_entries.append({
                'content': entry.get('content', ''),
                # 'score': relevance_score
            })
        
        # Sort by relevance and combine
        # relevant_entries.sort(key=lambda x: x['score'], reverse=True)
        context = "\n".join(entry['content'] for entry in relevant_entries[:3])
        return context if context else "No relevant knowledge base entries found."
        
    except Exception as e:
        print(f"Error getting knowledge base context: {e}")
        return "Error accessing knowledge base."

def generate_auto_reply(email_content, subject, knowledge_context):
    """Generate automatic reply using Groq with knowledge base context"""
    try:
        if not GROQ_API_KEY:
            st.error("Groq API key is not set. Please check your secrets configuration.")
            return None

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
        
        # Print request details for debugging
        print(f"Making request to Groq API...")
        print(f"Headers: {headers}")
        print(f"Data: {data}")
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        
        # Print response details for debugging
        print(f"Groq API Response Status: {response.status_code}")
        print(f"Groq API Response: {response.text}")
        
        if response.status_code != 200:
            st.error(f"API request failed with status code {response.status_code}")
            return None
            
        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content']
        else:
            st.error(f"No response generated from AI. Response data: {response_data}")
            return None
            
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        print(f"Request exception: {str(e)}")
        return None
    except Exception as e:
        st.error(f"Error generating auto-reply: {str(e)}")
        print(f"General exception: {str(e)}")
        return None

def auto_reply_monitor():
    """Background process to monitor and auto-reply to emails"""
    try:
        # Get Gmail service
        creds = Credentials.from_authorized_user_info(st.session_state.token)
        service = build('gmail', 'v1', credentials=creds)
        
        # Get unread messages
        messages = get_unread_messages(service)
        current_time = datetime.now(timezone.utc)
        
        for msg in messages:
            # Check if message is older than 2 minutes and hasn't been replied to
            msg_time = datetime.fromtimestamp(int(msg['internalDate'])/1000, timezone.utc)
            time_diff = (current_time - msg_time).total_seconds() / 60
            
            if time_diff >= 2 and not msg.get('auto_replied'):
                # Get knowledge base context
                knowledge_context = get_knowledge_base_context(supabase, msg['body'])
                
                # Generate and send auto-reply
                auto_reply = generate_auto_reply(msg['body'], msg['subject'], knowledge_context)
                if auto_reply:
                    success = send_reply(service, msg['threadId'], msg['from'], msg['subject'], auto_reply)
                    if success:
                        # Mark message as auto-replied
                        msg['auto_replied'] = True
                        print(f"Auto-replied to email: {msg['subject']}")
    except Exception as e:
        print(f"Error in auto-reply monitor: {e}")

def auto_reply_page():
    """Auto Reply Page"""
    if not st.session_state.authenticated:
        st.warning("Please connect your Gmail account first")
        return
        
    st.header("AI Auto-Reply")
    
    # Auto-reply settings
    st.subheader("Auto-Reply Settings")
    auto_reply_enabled = st.toggle("Enable Automatic Replies", value=True)
    st.caption("Emails will be automatically replied to after 2 minutes if no manual response is sent")
    
    # Get Gmail service
    creds = Credentials.from_authorized_user_info(st.session_state.token)
    if not creds:
        st.error("Failed to get Gmail credentials")
        return
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Start auto-reply monitor if enabled
    if auto_reply_enabled:
        if 'auto_reply_thread' not in st.session_state:
            st.session_state.auto_reply_thread = True
            threading.Thread(target=auto_reply_monitor, daemon=True).start()
    
    # Fetch unread messages
    with st.spinner("Fetching unread messages..."):
        messages = get_unread_messages(service)
    
    if not messages:
        st.info("No unread messages found")
        return
    
    st.subheader("Unread Messages")
    
    # Process each message
    for msg in messages:
        with st.expander(f"📧 {msg['subject']}"):
            st.caption(f"From: {msg['from']}")
            st.text_area("Message", msg['body'], height=100)
            
            # Get knowledge base context
            knowledge_context = get_knowledge_base_context(supabase, msg['body'])
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Generate AI Reply", key=f"gen_{msg['id']}"):
                    with st.spinner("Generating AI response..."):
                        ai_response = generate_auto_reply(msg['body'], msg['subject'], knowledge_context)
                        if ai_response:
                            st.session_state[f"response_{msg['id']}"] = ai_response
                            st.success("AI response generated!")
                        else:
                            st.error("Failed to generate AI response")
            
            # Show AI response if generated
            if f"response_{msg['id']}" in st.session_state:
                st.text_area("AI Response", st.session_state[f"response_{msg['id']}"], height=150)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("Send Reply", key=f"send_{msg['id']}"):
                        with st.spinner("Sending reply..."):
                            success = send_reply(
                                service,
                                msg['threadId'],
                                msg['from'],
                                msg['subject'],
                                st.session_state[f"response_{msg['id']}"]
                            )
                            if success:
                                st.success("Reply sent successfully!")
                                msg['auto_replied'] = True  # Mark as replied
                            else:
                                st.error("Failed to send reply")

def get_unread_messages(service):
    """Fetch unread messages from Gmail"""
    try:
        results = service.users().messages().list(
            userId='me',
            labelIds=['INBOX', 'UNREAD'],
            maxResults=10
        ).execute()
        
        messages = results.get('messages', [])
        if not messages:
            return []
            
        detailed_messages = []
        for message in messages:
            msg = service.users().messages().get(
                userId='me',
                id=message['id'],
                format='full'
            ).execute()
            
            headers = msg['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'No Sender')
            
            # Get message body
            if 'parts' in msg['payload']:
                parts = msg['payload']['parts']
                body = next((
                    part['body'].get('data', '')
                    for part in parts
                    if part['mimeType'] == 'text/plain'
                ), '')
            else:
                body = msg['payload']['body'].get('data', '')
            
            if body:
                body = base64.urlsafe_b64decode(body).decode('utf-8')
            
            detailed_messages.append({
                'id': message['id'],
                'subject': subject,
                'from': from_email,
                'body': body,
                'threadId': msg['threadId']
            })
            
        return detailed_messages
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return []

def send_reply(service, thread_id, to_email, subject, message_body):
    """Send reply email"""
    try:
        message = MIMEText(message_body)
        message['to'] = to_email
        message['subject'] = f"Re: {subject}"
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        service.users().messages().send(
            userId='me',
            body={
                'raw': raw_message,
                'threadId': thread_id
            }
        ).execute()
        return True
    except Exception as e:
        print(f"Error sending reply: {e}")
        return False

# Groq API configuration
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Supabase configuration
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Initialize session state variables
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'token' not in st.session_state:
    st.session_state.token = None
if 'page' not in st.session_state:
    st.session_state.page = "Compose Email"
if 'ai_response' not in st.session_state:
    st.session_state.ai_response = ""
if 'message_input' not in st.session_state:
    st.session_state.message_input = ""

# Initialize Supabase
supabase = initialize_supabase()

# Handle OAuth callback if there's a code in URL params
query_params = st.experimental_get_query_params()
if "code" in query_params and "state" in query_params:
    handle_oauth_callback()

# Verify token on every page load if authenticated
if st.session_state.authenticated and not verify_oauth_token():
    st.session_state.authenticated = False
    st.session_state.token = None

# Main app layout
st.title("Gmail AI Assistant")

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")
    
    # Navigation buttons
    if st.button("Compose Email", use_container_width=True):
        st.session_state.page = "Compose Email"
    if st.button("Email Templates", use_container_width=True):
        st.session_state.page = "Email Templates"
    if st.button("Knowledge Base", use_container_width=True):
        st.session_state.page = "Knowledge Base"
    if st.button("Settings", use_container_width=True):
        st.session_state.page = "Settings"
    if st.button("AI Auto-Reply", use_container_width=True):
        st.session_state.page = "AI Auto-Reply"

    # Gmail Authentication
    st.header("Gmail Authentication")
    if not st.session_state.authenticated:
        if st.button("Connect Gmail", key="connect_gmail"):
            auth_url = initialize_oauth_flow()
            if auth_url:
                st.markdown(f'[Click here to authorize Gmail]({auth_url})')
                st.info("Please click the link above to connect your Gmail account")
            else:
                st.error("Failed to initialize OAuth flow")
    else:
        st.success("✓ Connected to Gmail")
        if st.button("Logout", key="logout"):
            st.session_state.authenticated = False
            st.session_state.token = None
            st.experimental_rerun()

# Auto-response background task
def check_for_unreplied_emails():
    if not st.session_state.get('authenticated'):
        return
        
    try:
        creds = Credentials.from_authorized_user_info(st.session_state.token)
        service = build('gmail', 'v1', credentials=creds)
        
        # Get unreplied messages from the last hour
        query = "in:inbox -has:userlabels is:unread newer_than:1h"
        results = service.users().messages().list(userId='me', q=query).execute()
        messages = results.get('messages', [])
        
        for message in messages:
            msg = service.users().messages().get(userId='me', id=message['id']).execute()
            thread = service.users().threads().get(userId='me', id=msg['threadId']).execute()
            
            # Check if thread has no replies
            if len(thread['messages']) == 1:
                headers = msg['payload']['headers']
                subject = next(h['value'] for h in headers if h['name'].lower() == 'subject')
                from_email = next(h['value'] for h in headers if h['name'].lower() == 'from')
                
                # Generate AI response
                original_content = msg['snippet']
                prompt = f"Please generate a professional response to this email:\nFrom: {from_email}\nSubject: {subject}\nContent: {original_content}"
                
                ai_response = generate_ai_response(prompt)
                if ai_response:
                    # Send response
                    response_msg = create_email_message(
                        sender='me',
                        to=from_email,
                        subject=f"Re: {subject}",
                        message_text=ai_response
                    )
                    
                    service.users().messages().send(userId='me', body=response_msg).execute()
                    
                    # Mark as read
                    service.users().messages().modify(
                        userId='me',
                        id=message['id'],
                        body={'removeLabelIds': ['UNREAD']}
                    ).execute()
                    
    except Exception as e:
        print(f"Auto-response error: {e}")

# Start auto-response checker if authenticated
if st.session_state.get('authenticated'):
    if 'auto_response_running' not in st.session_state:
        st.session_state.auto_response_running = True
        
        def auto_response_thread():
            while True:
                check_for_unreplied_emails()
                time.sleep(120)  # 2 minutes
                
        threading.Thread(target=auto_response_thread, daemon=True).start()

def compose_email_page():
    if not st.session_state.authenticated:
        st.warning("Please connect your Gmail account first")
        return
        
    st.header("Compose Email")
    
    # Email form
    col1, col2 = st.columns(2)
    with col1:
        to = st.text_input("To", key="to")
        subject = st.text_input("Subject", key="subject")
        
    # Message body
    message = st.text_area("Message", value=st.session_state.message_input, height=200, key="message_area")
    
    # Update message input in session state
    if message != st.session_state.message_input:
        st.session_state.message_input = message
        
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate AI Response"):
            with st.spinner("Generating response..."):
                ai_response = generate_ai_response(st.session_state.message_input)
                if ai_response:
                    st.session_state.ai_response = ai_response
                    st.success("AI response generated!")
        
    with col2:
        if st.button("Send Email") and st.session_state.authenticated:
            if not to or not subject or not message:
                st.error("Please fill in all fields")
            else:
                with st.spinner("Sending email..."):
                    try:
                        creds = Credentials.from_authorized_user_info(st.session_state.token)
                        service = build('gmail', 'v1', credentials=creds)
                        
                        # Get user's email address
                        user_info = service.users().getProfile(userId='me').execute()
                        sender = user_info['emailAddress']
                        
                        # Create and send message
                        email_message = create_email_message(
                            sender,
                            to,
                            subject,
                            message
                        )
                        
                        if send_email(service, email_message):
                            st.success("Email sent successfully!")
                            # Clear the form
                            st.session_state.message_input = ""
                            st.session_state.ai_response = ""
                            st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error sending email: {str(e)}")
        
    # Display AI response if available
    if st.session_state.ai_response:
        st.subheader("AI Generated Response")
        st.text_area("AI Response", value=st.session_state.ai_response, height=300, key="ai_response_display")
        if st.button("Use AI Response"):
            st.session_state.message_input = st.session_state.ai_response
            st.experimental_rerun()

def email_templates_page():
    """Email Templates Page"""
    if not st.session_state.authenticated:
        st.warning("Please connect your Gmail account first")
        return
        
    st.header("Email Templates")
    
    # Add new template section
    st.subheader("Create New Template")
    with st.form("new_template_form"):
        template_name = st.text_input("Template Name")
        subject = st.text_input("Subject Line")
        content = st.text_area("Template Content", height=200,
            help="You can use placeholders like {name}, {company}, etc.")
        tags = st.text_input("Tags (comma-separated)",
            help="Add tags to organize your templates, e.g., 'sales, follow-up'")
        
        submitted = st.form_submit_button("Save Template")
        if submitted and template_name and subject and content:
            try:
                # Add template to Supabase
                template_data = {
                    'name': template_name,
                    'subject': subject,
                    'content': content,
                    'tags': [tag.strip() for tag in tags.split(',') if tag.strip()],
                    'created_at': datetime.now(timezone.utc).isoformat()
                }
                
                result = supabase.table('email_templates').insert(template_data).execute()
                if result.data:
                    st.success(f"Template '{template_name}' saved successfully!")
                else:
                    st.error("Failed to save template")
            except Exception as e:
                st.error(f"Error saving template: {str(e)}")
    
    # View and manage templates section
    st.subheader("Your Templates")
    
    # Search and filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search templates", "")
    with col2:
        sort_by = st.selectbox("Sort by", ["Newest", "Name A-Z", "Most Used"])
    
    try:
        # Fetch templates from Supabase
        query = supabase.table('email_templates').select("*")
        
        # Apply sorting
        if sort_by == "Newest":
            query = query.order('created_at', desc=True)
        elif sort_by == "Name A-Z":
            query = query.order('name')
        
        templates = query.execute()
        
        if not templates.data:
            st.info("No templates found. Create your first template above!")
            return
            
        # Filter templates based on search
        filtered_templates = templates.data
        if search:
            search_lower = search.lower()
            filtered_templates = [
                t for t in templates.data
                if search_lower in t['name'].lower()
                or search_lower in t['subject'].lower()
                or search_lower in t.get('tags', [])
            ]
        
        # Display templates
        for template in filtered_templates:
            with st.expander(f"📝 {template['name']}"):
                st.caption(f"Subject: {template['subject']}")
                if template.get('tags'):
                    st.caption(f"Tags: {', '.join(template['tags'])}")
                st.text_area("Content", template['content'], height=100, key=f"content_{template['id']}")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button("Use Template", key=f"use_{template['id']}"):
                        # Set template in compose email page
                        st.session_state.message_input = template['content']
                        st.session_state.page = "Compose Email"
                        st.experimental_rerun()
                with col2:
                    if st.button("Edit", key=f"edit_{template['id']}"):
                        # Show edit form
                        st.session_state.editing_template = template
                        st.experimental_rerun()
                with col3:
                    if st.button("Delete", key=f"delete_{template['id']}"):
                        try:
                            supabase.table('email_templates').delete().eq('id', template['id']).execute()
                            st.success(f"Template '{template['name']}' deleted!")
                            st.experimental_rerun()
                        except Exception as e:
                            st.error(f"Error deleting template: {str(e)}")
    
    except Exception as e:
        st.error(f"Error loading templates: {str(e)}")

def knowledge_base_page():
    if not st.session_state.authenticated:
        st.warning("Please connect your Gmail account first")
        return
        
    st.header("Knowledge Base")
    if not supabase:
        st.error("Could not connect to knowledge base. Please check your Supabase configuration.")
        return
        
    # Add content
    st.write("Store and manage your email knowledge base here.")
    
    # Input for new knowledge item
    with st.form("knowledge_form"):
        title = st.text_input("Title")
        content = st.text_area("Content")
        submitted = st.form_submit_button("Add to Knowledge Base")
        
        if submitted and title and content:
            try:
                # Insert into Supabase
                supabase.table('knowledge_base').insert({
                    'title': title,
                    'content': content,
                    'created_at': datetime.now(timezone.utc).isoformat()
                }).execute()
                st.success("Added to knowledge base!")
            except Exception as e:
                st.error(f"Error adding to knowledge base: {str(e)}")
    
    # Display existing knowledge items
    try:
        response = supabase.table('knowledge_base').select("*").order('created_at', desc=True).execute()
        
        if response.data:
            for item in response.data:
                with st.expander(item['title']):
                    st.write(item['content'])
                    st.caption(f"Created at: {item['created_at']}")
    except Exception as e:
        st.error(f"Error fetching knowledge base: {str(e)}")

def settings_page():
    if not st.session_state.authenticated:
        st.warning("Please connect your Gmail account first")
        return
        
    st.header("Settings")
    st.info("Coming soon!")

def auto_reply_page():
    """Auto Reply Page"""
    if not st.session_state.authenticated:
        st.warning("Please connect your Gmail account first")
        return
        
    st.header("AI Auto-Reply")
    
    # Auto-reply settings
    st.subheader("Auto-Reply Settings")
    auto_reply_enabled = st.toggle("Enable Automatic Replies", value=True)
    st.caption("Emails will be automatically replied to after 2 minutes if no manual response is sent")
    
    # Get Gmail service
    creds = Credentials.from_authorized_user_info(st.session_state.token)
    if not creds:
        st.error("Failed to get Gmail credentials")
        return
    
    service = build('gmail', 'v1', credentials=creds)
    
    # Start auto-reply monitor if enabled
    if auto_reply_enabled:
        if 'auto_reply_thread' not in st.session_state:
            st.session_state.auto_reply_thread = True
            threading.Thread(target=auto_reply_monitor, daemon=True).start()
    
    # Fetch unread messages
    with st.spinner("Fetching unread messages..."):
        messages = get_unread_messages(service)
    
    if not messages:
        st.info("No unread messages found")
        return
    
    st.subheader("Unread Messages")
    
    # Process each message
    for msg in messages:
        with st.expander(f"📧 {msg['subject']}"):
            st.caption(f"From: {msg['from']}")
            st.text_area("Message", msg['body'], height=100)
            
            # Get knowledge base context
            knowledge_context = get_knowledge_base_context(supabase, msg['body'])
            
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("Generate AI Reply", key=f"gen_{msg['id']}"):
                    with st.spinner("Generating AI response..."):
                        ai_response = generate_auto_reply(msg['body'], msg['subject'], knowledge_context)
                        if ai_response:
                            st.session_state[f"response_{msg['id']}"] = ai_response
                            st.success("AI response generated!")
                        else:
                            st.error("Failed to generate AI response")
            
            # Show AI response if generated
            if f"response_{msg['id']}" in st.session_state:
                st.text_area("AI Response", st.session_state[f"response_{msg['id']}"], height=150)
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("Send Reply", key=f"send_{msg['id']}"):
                        with st.spinner("Sending reply..."):
                            success = send_reply(
                                service,
                                msg['threadId'],
                                msg['from'],
                                msg['subject'],
                                st.session_state[f"response_{msg['id']}"]
                            )
                            if success:
                                st.success("Reply sent successfully!")
                                msg['auto_replied'] = True  # Mark as replied
                            else:
                                st.error("Failed to send reply")

# Main content area based on selected page
if st.session_state.page == "Compose Email":
    compose_email_page()
elif st.session_state.page == "Email Templates":
    email_templates_page()
elif st.session_state.page == "Knowledge Base":
    knowledge_base_page()
elif st.session_state.page == "Settings":
    settings_page()
elif st.session_state.page == "AI Auto-Reply":
    auto_reply_page()

# Display OAuth error if present
if st.session_state.get('oauth_error'):
    st.sidebar.error(st.session_state.oauth_error)
    if st.sidebar.button("Clear Error"):
        st.session_state.oauth_error = None
        st.experimental_rerun()
