import streamlit as st
from datetime import datetime, timedelta
import random
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os
import json

# Page config
st.set_page_config(
    page_title="Gmail AI Assistant",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
.button {
    display: inline-block;
    padding: 0.5em 1em;
    margin: 0.5em 0;
    background-color: #FF4B4B;
    color: white;
    text-decoration: none;
    border-radius: 0.3em;
    border: none;
    font-size: 1em;
    font-weight: bold;
}
.button:hover {
    background-color: #FF2B2B;
    color: white;
    text-decoration: none;
}
.email-box {
    border: 1px solid #ddd;
    padding: 10px;
    margin: 5px 0;
    border-radius: 5px;
    background-color: white;
}
.email-header {
    color: #1f77b4;
    font-weight: bold;
}
.stButton>button {
    width: 100%;
    margin: 1px;
}
.feature-box {
    background-color: #f0f2f6;
    padding: 20px;
    border-radius: 10px;
    margin: 10px 0;
}
.settings-box {
    background-color: #e6e9ef;
    padding: 15px;
    border-radius: 8px;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Get Gmail API service instance."""
    if 'credentials' not in st.session_state:
        st.session_state.credentials = None

    if not st.session_state.credentials:
        try:
            # Show login button
            st.warning("Please sign in with your Google account to continue")
            if st.button("Sign in with Google"):
                # Create the flow using the client secrets
                flow = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": st.secrets["oauth"]["client_id"],
                            "client_secret": st.secrets["oauth"]["client_secret"],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [st.secrets["oauth"]["redirect_uri"]]
                        }
                    },
                    scopes=SCOPES,
                    redirect_uri=st.secrets["oauth"]["redirect_uri"]
                )
                
                # Generate the authorization URL
                auth_url, _ = flow.authorization_url(prompt="consent")
                
                # Store the flow in session state
                st.session_state['flow'] = flow
                
                # Redirect to Google's auth page
                st.markdown(f'<a href="{auth_url}" target="_self" class="button">Authorize Gmail Access</a>', unsafe_allow_html=True)
                
                return None
                
            # Check for the authorization response
            if 'code' in st.query_params:
                try:
                    flow = st.session_state.get('flow')
                    if flow:
                        flow.fetch_token(code=st.query_params['code'])
                        st.session_state.credentials = flow.credentials
                        st.success("Successfully authenticated!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error exchanging code for token: {str(e)}")
                    return None
                    
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            return None

    if st.session_state.credentials:
        try:
            return build('gmail', 'v1', credentials=st.session_state.credentials)
        except Exception as e:
            st.error(f"Error building Gmail service: {str(e)}")
            st.session_state.credentials = None
            return None

    return None

def send_email(to_email, subject, body):
    """Send email using Gmail API."""
    service = get_gmail_service()
    if not service:
        return False

    try:
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        
        # Encode the message
        raw = base64.urlsafe_b64encode(message.as_bytes())
        raw = raw.decode()
        
        # Send the message
        service.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

# Sample data with more realistic content
SAMPLE_EMAILS = [
    {
        'id': '1',
        'subject': 'Project Update: Q1 Goals',
        'from': 'sarah.manager@company.com',
        'date': (datetime.now() - timedelta(hours=2)).strftime('%Y-%m-%d %H:%M'),
        'body': '''Dear Team,

I hope this email finds you well. I wanted to check on the progress of our Q1 goals. Specifically:

1. User Authentication System
2. Database Optimization
3. Frontend Redesign

Could you please provide updates on these items? We have a stakeholder meeting next week.

Best regards,
Sarah''',
        'labels': ['Important', 'Project', 'Q1']
    },
    {
        'id': '2',
        'subject': 'Client Meeting Rescheduled',
        'from': 'john.client@bigcorp.com',
        'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M'),
        'body': '''Hello team,

Due to some scheduling conflicts, we need to move tomorrow's meeting to Thursday at 2 PM EST. 

Agenda remains the same:
- Project timeline review
- Budget discussion
- Next steps

Please confirm if this works for everyone.

Thanks,
John''',
        'labels': ['Meeting', 'Client', 'Schedule']
    },
    {
        'id': '3',
        'subject': 'New Feature Request',
        'from': 'product@company.com',
        'date': (datetime.now() - timedelta(hours=5)).strftime('%Y-%m-%d %H:%M'),
        'body': '''Hi Development team,

We've received several user requests for a new feature:

- Dark mode support
- Improved mobile responsiveness
- Export to PDF functionality

Could you review these requirements and provide an estimated timeline?

Best,
Product Team''',
        'labels': ['Feature', 'Development', 'Priority']
    }
]

# AI response templates
AI_RESPONSES = {
    '1': '''Dear Sarah,

Thank you for checking in on the Q1 goals. Here's our current status:

1. User Authentication System: 85% complete
   - Basic auth flow implemented
   - Working on 2FA integration

2. Database Optimization: 70% complete
   - Indexes optimized
   - Query performance improved by 40%

3. Frontend Redesign: 60% complete
   - New UI components developed
   - Testing in progress

We're on track to complete all items before the stakeholder meeting. I'll prepare a detailed presentation.

Best regards,
[Your name]''',
    
    '2': '''Dear John,

Thank you for the update. Thursday at 2 PM EST works perfectly for our team.

I'll update the calendar invitation and make sure all relevant documentation is prepared for:
- Project timeline review
- Budget discussion
- Next steps planning

Looking forward to our discussion.

Best regards,
[Your name]''',
    
    '3': '''Dear Product Team,

Thank you for sharing these feature requests. I've reviewed them and here's our initial assessment:

1. Dark Mode Support: 2-3 weeks
   - Theme system implementation
   - User preference storage
   
2. Mobile Responsiveness: 1-2 weeks
   - Responsive grid updates
   - Touch interaction improvements
   
3. PDF Export: 1 week
   - PDF generation library integration
   - Template creation

We can begin work on these features next sprint. Would you like to prioritize any particular feature?

Best regards,
[Your name]'''
}

# Initialize session state
if 'page' not in st.session_state:
    st.session_state.page = 'inbox'
if 'emails' not in st.session_state:
    st.session_state.emails = SAMPLE_EMAILS
if 'selected_email' not in st.session_state:
    st.session_state.selected_email = None
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        'name': '',
        'email': '',
        'signature': '',
        'profile_setup': False
    }

# Check if profile is set up
if not st.session_state.user_profile['profile_setup']:
    st.title("Welcome to Gmail AI Assistant")
    st.header("Set Up Your Profile")
    
    # Get Gmail service
    service = get_gmail_service()
    if service:
        try:
            # Get user's email address
            profile = service.users().getProfile(userId='me').execute()
            email = profile['emailAddress']
            
            with st.form("profile_setup"):
                name = st.text_input("Your Name:", value=st.session_state.user_profile.get('name', ''))
                st.info(f"Email: {email}")
                
                signature = st.text_area("Email Signature:", 
                    value=st.session_state.user_profile.get('signature', ''),
                    placeholder="""Sincerely,

Sarah Johnson
Senior Software Engineer
Tech Solutions Inc.

Email: sarah.johnson@techsolutions.com
Office: +1 (555) 123-4567
Mobile: +1 (555) 987-6543

Tech Solutions Inc.
123 Innovation Drive
San Francisco, CA 94105
https://techsolutions.com""")
                
                if st.form_submit_button("Save Profile"):
                    st.session_state.user_profile.update({
                        'name': name,
                        'email': email,
                        'signature': signature,
                        'profile_setup': True
                    })
                    st.success("Profile saved successfully.")
                    st.rerun()
        except Exception as e:
            st.error(f"Error getting user profile: {str(e)}")
    
    st.stop()

# Sidebar navigation
with st.sidebar:
    st.title("Gmail Assistant")
    
    if st.button("Inbox", use_container_width=True):
        st.session_state.page = 'inbox'
        st.rerun()
    
    if st.button("Composer", use_container_width=True):
        st.session_state.page = 'composer'
        st.rerun()
        
    if st.button("Templates", use_container_width=True):
        st.session_state.page = 'templates'
        st.rerun()
        
    if st.button("Auto-Reply", use_container_width=True):
        st.session_state.page = 'auto_reply'
        st.rerun()
        
    if st.button("Knowledge Base", use_container_width=True):
        st.session_state.page = 'knowledge_base'
        st.rerun()
        
    if st.button("Settings", use_container_width=True):
        st.session_state.page = 'settings'
        st.rerun()

# Main content area
if st.session_state.page == 'inbox':
    st.header("Inbox")
    
    # Filters
    st.subheader("Filters")
    filter_options = ['All', 'Important', 'Meeting', 'Project']
    selected_filter = st.selectbox("Show:", filter_options)
    st.session_state.filter = selected_filter.lower()
    
    # Inbox layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Messages")
        for email in st.session_state.emails:
            if st.session_state.filter != 'all':
                if st.session_state.filter not in [label.lower() for label in email['labels']]:
                    continue
                    
            st.markdown(f"""
            <div class='email-box'>
                <div class='email-header'>{email['subject']}</div>
                <div>From: {email['from']}</div>
                <div>Date: {email['date']}</div>
                <div>Labels: {', '.join(email['labels'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("View Details", key=f"view_{email['id']}"):
                st.session_state.selected_email = email
    
    with col2:
        st.subheader("Message Details")
        if st.session_state.selected_email:
            email = st.session_state.selected_email
            st.info(f"From: {email['from']}")
            st.warning(f"Date: {email['date']}")
            st.success(f"Labels: {', '.join(email['labels'])}")
            st.text_area("Message:", email['body'], height=200, disabled=True)
            
            st.markdown("### AI Assistant")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Generate Response"):
                    response = AI_RESPONSES.get(email['id'], "Thank you for your email. I'll review and respond shortly.")
                    st.session_state.responses[email['id']] = response
            
            with col2:
                if st.button("Suggest Labels"):
                    suggested_labels = ["Follow-up", "Urgent", "Review"]
                    st.info(f"Suggested Labels: {', '.join(suggested_labels)}")
            
            if email['id'] in st.session_state.get('responses', {}):
                st.markdown("### Generated Response")
                response = st.text_area("Edit Response:", st.session_state.responses[email['id']], height=300)
                if st.button("Send Response"):
                    if send_email(
                        email['from'],
                        f"Re: {email['subject']}",
                        response + "\n\n" + st.session_state.user_profile['signature']
                    ):
                        st.success("Response sent successfully.")
                    else:
                        st.error("Failed to send email. Please check your email settings.")
        else:
            st.info("Select an email from the inbox to view details")

elif st.session_state.page == 'composer':
    st.header("New Email")
    with st.form("email_composer"):
        st.info(f"Sending as: {st.session_state.user_profile['email']}")
        to_email = st.text_input("To:")
        subject = st.text_input("Subject:")
        body = st.text_area("Message:", height=300)
        
        full_message = f"{body}\n\n{st.session_state.user_profile['signature']}" if body else ""
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("Save Draft"):
                st.success("Email saved as draft.")
        with col2:
            if st.form_submit_button("Send"):
                if send_email(
                    to_email,
                    subject,
                    full_message
                ):
                    st.success("Email sent successfully.")
                else:
                    st.error("Failed to send email. Please check your email settings.")

elif st.session_state.page == 'settings':
    st.header("Settings")
    
    with st.expander("User Profile", expanded=True):
        with st.form("user_profile"):
            name = st.text_input("Your Name:", value=st.session_state.user_profile['name'])
            email = st.text_input("Your Email:", value=st.session_state.user_profile['email'])
            signature = st.text_area("Email Signature:", 
                value=st.session_state.user_profile['signature'],
                placeholder="""Sincerely,

Sarah Johnson
Senior Software Engineer
Tech Solutions Inc.

Email: sarah.johnson@techsolutions.com
Office: +1 (555) 123-4567
Mobile: +1 (555) 987-6543

Tech Solutions Inc.
123 Innovation Drive
San Francisco, CA 94105
https://techsolutions.com""",
                help="Your email signature is automatically added at the end of your emails. It typically includes your name, title, contact information, and company details.")
            
            if st.form_submit_button("Update Profile"):
                st.session_state.user_profile.update({
                    'name': name,
                    'email': email,
                    'signature': signature
                })
                st.success("Profile updated successfully.")
    
    with st.expander("Appearance"):
        st.selectbox("Theme:", ["Light", "Dark", "System"])
        st.checkbox("Show email preview")
        if st.button("Save Appearance"):
            st.success("Appearance settings saved.")
    
    with st.expander("Email Settings"):
        st.number_input("Emails per page:", min_value=10, max_value=50, value=25)
        st.checkbox("Send read receipts")
        st.checkbox("Enable smart compose")
        st.checkbox("Auto-append signature", value=True)
        if st.button("Save Email Settings"):
            st.success("Email settings saved.")
    
    with st.expander("AI Assistant Settings"):
        st.slider("Response creativity:", 0, 100, 50)
        st.multiselect("Enable AI features:", 
            ["Smart Compose", "Response Generation", "Label Suggestions"],
            ["Response Generation", "Label Suggestions"]
        )
        if st.button("Save AI Settings"):
            st.success("AI settings saved.")