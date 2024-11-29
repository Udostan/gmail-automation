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

## Deployment to Streamlit Cloud

### Prerequisites
1. GitHub repository with your code
2. Google Cloud Console project with Gmail API enabled
3. Groq API account and key
4. Supabase project

### Step-by-Step Deployment Guide

1. **Prepare Your Repository**
   - Ensure all dependencies are in `requirements.txt`
   - Remove any sensitive information from code
   - Commit and push all changes to GitHub

2. **Configure Google OAuth**
   - Go to Google Cloud Console
   - Add `https://your-app-url.streamlit.app` to authorized redirect URIs
   - Add `https://your-app-url.streamlit.app/*` to authorized JavaScript origins

3. **Deploy on Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Select the main branch and the `streamlit_app.py` file

4. **Configure Secrets**
   In Streamlit Cloud dashboard:
   - Go to your app settings
   - Add the following secrets:
     ```toml
     SUPABASE_URL = "your-supabase-url"
     SUPABASE_KEY = "your-supabase-key"
     GOOGLE_CLIENT_ID = "your-google-client-id"
     GOOGLE_CLIENT_SECRET = "your-google-client-secret"
     GOOGLE_REDIRECT_URI = "https://your-app-url.streamlit.app"
     GROQ_API_KEY = "your-groq-api-key"
     ```

5. **Verify Deployment**
   - Check the deployment logs
   - Test OAuth flow
   - Verify all features are working

### Security Considerations

1. **OAuth Configuration**
   - Use correct redirect URIs
   - Keep client secrets secure
   - Configure proper scopes

2. **API Keys**
   - Never commit API keys to the repository
   - Use environment variables for all sensitive data
   - Regularly rotate API keys

3. **Data Protection**
   - Ensure Supabase security rules are properly configured
   - Implement proper session management
   - Handle user data according to privacy regulations

### Troubleshooting

1. **OAuth Issues**
   - Verify redirect URIs in Google Cloud Console
   - Check OAuth consent screen configuration
   - Ensure all required scopes are enabled

2. **API Connection Problems**
   - Verify API keys are correctly set in Streamlit secrets
   - Check API rate limits
   - Monitor error logs in Streamlit Cloud

3. **Database Issues**
   - Verify Supabase connection string
   - Check database permissions
   - Monitor database logs

## Maintenance

1. **Regular Updates**
   - Keep dependencies updated
   - Monitor security advisories
   - Update API versions when needed

2. **Monitoring**
   - Check application logs regularly
   - Monitor API usage and quotas
   - Track error rates and performance

3. **Backup**
   - Regularly backup Supabase database
   - Keep configuration backups
   - Document all custom settings

## Support

For issues and feature requests, please create an issue in the GitHub repository.
