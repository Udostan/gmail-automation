import streamlit as st
from datetime import datetime, timedelta
import random

# Page config
st.set_page_config(
    page_title="Gmail AI Assistant",
    page_icon="📧",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
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
if 'responses' not in st.session_state:
    st.session_state.responses = {}
if 'filter' not in st.session_state:
    st.session_state.filter = 'all'

# Sidebar navigation
with st.sidebar:
    st.title("📧 Gmail Assistant")
    
    # Navigation
    st.header("📌 Navigation")
    nav_options = {
        "📥 Inbox": "inbox",
        "✍️ Composer": "composer",
        "📝 Templates": "templates",
        "🤖 Auto-Reply": "auto_reply",
        "📚 Knowledge Base": "knowledge_base",
        "⚙️ Settings": "settings"
    }
    
    for label, page in nav_options.items():
        if st.button(label, key=f"nav_{page}"):
            st.session_state.page = page
            st.session_state.selected_email = None
    
    # Filters (only show in inbox)
    if st.session_state.page == 'inbox':
        st.header("📑 Filters")
        filter_options = ['All', 'Important', 'Meeting', 'Project']
        selected_filter = st.selectbox("Show:", filter_options)
        st.session_state.filter = selected_filter.lower()

# Main content based on selected page
if st.session_state.page == 'inbox':
    # Inbox layout
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📥 Inbox")
        for email in st.session_state.emails:
            # Apply filters
            if st.session_state.filter != 'all':
                if st.session_state.filter not in [label.lower() for label in email['labels']]:
                    continue
                    
            st.markdown(f"""
            <div class='email-box'>
                <div class='email-header'>📨 {email['subject']}</div>
                <div>From: {email['from']}</div>
                <div>Date: {email['date']}</div>
                <div>Labels: {', '.join(email['labels'])}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("View Details", key=f"view_{email['id']}"):
                st.session_state.selected_email = email
    
    with col2:
        st.subheader("📝 Message Details")
        if st.session_state.selected_email:
            email = st.session_state.selected_email
            st.info(f"📧 From: {email['from']}")
            st.warning(f"📅 Date: {email['date']}")
            st.success(f"🏷️ Labels: {', '.join(email['labels'])}")
            st.text_area("Message:", email['body'], height=200, disabled=True)
            
            # AI Actions
            st.markdown("### 🤖 AI Assistant")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📝 Generate Response"):
                    response = AI_RESPONSES.get(email['id'], "Thank you for your email. I'll review and respond shortly.")
                    st.session_state.responses[email['id']] = response
            
            with col2:
                if st.button("🏷️ Suggest Labels"):
                    suggested_labels = ["Follow-up", "Urgent", "Review"]
                    st.info(f"Suggested Labels: {', '.join(suggested_labels)}")
            
            if email['id'] in st.session_state.responses:
                st.markdown("### 📨 Generated Response:")
                response = st.text_area("Edit Response:", st.session_state.responses[email['id']], height=300)
                if st.button("✉️ Send Response"):
                    st.success("Response sent successfully! (Demo Mode)")
                    st.balloons()
        else:
            st.info("👈 Select an email from the inbox to view details")

elif st.session_state.page == 'composer':
    st.header("✍️ New Email")
    with st.form("email_composer"):
        to_email = st.text_input("To:")
        subject = st.text_input("Subject:")
        body = st.text_area("Message:", height=300)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("📝 Draft"):
                st.success("Email saved as draft! (Demo Mode)")
        with col2:
            if st.form_submit_button("✉️ Send"):
                st.success("Email sent successfully! (Demo Mode)")
                st.balloons()

elif st.session_state.page == 'templates':
    st.header("📝 Email Templates")
    
    # Template list
    for name, template in AI_RESPONSES.items():
        with st.expander(f"📄 {name}"):
            st.markdown(f"**Subject:** Re: {{original_subject}}")
            st.markdown("**Body:**")
            st.text_area("", template, height=200, key=f"template_{name}")
            if st.button("Use Template", key=f"use_{name}"):
                st.session_state.page = 'composer'
                st.rerun()
    
    # Add new template
    st.markdown("### ➕ Add New Template")
    with st.form("new_template"):
        template_name = st.text_input("Template Name:")
        template_subject = st.text_input("Subject:")
        template_body = st.text_area("Body:", height=200)
        if st.form_submit_button("Save Template"):
            st.success("Template saved! (Demo Mode)")

elif st.session_state.page == 'auto_reply':
    st.header("🤖 Auto-Reply Rules")
    
    # Add new rule
    with st.form("auto_reply_rule"):
        st.subheader("Add New Rule")
        condition = st.text_input("When email contains:")
        response = st.text_area("Send this response:", height=150)
        if st.form_submit_button("Add Rule"):
            st.success("Auto-reply rule added! (Demo Mode)")
    
    # Existing rules
    st.subheader("Existing Rules")
    sample_rules = [
        {"condition": "urgent", "response": "I'll look into this right away."},
        {"condition": "meeting", "response": "I'll review and confirm my availability."}
    ]
    for rule in sample_rules:
        with st.expander(f"Rule: Contains '{rule['condition']}'"):
            st.text_area("Response:", rule['response'], height=100)
            if st.button("Delete Rule", key=f"delete_{rule['condition']}"):
                st.success("Rule deleted! (Demo Mode)")

elif st.session_state.page == 'knowledge_base':
    st.header("📚 Knowledge Base")
    
    # Add new entry
    with st.form("knowledge_entry"):
        st.subheader("Add New Entry")
        topic = st.text_input("Topic:")
        content = st.text_area("Content:", height=150)
        if st.form_submit_button("Add Entry"):
            st.success("Knowledge base entry added! (Demo Mode)")
    
    # Existing entries
    st.subheader("Existing Entries")
    sample_entries = [
        {"topic": "Project Guidelines", "content": "Standard project workflow and guidelines..."},
        {"topic": "Common Responses", "content": "Frequently used email responses..."}
    ]
    for entry in sample_entries:
        with st.expander(f"📖 {entry['topic']}"):
            st.text_area("Content:", entry['content'], height=100)
            if st.button("Delete Entry", key=f"delete_{entry['topic']}"):
                st.success("Entry deleted! (Demo Mode)")

elif st.session_state.page == 'settings':
    st.header("⚙️ Settings")
    
    with st.expander("👤 User Settings"):
        st.text_input("Display Name:", "Demo User")
        st.text_input("Email Signature:", "Best regards,\nDemo User")
        if st.button("Save User Settings"):
            st.success("Settings saved! (Demo Mode)")
    
    with st.expander("🎨 Appearance"):
        st.selectbox("Theme:", ["Light", "Dark", "System"])
        st.checkbox("Show email preview")
        if st.button("Save Appearance"):
            st.success("Appearance settings saved! (Demo Mode)")
    
    with st.expander("📧 Email Settings"):
        st.number_input("Emails per page:", min_value=10, max_value=50, value=25)
        st.checkbox("Send read receipts")
        st.checkbox("Enable smart compose")
        if st.button("Save Email Settings"):
            st.success("Email settings saved! (Demo Mode)")
    
    with st.expander("🤖 AI Assistant Settings"):
        st.slider("Response creativity:", 0, 100, 50)
        st.multiselect("Enable AI features:", 
            ["Smart Compose", "Response Generation", "Label Suggestions"],
            ["Response Generation", "Label Suggestions"]
        )
        if st.button("Save AI Settings"):
            st.success("AI settings saved! (Demo Mode)")