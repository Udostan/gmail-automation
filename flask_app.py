import os
from dotenv import load_dotenv
import pickle
from flask import Flask, request, url_for, session, redirect, render_template, jsonify
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from pathlib import Path
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import PyPDF2
import pandas as pd
import requests
from bs4 import BeautifulSoup
from werkzeug.utils import secure_filename
import threading
import time
from queue import Queue
import base64

# Load environment variables from .env file
load_dotenv()

# Allow HTTP for local development only if not in production
if not os.getenv('PRODUCTION', False):
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Groq API configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"  # Groq's API endpoint

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config['UPLOAD_FOLDER'] = os.getenv('UPLOAD_FOLDER', 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'csv', 'txt'}

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///email_app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def init_database():
    """Initialize the database and create all tables."""
    try:
        # Ensure we're in an application context
        with app.app_context():
            # Create tables if they don't exist
            db.create_all()
            print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        raise

# Model definitions
class EmailTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Knowledge Base Model
class KnowledgeBase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100), nullable=False)  # e.g., 'text_input', 'file_upload', 'website'
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

# Email Queue Model
class EmailQueue(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(500))
    body = db.Column(db.Text)
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    response_sent = db.Column(db.Boolean, default=False)

# Create necessary folders
os.makedirs('uploads', exist_ok=True)

# Initialize database
init_database()

# OAuth 2.0 configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
CLIENT_SECRETS_FILE = "credentials.json"

@app.route('/')
def index():
    if 'credentials' not in session:
        return render_template('login.html')
    return render_template('dashboard.html')

@app.route('/authorize')
def authorize():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(authorization_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
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
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    if 'credentials' in session:
        del session['credentials']
    return redirect(url_for('index'))

@app.route('/send_email', methods=['POST'])
def send_email():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    credentials = Credentials(**session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)
    
    data = request.get_json()
    to = data.get('to')  # This will now be a list of email addresses
    subject = data.get('subject')
    message = data.get('message')
    
    if not to or not isinstance(to, list) or len(to) == 0:
        return {'status': 'error', 'message': 'At least one recipient email is required'}
    
    # Create email message
    email_msg = create_message('me', to, subject, message)
    
    try:
        service.users().messages().send(userId='me', body=email_msg).execute()
        return {'status': 'success', 'message': f'Email sent successfully to {len(to)} recipients'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/list_emails')
def list_emails():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    credentials = Credentials(**session['credentials'])
    service = build('gmail', 'v1', credentials=credentials)
    
    try:
        results = service.users().messages().list(userId='me', maxResults=10).execute()
        messages = results.get('messages', [])
        
        email_list = []
        for msg in messages:
            email = service.users().messages().get(userId='me', id=msg['id']).execute()
            headers = email['payload']['headers']
            subject = next(h['value'] for h in headers if h['name'] == 'Subject')
            sender = next(h['value'] for h in headers if h['name'] == 'From')
            email_list.append({
                'id': msg['id'],
                'subject': subject,
                'sender': sender
            })
        
        return {'status': 'success', 'emails': email_list}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@app.route('/templates', methods=['GET'])
def list_templates():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    templates = EmailTemplate.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'subject': t.subject,
        'body': t.body,
        'created_at': t.created_at.isoformat(),
        'updated_at': t.updated_at.isoformat()
    } for t in templates])

@app.route('/templates', methods=['POST'])
def create_template():
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    data = request.get_json()
    template = EmailTemplate(
        name=data['name'],
        subject=data['subject'],
        body=data['body']
    )
    db.session.add(template)
    db.session.commit()
    
    return jsonify({
        'id': template.id,
        'name': template.name,
        'subject': template.subject,
        'body': template.body,
        'created_at': template.created_at.isoformat(),
        'updated_at': template.updated_at.isoformat()
    })

