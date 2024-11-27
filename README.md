# Gmail Automation Web App

This web application allows you to automate various Gmail operations using the Gmail API.

## Setup Instructions

1. Create a Google Cloud Project and enable the Gmail API
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Gmail API
   - Create OAuth 2.0 credentials (download as credentials.json)

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Place your credentials.json file in the project root directory

4. Run the application:
```bash
python app.py
```

5. Visit http://localhost:5000 in your browser

## Features
- OAuth2 authentication with Gmail
- View emails
- Send emails
- Search emails
- Automated email operations
