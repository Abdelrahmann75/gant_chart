from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from streamlit import session_state as state
from pathlib import Path

# Set the page layout and title
st.set_page_config(layout="wide", page_title="IPR Analysis Suite", page_icon="🔒")

# Custom CSS for styling
st.markdown("""
    <style>
        .login-box {
            max-width: 350px;
            padding: 2rem;
            margin: auto;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 16px;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        [data-testid="stVerticalBlock"] label:hover {
            background: rgba(255, 255, 255, 0.1) !important;
        }
        [data-testid="stVerticalBlock"] label div p {
            font-weight: 500 !important;
            font-size: 1.1rem !important;
        }
        .card {
            background: white !important;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        .card:hover {
            transform: translateY(-5px);
        }
        .filter-section {
            background-color: #eaf2f8;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# User credentials
USERS = {
    "test": "ipr123",
    "user": "password123"
}

def authenticate(username, password):
    return USERS.get(username) == password

def login_page():
    st.title("🔒 IPR Analysis Suite")
    st.markdown("<h3 style='text-align: center; color: var(--text);'>Welcome! Please Login</h3>", unsafe_allow_html=True)
    
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<div class='login-box'>", unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("👤 Username", placeholder="Enter your username")
                password = st.text_input("🔑 Password", type="password", placeholder="Enter your password")
                login_button = st.form_submit_button("Login →")
                
                if login_button:
                    if authenticate(username, password):
                        state.authenticated = True
                        state.username = username
                        st.rerun()
                    else:
                        st.error("Invalid username or password")
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("---")
                if st.form_submit_button("Clear Cache"):
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.success("🔄 Cache cleared successfully!")

# Check authentication state
if not getattr(state, 'authenticated', False):
    login_page()
else:
    def main_app():
        with st.sidebar:
            st.write(f"Welcome, {state.username}!")
            if st.button("🚪 Logout"):
                state.authenticated = False
                st.rerun()

        # Paths relative to this script
        base_path = Path(__file__).parent / "my_pages"
        llm_path = Path(__file__).parent / "LLM_SQL"

       

        pages = [
            
            {"file": "metrics.py", "title": "Production Metrics", "icon": "📊", "section": "Detailed Analysis"},
            {"file": "prod_differ.py", "title": "Production Differ", "icon": "📊", "section": "Detailed Analysis"},
            {"file": "2IPR_analysis.py", "title": "Production plots", "icon": "📉", "section": "Detailed Analysis"},
       
            {"file": "dca.py", "title": "Decline Curve Analysis", "icon": "📉", "section": "Detailed Analysis"},
            {"file": "cases_trial.py", "title": "Production Profile", "icon": "📉", "section": "Detailed Analysis"},
            {"file": "bi_weekly.py", "title": "Bi Weekly Report", "icon": "📊", "section": "Detailed Analysis"},
            {"file": "file_vis.py", "title": "Well CPI", "icon": "🔭", "section": "Well Data"},
            {"file": "app.py", "title": "Chat Bot", "icon": "📊", "section": "AI Assistant"}
        ]

        # Group pages into sections
        sections = {"AI Assistant": [], "Updating Database": [], "Detailed Analysis": [],"Well Data" : []}
        for page in pages:
            if page["file"] == "app.py":
                file_path = llm_path / page["file"]
            else:
                file_path = base_path / page["file"]

            page_obj = st.Page(str(file_path), title=page["title"], icon=page["icon"])
            sections[page["section"]].append(page_obj)

        # Navigation
        pg = st.navigation(sections)

        # Logo and image
        st.logo( "IPR-275.png")
        st.image("IPR-275.png")

        # Run selected page
        pg.run()

    main_app()
