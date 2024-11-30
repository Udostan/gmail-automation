from flask import Flask, request, redirect, session, url_for
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
import base64
import os
import json
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']

# OAuth 2.0 client configuration
CLIENT_CONFIG = {
    "web": {
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.getenv("REDIRECT_URI")]
    }
}

@app.route('/')
def index():
    if 'credentials' not in session:
        return '''
            <h1>Gmail AI Assistant</h1>
            <p>Please sign in with your Google account to continue.</p>
            <a href="/login" 
               style="display: inline-block; 
                      padding: 10px 20px; 
                      background-color: #4285f4; 
                      color: white; 
                      text-decoration: none; 
                      border-radius: 5px;
                      font-family: Arial, sans-serif;">
                Sign in with Google
            </a>
        '''
    return '''
        <h1>Welcome to Gmail AI Assistant</h1>
        <p>You are logged in!</p>
        <a href="/logout" 
           style="display: inline-block; 
                  padding: 10px 20px; 
                  background-color: #db4437; 
                  color: white; 
                  text-decoration: none; 
                  border-radius: 5px;
                  font-family: Arial, sans-serif;">
            Logout
        </a>
    '''

@app.route('/login')
def login():
    # Create flow instance
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=os.getenv("REDIRECT_URI")
    )
    
    # Generate URL for request to Google's OAuth 2.0 server
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    
    flow = Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        state=state,
        redirect_uri=os.getenv("REDIRECT_URI")
    )
    
    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def get_gmail_service():
    if 'credentials' not in session:
        return None
        
    credentials = Credentials(
        **session['credentials']
    )
    
    return build('gmail', 'v1', credentials=credentials)

def send_email(to_email, subject, body):
    service = get_gmail_service()
    if not service:
        return False
        
    message = MIMEText(body)
    message['to'] = to_email
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    try:
        service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
        return True
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        return False

if __name__ == '__main__':
    app.run(debug=True)
