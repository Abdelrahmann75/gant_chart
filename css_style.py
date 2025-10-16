import streamlit as st


def apply_custom_css_login():
    """
    Apply custom CSS styling for the DFMS Streamlit application.
    This function handles all visual styling including login page, cards, and filters.
    """
    st.markdown("""
        <style>
            /* ===== GLOBAL STYLES ===== */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
            
            * {
                font-family: 'Inter', 'Segoe UI', sans-serif;
            }
            
            /* Remove default Streamlit padding */
            .block-container {
                padding-top: 3rem !important;
                padding-bottom: 3rem !important;
            }
            
            /* ===== BACKGROUND ===== */
            .stApp {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                background-attachment: fixed;
            }
            
            /* Alternative gradient backgrounds */
            .stApp::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.4), transparent 50%),
                    radial-gradient(circle at 80% 80%, rgba(200, 210, 225, 0.3), transparent 50%);
                pointer-events: none;
                z-index: 0;
            }
            
            /* ===== LOGIN PAGE CONTAINER ===== */
            [data-testid="stForm"] {
                background: rgba(255, 255, 255, 0.98) !important;
                padding: 3rem 2.5rem !important;
                border-radius: 20px !important;
                box-shadow: 
                    0 20px 60px rgba(0, 0, 0, 0.15),
                    0 0 100px rgba(255, 255, 255, 0.5) inset !important;
                backdrop-filter: blur(20px) !important;
                -webkit-backdrop-filter: blur(20px) !important;
                border: 1px solid rgba(255, 255, 255, 0.6) !important;
                width: 480px !important;
                max-width: 90% !important;
                margin: 0 auto !important;
                animation: fadeInScale 0.6s ease-out;
            }
            
            @keyframes fadeInScale {
                from {
                    opacity: 0;
                    transform: scale(0.9) translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: scale(1) translateY(0);
                }
            }
            
            /* ===== TITLE STYLING ===== */
            .stApp h1 {
                text-align: center !important;
                color: #2c3e50 !important;
                font-size: 3rem !important;
                font-weight: 700 !important;
                text-shadow: 0 2px 10px rgba(0, 0, 0, 0.1) !important;
                margin-bottom: 2rem !important;
                letter-spacing: -1px !important;
            }
            
            /* ===== INPUT FIELDS ===== */
            [data-testid="stForm"] input {
                background: rgba(248, 250, 252, 0.8) !important;
                border: 2px solid rgba(226, 232, 240, 0.8) !important;
                border-radius: 12px !important;
                padding: 0.85rem 1rem !important;
                font-size: 1rem !important;
                transition: all 0.3s ease !important;
                color: #1e293b !important;
            }
            
            [data-testid="stForm"] input:focus {
                background: white !important;
                border-color: #667eea !important;
                box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1) !important;
                outline: none !important;
            }
            
            [data-testid="stForm"] input::placeholder {
                color: #94a3b8 !important;
            }
            
            /* ===== LABELS ===== */
            [data-testid="stForm"] label {
                color: #334155 !important;
                font-weight: 600 !important;
                font-size: 0.95rem !important;
                margin-bottom: 0.5rem !important;
                display: block !important;
            }
            
            [data-testid="stForm"] label p {
                font-weight: 600 !important;
                font-size: 0.95rem !important;
                color: #334155 !important;
            }
            
            /* ===== LOGIN BUTTON ===== */
            [data-testid="stForm"] button[kind="primaryFormSubmit"] {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
                color: white !important;
                border: none !important;
                border-radius: 12px !important;
                padding: 0.85rem 2rem !important;
                font-size: 1.05rem !important;
                font-weight: 600 !important;
                width: 100% !important;
                margin-top: 1rem !important;
                cursor: pointer !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 4px 15px rgba(59, 130, 246, 0.4) !important;
                text-transform: none !important;
            }
            
            [data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 6px 25px rgba(59, 130, 246, 0.5) !important;
            }
            
            [data-testid="stForm"] button[kind="primaryFormSubmit"]:active {
                transform: translateY(0) !important;
            }
            
            /* ===== CLEAR CACHE BUTTON ===== */
            [data-testid="stForm"] button[kind="formSubmit"]:not([kind="primaryFormSubmit"]) {
                background: rgba(248, 250, 252, 0.9) !important;
                color: #64748b !important;
                border: 2px solid #e2e8f0 !important;
                border-radius: 12px !important;
                padding: 0.75rem 1.5rem !important;
                font-size: 0.95rem !important;
                font-weight: 500 !important;
                width: 100% !important;
                margin-top: 0.5rem !important;
                transition: all 0.3s ease !important;
            }
            
            [data-testid="stForm"] button[kind="formSubmit"]:not([kind="primaryFormSubmit"]):hover {
                background: white !important;
                border-color: #cbd5e1 !important;
                color: #475569 !important;
                transform: translateY(-1px) !important;
            }
            
            /* ===== DIVIDER LINE ===== */
            [data-testid="stForm"] hr {
                margin: 2rem 0 1.5rem 0 !important;
                border: none !important;
                border-top: 1px solid rgba(226, 232, 240, 0.6) !important;
            }
            
            /* ===== ERROR MESSAGES ===== */
            .stAlert {
                background: rgba(254, 226, 226, 0.95) !important;
                color: #991b1b !important;
                border: 1px solid rgba(239, 68, 68, 0.3) !important;
                border-radius: 10px !important;
                padding: 0.75rem 1rem !important;
                margin-top: 1rem !important;
            }
            
            /* ===== SUCCESS MESSAGES ===== */
            .stSuccess {
                background: rgba(220, 252, 231, 0.95) !important;
                color: #065f46 !important;
                border: 1px solid rgba(34, 197, 94, 0.3) !important;
                border-radius: 10px !important;
                padding: 0.75rem 1rem !important;
                margin-top: 1rem !important;
            }
            
            /* ===== LOCK ICON STYLING ===== */
            .stApp > div:first-child img {
                display: none !important;
            }
            
            /* ===== MODERN CARDS (for main app) ===== */
            .card {
                background: white !important;
                padding: 1.5rem;
                border-radius: 16px;
                box-shadow: 
                    0 4px 6px -1px rgba(0, 0, 0, 0.1),
                    0 2px 4px -1px rgba(0, 0, 0, 0.06);
                transition: all 0.3s ease;
                border: 1px solid rgba(0, 0, 0, 0.05);
            }
            
            .card:hover {
                transform: translateY(-4px);
                box-shadow: 
                    0 20px 25px -5px rgba(0, 0, 0, 0.1),
                    0 10px 10px -5px rgba(0, 0, 0, 0.04);
            }
            
            /* ===== FILTER SECTION ===== */
            .filter-section {
                background-color: #eaf2f8;
                padding: 1.25rem;
                border-radius: 12px;
                margin: 1rem 0;
                border-left: 4px solid #3b82f6;
                transition: all 0.3s ease;
            }
            
            .filter-section:hover {
                background-color: #dce8f2;
                border-left-width: 6px;
            }
            
            /* ===== SIDEBAR STYLING (for main app) ===== */
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
            }
            
            [data-testid="stSidebar"] .stButton > button {
                width: 100%;
                border-radius: 10px;
                transition: all 0.3s ease;
            }
            
            /* ===== LOGOUT BUTTON ===== */
            [data-testid="stSidebar"] button {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%) !important;
                color: white !important;
                border: none !important;
                padding: 0.75rem 1.5rem !important;
                font-weight: 600 !important;
                border-radius: 10px !important;
                transition: all 0.3s ease !important;
            }
            
            [data-testid="stSidebar"] button:hover {
                background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%) !important;
                transform: translateY(-2px) !important;
                box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4) !important;
            }
            
            /* ===== RESPONSIVE DESIGN ===== */
            @media (max-width: 768px) {
                [data-testid="stForm"] {
                    padding: 2rem 1.5rem !important;
                    margin: 1rem !important;
                }
                
                .stApp h1 {
                    font-size: 2rem !important;
                }
            }
            
            /* ===== SCROLLBAR ===== */
            ::-webkit-scrollbar {
                width: 10px;
                height: 10px;
            }
            
            ::-webkit-scrollbar-track {
                background: rgba(241, 245, 249, 0.5);
                border-radius: 5px;
            }
            
            ::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
                border-radius: 5px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
            }
            
            /* ===== REMOVE STREAMLIT BRANDING ===== */
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
        </style>
    """, unsafe_allow_html=True)
