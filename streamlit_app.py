import streamlit as st

# Basic page configuration
st.set_page_config(page_title="Gmail Automation", layout="wide")

# Display basic page
st.title("Gmail Automation")
st.write("Basic initialization test")

# Test secrets access
try:
    # Verify secrets are available
    required_secrets = [
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "OAUTH_REDIRECT_URI",
        "GROQ_API_KEY"
    ]
    
    missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
    if missing_secrets:
        st.error(f"Missing required secrets: {', '.join(missing_secrets)}")
    else:
        st.success("All required secrets are available")
        
except Exception as e:
    st.error(f"Error checking secrets: {str(e)}")