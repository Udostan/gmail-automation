import streamlit as st

# Page config
st.set_page_config(page_title="Email Assistant", page_icon="📧", layout="wide")

# Sample data
SAMPLE_EMAILS = [
    {
        'id': '1',
        'subject': 'Project Update Request',
        'from': 'manager@company.com',
        'date': '2024-02-20',
        'body': 'Hi team,\n\nCould you please provide an update on the current project status?'
    },
    {
        'id': '2',
        'subject': 'Meeting Schedule Change',
        'from': 'admin@company.com',
        'date': '2024-02-19',
        'body': 'Dear all,\n\nThe weekly team meeting has been rescheduled to Thursday at 2 PM.'
    },
    {
        'id': '3',
        'subject': 'Client Feedback Required',
        'from': 'client.success@company.com',
        'date': '2024-02-18',
        'body': 'Hello,\n\nWe need your feedback on the latest feature release.'
    }
]

# Initialize session state
if 'emails' not in st.session_state:
    st.session_state.emails = SAMPLE_EMAILS
if 'selected_email' not in st.session_state:
    st.session_state.selected_email = None

# Title
st.title("📧 Email Assistant")

# Layout
col1, col2 = st.columns([1, 2])

# Email list
with col1:
    st.subheader("📥 Inbox")
    for email in st.session_state.emails:
        if st.button(
            f"📨 {email['subject']}\n\nFrom: {email['from']}\nDate: {email['date']}",
            key=f"email_{email['id']}"
        ):
            st.session_state.selected_email = email

# Email details
with col2:
    st.subheader("📝 Message Details")
    if st.session_state.selected_email:
        email = st.session_state.selected_email
        st.markdown(f"**From:** {email['from']}")
        st.markdown(f"**Date:** {email['date']}")
        st.markdown(f"**Subject:** {email['subject']}")
        st.markdown("---")
        st.text_area("Message:", email['body'], height=200)
        
        # AI Response
        if st.button("🤖 Generate Response"):
            response = f"Thank you for your email regarding {email['subject']}. I will review and respond shortly."
            st.text_area("AI Response:", response, height=150)
            if st.button("Send Response"):
                st.success("Response sent! (Demo Mode)")
    else:
        st.info("👈 Select an email from the inbox")