# =================== PROFESSIONAL CSS STYLING ===================
def load_custom_css_admin():
    st.markdown("""
    <style>
    /* Main Container */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 10px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: white;
        border-radius: 8px;
        padding: 0 24px;
        font-weight: 600;
        border: 2px solid transparent;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e3f2fd;
        border-color: #2196f3;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-color: #667eea;
    }
    
    /* Cards */
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        margin-bottom: 1rem;
    }
    
    .metric-card h3 {
        margin: 0 0 0.5rem 0;
        color: #667eea;
        font-size: 1rem;
    }
    
    .metric-card p {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        color: #2c3e50;
    }
    
    /* Info boxes */
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
    
    .success-box {
        background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #4caf50;
        margin: 1rem 0;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #ff9800;
        margin: 1rem 0;
    }
    
    /* Buttons */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    /* DataFrames */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Section Headers */
    .section-header {
        color: #2c3e50;
        border-bottom: 3px solid #667eea;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        font-weight: 700;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        border-top: 2px solid #e0e0e0;
    }
    
    /* Coming Soon */
    .coming-soon {
        text-align: center;
        padding: 4rem 2rem;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        border-radius: 10px;
        margin: 2rem 0;
    }
    
    .coming-soon h2 {
        color: #667eea;
        font-size: 2rem;
        margin-bottom: 1rem;
    }
    
    .coming-soon p {
        color: #7f8c8d;
        font-size: 1.1rem;
    }
    </style>
    """, unsafe_allow_html=True)



def load_custom_css_main():
  st.markdown("""
  <style>
  /* Main Container */
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
  
  /* Tab Styling */
  .stTabs [data-baseweb="tab-list"] {
      gap: 8px;
      background-color: #f8f9fa;
      padding: 10px;
      border-radius: 10px;
  }
  
  .stTabs [data-baseweb="tab"] {
      height: 50px;
      background-color: white;
      border-radius: 8px;
      padding: 0 24px;
      font-weight: 600;
      border: 2px solid transparent;
      transition: all 0.3s ease;
  }
  
  .stTabs [data-baseweb="tab"]:hover {
      background-color: #e3f2fd;
      border-color: #2196f3;
  }
  
  .stTabs [aria-selected="true"] {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border-color: #667eea;
  }
  
    
    
  
  
  .success-box {
      background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%);
      padding: 1rem;
      border-radius: 8px;
      border-left: 4px solid #4caf50;
      margin: 1rem 0;
  }
  
  
  
  /* Buttons */
  .stButton > button {
      width: 100%;
      border-radius: 8px;
      font-weight: 600;
      transition: all 0.3s ease;
  }
  
  .stButton > button:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }
  
  /* DataFrames */
  .dataframe {
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  
  

  
  </style>
  """, unsafe_allow_html=True)

