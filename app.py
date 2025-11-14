import streamlit as st


# Inject CSS
st.markdown("""
<style>
.big-button {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white !important;
    padding: 20px 50px;
    font-size: 20px;
    font-weight: bold;
    text-decoration: none;
    border-radius: 10px;
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    transition: all 0.3s ease;
    text-align: center;
    margin: 20px 0;
}

.big-button:hover {
    transform: translateY(-3px);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    text-decoration: none;
}

.info-box {
    background: white;
    padding: 25px;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    margin: 15px 0;
}

.feature-item {
    color: #2c3e50;
    font-size: 16px;
    margin: 10px 0;
    padding-left: 25px;
}

.feature-item:before {
    content: "✓ ";
    color: #27ae60;
    font-weight: bold;
    font-size: 18px;
    margin-left: -25px;
    margin-right: 10px;
}
</style>
""", unsafe_allow_html=True)

# Main title
st.title("💬 Alamein & Petrosilah Chat Bot")
st.markdown("---")

# Create columns
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.subheader("🛢️ SQL Chatbot")
    st.write("Access our powerful SQL Chatbot interface for natural language database queries.")
    
    st.markdown("""
    <div class="feature-item">Natural language to SQL conversion</div>
    <div class="feature-item">Multi-select helper for wells, zones, and fields</div>
    <div class="feature-item">Interactive data visualization</div>
    <div class="feature-item">Export results to CSV</div>
    <div class="feature-item">Professional, user-friendly interface</div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin: 30px 0;">
        <a href="https://iprdashboard.z6.web.core.windows.net/" target="_blank" class="big-button">
            🚀 Launch SQL Chatbot
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    
    
    st.markdown('<div class="info-box">', unsafe_allow_html=True)
    st.subheader("💡 Tips")
    st.markdown("""
    • Use the multi-select helper  
    • Try natural language queries  
    • Export results to CSV  
    • Use fullscreen mode
    """)
    st.markdown('</div>', unsafe_allow_html=True)