@app.route('/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    template = EmailTemplate.query.get_or_404(template_id)
    return jsonify({
        'id': template.id,
        'name': template.name,
        'subject': template.subject,
        'body': template.body,
        'created_at': template.created_at.isoformat(),
        'updated_at': template.updated_at.isoformat()
    })

@app.route('/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    template = EmailTemplate.query.get_or_404(template_id)
    data = request.get_json()
    
    template.name = data.get('name', template.name)
    template.subject = data.get('subject', template.subject)
    template.body = data.get('body', template.body)
    db.session.commit()
    
    return jsonify({
        'id': template.id,
        'name': template.name,
        'subject': template.subject,
        'body': template.body,
        'created_at': template.created_at.isoformat(),
        'updated_at': template.updated_at.isoformat()
    })

@app.route('/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    if 'credentials' not in session:
        return redirect(url_for('authorize'))
    
    template = EmailTemplate.query.get_or_404(template_id)
    db.session.delete(template)
    db.session.commit()
    
    return '', 204

def create_message(sender, to, subject, message_text):
    from email.mime.text import MIMEText
    import base64
    
    message = MIMEText(message_text)
    # Handle multiple recipients
    if isinstance(to, list):
        message['to'] = ', '.join(to)
    else:
        message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
    return {'raw': raw_message}

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

# Knowledge Base Routes
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def process_csv(file_path):
    df = pd.read_csv(file_path)
    return df.to_string()

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup.get_text()

@app.route('/knowledge/add/text', methods=['POST'])
def add_text_knowledge():
    try:
        print("Received request to add text knowledge")
        data = request.get_json()
        print(f"Request data: {data}")
        
        if not data or 'text' not in data:
            print("No text provided in request")
            return jsonify({'success': False, 'error': 'No text provided'}), 400
            
        text = data['text']
        if not text.strip():
            print("Empty text content")
            return jsonify({'success': False, 'error': 'Text content is empty'}), 400
            
        print(f"Attempting to save text: {text[:100]}...")  # Log first 100 chars
        
        try:
            # Ensure we're in an application context
            with app.app_context():
                # Create new knowledge base entry
                knowledge_entry = KnowledgeBase(
                    content=text,
                    source='text_input',
                    date_added=datetime.utcnow()
                )
                
                print("Created knowledge base entry, attempting to save...")
                db.session.add(knowledge_entry)
                db.session.commit()
                print("Successfully saved to database")
                
                return jsonify({
                    'success': True,
                    'message': 'Text added to knowledge base successfully'
                })
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
            
    except Exception as e:
        print(f"Error in add_text_knowledge: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/knowledge/add/file', methods=['POST'])
def add_file_knowledge():
    if 'credentials' not in session:
        return redirect('/login')
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        file_type = filename.rsplit('.', 1)[1].lower()
        if file_type == 'pdf':
            content = extract_text_from_pdf(file_path)
        elif file_type == 'csv':
            content = process_csv(file_path)
        else:  # txt file
            with open(file_path, 'r') as f:
                content = f.read()
        
        knowledge = KnowledgeBase(
            content=content,
            source=filename,
            date_added=datetime.utcnow()
        )
        db.session.add(knowledge)
        db.session.commit()
        
        return jsonify({'message': f'{file_type.upper()} file processed and added to knowledge base'})
    
    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/knowledge/add/website', methods=['POST'])
def add_website_knowledge():
    if 'credentials' not in session:
        return redirect('/login')
    
    url = request.form.get('url')
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        content = scrape_website(url)
        knowledge = KnowledgeBase(
            content=content,
            source=url,
            date_added=datetime.utcnow()
        )
        db.session.add(knowledge)
        db.session.commit()
        
        return jsonify({'message': 'Website content added to knowledge base'})
    except Exception as e:
        return jsonify({'error': f'Failed to process website: {str(e)}'}), 400

@app.route('/test_grok', methods=['POST'])
def test_grok():
    try:
        # Get all knowledge base entries
        knowledge_entries = KnowledgeBase.query.all()
        knowledge_text = "\n\n".join([entry.content for entry in knowledge_entries])
        
        # Prepare the system message with the knowledge base
        system_message = f"You are a helpful business assistant. Use the following business knowledge base to inform your responses:\n\n{knowledge_text}"
        
        # Prepare the API request
        api_key = os.getenv('GROQ_API_KEY') or os.getenv('GROQ_API_KEY')  # Try both for backward compatibility
        if not api_key:
            return jsonify({
                'success': False,
                'error': 'API key not found. Please set GROQ_API_KEY in your .env file.'
            }), 500
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'messages': [
                {'role': 'system', 'content': system_message},
                {'role': 'user', 'content': 'Please generate a professional and helpful response to this email:\nHello! How can you help me with my business?'}
            ],
            'model': 'mixtral-8x7b-32768',
            'temperature': 0.7,
            'max_tokens': 1000
        }
        
        print("Making request to Groq API: https://api.groq.com/openai/v1/chat/completions")
        print(f"Headers: {headers}")
        print(f"Data: {data}")
        
        response = requests.post(
            GROQ_API_URL,
            headers=headers,
            json=data,
            timeout=30
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Parse the response
        response_data = response.json()
        if 'choices' in response_data and len(response_data['choices']) > 0:
            generated_text = response_data['choices'][0]['message']['content']
            return jsonify({
                'success': True,
                'response': generated_text
            })
        else:
            print(f"Unexpected response format: {response_data}")
            return jsonify({
                'success': False,
                'error': 'Unexpected response format from API'
            }), 500
            
    except requests.exceptions.RequestException as e:
        print(f"\nRequest error: {str(e)}")
        if hasattr(e.response, 'content'):
            print(f"Error response: {e.response.content.decode()}")
        return jsonify({
            'success': False,
            'error': f'API request failed: {str(e)}'
        }), 500
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/init_test_knowledge')
def init_test_knowledge():
    try:
        # Add a test knowledge entry
        test_knowledge = KnowledgeBase(
            content="""Our company specializes in eco-friendly home cleaning products. 
            We offer a range of natural, biodegradable cleaning solutions that are safe for families and pets. 
            Our most popular products include:
            1. All-Purpose Natural Cleaner
            2. Pet-Safe Floor Cleaner
            3. Eco-Friendly Laundry Detergent
            
            We offer worldwide shipping and have a 30-day satisfaction guarantee on all products.
            Our customer service team is available Monday-Friday, 9 AM - 5 PM EST.""",
            source="test_init",
            date_added=datetime.utcnow()
        )
        
        db.session.add(test_knowledge)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Test knowledge added successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

# Email monitoring and auto-response system
def generate_ai_response(email_body, knowledge_base):
    # Combine all knowledge base content
    context = "\n\n".join([entry.content for entry in knowledge_base])
    
    # Create prompt for Groq
    messages = [
        {
            "role": "system",
            "content": "You are a helpful business assistant. Use the following business knowledge base to inform your responses:"
                      f"\n\n{context}"
        },
        {
            "role": "user",
            "content": f"Please generate a professional and helpful response to this email:\n{email_body}"
        }
    ]
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "messages": messages,
            "model": "mixtral-8x7b-32768",
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        print(f"Making request to Groq API: {GROQ_API_URL}")
        print(f"Headers: {headers}")
        print(f"Data: {data}")
        
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        
        print(f"Response status code: {response.status_code}")
        print(f"Response content: {response.text}")
        
        response.raise_for_status()
        
        return response.json()['choices'][0]['message']['content']
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        if hasattr(e.response, 'text'):
            print(f"Error response: {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return None

def monitor_emails():
    while True:
        try:
            # Get Gmail service
            creds = Credentials.from_authorized_user_info(session['credentials'])
            service = build('gmail', 'v1', credentials=creds)
            
            # Check for new emails
            results = service.users().messages().list(userId='me', q='is:unread').execute()
            messages = results.get('messages', [])
            
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                
                # Extract email details
                headers = msg['payload']['headers']
                subject = next(h['value'] for h in headers if h['name'] == 'Subject')
                sender = next(h['value'] for h in headers if h['name'] == 'From')
                
                # Get email body
                if 'data' in msg['payload']['body']:
                    body = msg['payload']['body']['data']
                else:
                    parts = msg['payload']['parts']
                    body = next(part['body']['data'] for part in parts if part['mimeType'] == 'text/plain')
                
                # Add to queue
                email = EmailQueue(
                    sender=sender,
                    subject=subject,
                    body=body,
                    received_at=datetime.utcnow()
                )
                db.session.add(email)
                db.session.commit()
                
                # Wait 2 minutes
                time.sleep(120)
                
                # Check if email is still unread
                msg_status = service.users().messages().get(userId='me', id=message['id']).execute()
                if 'UNREAD' in msg_status['labelIds']:
                    # Generate and send AI response
                    knowledge_base = KnowledgeBase.query.all()
                    ai_response = generate_ai_response(body, knowledge_base)
                    
                    if ai_response:
                        # Send response
                        message = {
                            'raw': ai_response
                        }
                        service.users().messages().send(userId='me', body=message).execute()
                        
                        # Update queue
                        email.processed = True
                        email.response_sent = True
                        db.session.commit()
        
        except Exception as e:
            print(f"Error in email monitoring: {e}")
        
        time.sleep(60)  # Check every minute

# Start email monitoring in a separate thread
email_monitor_thread = threading.Thread(target=monitor_emails, daemon=True)
email_monitor_thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)
