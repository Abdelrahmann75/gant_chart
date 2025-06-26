from dotenv import load_dotenv
load_dotenv()  # Load environment variables for the entire app
import streamlit as st
from streamlit import session_state as state

# Set the page layout and title
st.set_page_config(layout="wide", page_title="DFMS", page_icon="🔒")

# Custom CSS for styling with updated colors and sizes
st.markdown("""
    <style>
        /* Modern login box with glassmorphism (reduced size) */
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
        /* Modern cards */
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
        /* Filter section styling: very light blue background */
        .filter-section {
            background-color: #eaf2f8;
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
        }
    </style>
""", unsafe_allow_html=True)

# User credentials (For demo purposes - In production, use secure authentication)
USERS = {
    "admin": "ipr123",
    "user": "password123"
}

def authenticate(username, password):
    return USERS.get(username) == password

def login_page():
    st.title("🔒 ")
    
    
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            # Wrap the form inside a div with the login-box class for glassmorphism styling
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

                            # Cache clear button with a confirmation
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
        # Add logout button in sidebar
        with st.sidebar:
            
            for i in range(18):
                st.write(" ")
            if st.button("🚪 Logout"):
                state.authenticated = False
                st.rerun()

        # Common base paths for pages
        base_path = "Y:/IPR_App/update/my_pages/"
        llm_path = "Y:/IPR_App/update/my_pages/LLM_SQL/"  # Ensure trailing slash

        # Define page details in a list
        pages = [
            {"file": "1PetroSilah_Update.py", "title": "PetroSilah Update", "icon": "🔄", "section": "Updating Database"},
            {"file": "metrics.py", "title": "Production Metrics", "icon": "📊", "section": "Detailed Analysis"},
            {"file": "prod_differ.py", "title": "Production Differ", "icon": "📊", "section": "Detailed Analysis"},
            {"file": "2IPR_analysis.py", "title": "Production plots", "icon": "📉", "section": "Detailed Analysis"},
            {"file": "eho_update.py", "title": "Alamein Update", "icon": "🔄", "section": "Updating Database"},
            {"file": "dca.py", "title": "Decline Curve Analysis", "icon": "📉", "section": "Detailed Analysis"},
            {"file": "cases_trial.py", "title": "Production Profile", "icon": "📉", "section": "Detailed Analysis"},
            {"file": "bi_weekly.py", "title": "Bi Weekly Report", "icon": "📊", "section": "Detailed Analysis"},
            {"file": "file_vis.py", "title": "Well CPI", "icon": "🔭", "section": "Well Data"},
            {"file": "app.py", "title": "Chat Bot", "icon": "📊", "section": "AI Assistant"}
        ]

        # Group pages into sections dynamically
        sections = {"AI Assistant":[],"Updating Database": [], "Detailed Analysis": [],"Well Data":[]}
        for page in pages:
            # Use llm_path for the 'app.py' page; otherwise use base_path
            if page["file"] == "app.py":
                file_path = llm_path + page["file"]
            else:
                file_path = base_path + page["file"]

            # Create the page object using the resolved file path
            page_obj = st.Page(file_path, title=page["title"], icon=page["icon"])
            sections[page["section"]].append(page_obj)

        # Navigation setup with sections
        pg = st.navigation(sections)

        # Add logo and image (if available, adjust paths as necessary)
        st.logo('IPR-275.png')
        st.image('IPR-275.png')

        # Run navigation
        pg.run()

    main_app() 