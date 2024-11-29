# Gmail Automation with AI

A Streamlit-based application that automates Gmail interactions using AI-powered responses and intelligent email management.

## Features

- Gmail OAuth integration
- AI-powered email auto-replies using Groq API
- Knowledge base integration with Supabase
- Email template management
- Automated email monitoring and responses
- Professional email composition interface

## Requirements

- Python 3.12
- Streamlit
- Google Gmail API credentials
- Groq API key
- Supabase account and credentials

## Environment Variables

Create a `.streamlit/secrets.toml` file with the following:

```toml
# Supabase credentials
SUPABASE_URL = "your-supabase-url"
SUPABASE_KEY = "your-supabase-key"

# Google OAuth Settings
GOOGLE_CLIENT_ID = "your-google-client-id"
GOOGLE_CLIENT_SECRET = "your-google-client-secret"
GOOGLE_REDIRECT_URI = "your-redirect-uri"

# Groq API key
GROQ_API_KEY = "your-groq-api-key"
```

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set up your environment variables
4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Deployment

This application can be deployed on Streamlit Cloud:

1. Push your code to GitHub
2. Visit [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add your secrets in the Streamlit Cloud dashboard
5. Deploy!
