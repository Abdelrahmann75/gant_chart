from dotenv import load_dotenv
load_dotenv()  # Load environment variables for the entire app
import streamlit as st
from pathlib import Path
from streamlit import session_state as state
import sqlite3
from typing import Optional, Tuple
from datetime import datetime
from utils.login_panel import AuthManager

# Set the page layout and title
st.set_page_config(layout="wide", page_title="DFMS")

def login_page():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">

<div style="text-align:center; padding:40px 0; font-family:'Montserrat', sans-serif;">
    <h1 style="font-size: 42px; color:#002244; font-weight:700; letter-spacing:-1px;">
        IPR Energy Intelligence Portal
    </h1>
    <p style="font-size:18px; color:#444;">
        Unified Production Dashboards, Forecasting, and Visualization
    </p>
    <hr style="width:55%; border:1px solid #d4af37; margin:25px auto;">
    <p style="font-size:16px; color:#777;">
        Connecting to IPR Databases... 🌐
    </p>
</div>
""", unsafe_allow_html=True)

    # Updated CSS with autofill prevention and wider tabs
    st.markdown("""
    <style>
    /* Widen the main content area */
    .main .block-container {
        max-width: 90%;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* Widen tabs */
    .stTabs {
        max-width: 600px;
        margin: 0 auto 20px auto;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
        justify-content: center;
    }

    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 8px;
        padding: 0px 24px;
        font-weight: 600;
        font-size: 16px;
        border: 2px solid #e0e0e0;
        color: #555;
        transition: all 0.3s ease;
        flex: 1;
        max-width: 280px;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f0f7ff;
        border-color: #2196F3;
        color: #2196F3;
        transform: translateY(-2px);
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-color: #667eea;
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    /* Form styling */
    .stTextInput > div > div > input {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        padding: 12px;
        font-size: 15px;
        transition: border-color 0.3s ease;
        width: 100% !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    /* Prevent autofill styling */
    input:-webkit-autofill,
    input:-webkit-autofill:hover,
    input:-webkit-autofill:focus,
    input:-webkit-autofill:active {
        -webkit-box-shadow: 0 0 0 1000px white inset !important;
        box-shadow: 0 0 0 1000px white inset !important;
        -webkit-text-fill-color: #555 !important;
    }

    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        font-size: 16px;
        padding: 12px 24px;
        transition: all 0.3s ease;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
    }

    /* Info box styling */
    .element-container:has(.stAlert) {
        margin-top: 10px;
        margin-bottom: 10px;
    }

    div[data-baseweb="notification"] {
        border-radius: 8px;
        border-left: 4px solid #2196F3;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <form autocomplete="off" style="display:none;">
            <input type="text" name="fake-username" autocomplete="off">
            <input type="password" name="fake-password" autocomplete="new-password">
        </form>
    """, unsafe_allow_html=True)

    with st.container():
        col1, col2, col3 = st.columns([1, 1.5, 1])
        with col2:
            tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
            
            with tab1:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.form("login_form", clear_on_submit=True):
                    username = st.text_input(
                        "👤 Username", 
                        placeholder="Enter your username", 
                        key="login_user",
                        autocomplete="off"
                    )
                    password = st.text_input(
                        "🔑 Password", 
                        type="password", 
                        placeholder="Enter your password", 
                        key="login_pass",
                        autocomplete="new-password"
                    )
                    
                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        login_button = st.form_submit_button("Login →", use_container_width=True)
                    
                    if login_button:
                        success, user_id, message = AuthManager.verify_user(username, password)
                        
                        if success:
                            # Log the login and get session token
                            login_id, session_token = AuthManager.log_login(user_id)
                            
                            # Store in session state
                            state.authenticated = True
                            state.username = username
                            state.user_id = user_id
                            state.login_id = login_id
                            state.session_token = session_token  # IMPORTANT!
                            
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
            
            with tab2:
                st.markdown("<br>", unsafe_allow_html=True)
                st.info("ℹ️ Password for all users: **ipr123**")
                with st.form("register_form", clear_on_submit=True):
                    new_username = st.text_input(
                        "👤 Choose Username", 
                        placeholder="Enter new username", 
                        key="reg_user",
                        autocomplete="off"
                    )
                    confirm_password = st.text_input(
                        "🔑 Confirm Password", 
                        type="password", 
                        placeholder="Enter password: ipr123", 
                        key="reg_pass",
                        autocomplete="new-password"
                    )
                    
                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        register_button = st.form_submit_button("Register →", use_container_width=True)
                    
                    if register_button:
                        success, user_id, message = AuthManager.create_user(new_username, confirm_password)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                        else:
                            st.error(message)
            
            st.markdown("---")
            if st.button("🔄 Clear Cache", use_container_width=True):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("🔄 Cache cleared successfully!")

if not getattr(state, 'authenticated', False):
    login_page()
else:
    def main_app():
        base_path = Path(__file__).parent / "my_pages"
        llm_path = Path(__file__).parent / "LLM_SQL"

        # Define all pages with their sections
        pages_config = {
            "🤖 AI Assistant": [
                {"file": "app.py", "title": "Chat Bot", "icon": "💬", "path": llm_path}
            ],
            "📊 Production Dashboards": [
                {"file": "multilevel_analysis.py", "title": "Production Hierarchy", "icon": "📈", "path": base_path},
                {"file": "metrics.py", "title": "Production Metrics", "icon": "📈", "path": base_path},
                {"file": "prod_differ.py", "title": "Production Differ", "icon": "📉", "path": base_path},
                {"file": "2IPR_analysis.py", "title": "Production Plots", "icon": "📊", "path": base_path},
                {"file": "bi_weekly.py", "title": "Bi Weekly Report", "icon": "📋", "path": base_path}
                

            ],
            "🔭 Well Data": [
                {"file": "file_vis.py", "title": "Well CPI", "icon": "🔭", "path": base_path},
                {"file": "wc_cont.py", "title": "Bubble Maps & Static Pressure", "icon": "📍", "path": base_path}
            ],
            "🌟 Polaris Forecast Engine": [
                {"file": "arps.py", "title": "Production Planner", "icon": "📈", "path": base_path},
                {"file": "admin_panel.py", "title": "Control Center", "icon": "🖥️", "path": base_path}
            ]
        }

        # Professional Modern CSS for section tabs
        st.markdown("""
        <style>
        /* Main container for section tabs */
        .section-tabs-container {
            background: linear-gradient(135deg, #2c5f8d 0%, #3a7cb8 50%, #5a9fd4 100%);
            padding: 30px 40px;
            border-radius: 20px;
            margin: 20px 0 35px 0;
            box-shadow: 0 10px 40px rgba(44, 95, 141, 0.4);
            position: relative;
            overflow: hidden;
        }

        /* Animated background effect */
        .section-tabs-container::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.08) 0%, transparent 70%);
            animation: pulse 15s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { transform: translate(0, 0); }
            50% { transform: translate(10px, 10px); }
        }

        /* Button container alignment */
        div[data-testid="column"] {
            display: flex;
            align-items: stretch;
            position: relative;
            z-index: 1;
        }

        /* Style all section buttons */
        div[data-testid="column"] .stButton {
            width: 100%;
        }

        div[data-testid="column"] .stButton button {
            width: 100% !important;
            min-height: 70px !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
            font-size: 15px !important;
            padding: 18px 15px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            border: 2px solid transparent !important;
            position: relative !important;
            overflow: hidden !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            line-height: 1.4 !important;
        }

        /* Shimmer effect on buttons */
        div[data-testid="column"] .stButton button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
            transition: left 0.5s;
        }

        div[data-testid="column"] .stButton button:hover::before {
            left: 100%;
        }

        /* INACTIVE buttons (secondary) - Blue with transparency */
        div[data-testid="column"] .stButton button[kind="secondary"] {
            background: rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(10px) !important;
            color: white !important;
            border: 2px solid rgba(255, 255, 255, 0.4) !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15) !important;
            text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
        }

        /* ACTIVE button (primary) - Your custom blue #5DADE2 */
        div[data-testid="column"] .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%) !important;
            color: white !important;
            border: 2px solid #5DADE2 !important;
            box-shadow: 0 6px 20px rgba(93, 173, 226, 0.5),
                        0 0 0 1px rgba(255, 255, 255, 0.2) inset !important;
            font-weight: 700 !important;
            transform: translateY(-3px) !important;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
        }

        /* Prevent color change on click/press */
        div[data-testid="column"] .stButton button[kind="primary"]:active {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%) !important;
            color: white !important;
        }

        div[data-testid="column"] .stButton button[kind="primary"]:focus {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%) !important;
            color: white !important;
            outline: none !important;
        }

        /* ALL PRIMARY BUTTONS IN APP - Apply same color */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%) !important;
            color: white !important;
            border: 2px solid #5DADE2 !important;
            box-shadow: 0 4px 15px rgba(93, 173, 226, 0.4) !important;
            transition: all 0.3s ease !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #6FB9E8 0%, #5DADE2 100%) !important;
            box-shadow: 0 6px 20px rgba(93, 173, 226, 0.5) !important;
            transform: translateY(-2px) !important;
        }

        .stButton > button[kind="primary"]:active,
        .stButton > button[kind="primary"]:focus {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%) !important;
            color: white !important;
        }

        /* Sidebar navigation styling */
        [data-testid="stSidebarNav"] {
            background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 15px;
            border-radius: 15px;
            margin-top: 20px;
        }

        [data-testid="stSidebarNav"] a {
            background: white;
            border-radius: 12px;
            margin-bottom: 10px;
            padding: 14px 16px;
            border: 2px solid #e0e0e0;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        }

        [data-testid="stSidebarNav"] a:hover {
            border-color: #5DADE2;
            background: linear-gradient(135deg, #E8F6FC 0%, #D4EEF9 100%);
            transform: translateX(8px);
            box-shadow: 0 4px 12px rgba(93, 173, 226, 0.3);
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%);
            color: white;
            border-color: #5DADE2;
            font-weight: 600;
            box-shadow: 0 4px 15px rgba(93, 173, 226, 0.4);
        }

        /* Sidebar logout button */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #5DADE2 0%, #4A9FD4 100%) !important;
            color: white !important;
            border: 2px solid #5DADE2 !important;
        }

        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #6FB9E8 0%, #5DADE2 100%) !important;
        }

        /* Responsive design */
        @media (max-width: 1200px) {
            div[data-testid="column"] .stButton button {
                min-height: 60px !important;
                font-size: 14px !important;
                padding: 14px 10px !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)

        # Initialize selected section
        if "selected_section" not in st.session_state:
            st.session_state.selected_section = list(pages_config.keys())[0]

        # Sidebar with user info
        with st.sidebar:
            st.logo('IPR-275.png')
            st.markdown("---")
            user_id, username = AuthManager.get_current_user()
            st.markdown(f"### 👤 **{username}**")
            st.markdown("---")
            
            if st.button("🚪 Logout", use_container_width=True, type="primary"):
                AuthManager.logout()

        # Section tabs container (NO TITLE)
        st.markdown('<div class="section-tabs-container">', unsafe_allow_html=True)

        cols = st.columns(len(pages_config))
        for idx, (section_name, _) in enumerate(pages_config.items()):
            with cols[idx]:
                if st.button(
                    section_name,
                    key=f"section_{idx}",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_section == section_name else "secondary"
                ):
                    st.session_state.selected_section = section_name
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Create navigation for selected section
        selected_section = st.session_state.selected_section
        selected_pages = pages_config[selected_section]
        
        # Build page objects
        page_objects = []
        for page in selected_pages:
            file_path = page["path"] / page["file"]  # Fixed: Use / instead of +
            page_obj = st.Page(file_path, title=page["title"], icon=page["icon"])
            page_objects.append(page_obj)

        # Run navigation
        pg = st.navigation(page_objects)
        pg.run()

    main_app()