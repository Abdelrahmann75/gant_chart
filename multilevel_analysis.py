import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# Enhanced CSS styling
st.markdown(
    """
    <style>
    /* Main container styling */
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
    }
    
    /* Card-like containers */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Title styling */
    h1 {
        color: #2c3e50;
        text-align: center;
        font-weight: 700;
        font-size: 2.5rem;
        margin-bottom: 1rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    h2, h3 {
        color: #34495e;
        font-weight: 600;
    }
    
    /* Filter section styling */
    .filter-container {
        background: white;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    /* Selectbox and input styling */
    .stSelectbox > div > div {
        background-color: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
        transition: all 0.3s ease;
    }
    
    .stSelectbox > div > div:hover {
        border-color: #667eea;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
    }
    
    /* Multiselect styling */
    .stMultiSelect > div > div {
        background-color: #ffffff;
        border: 2px solid #e0e0e0;
        border-radius: 10px;
    }
    
    /* Radio button styling */
    .stRadio > div {
        background-color: white;
        padding: 1rem;
        border-radius: 10px;
        border: 2px solid #e0e0e0;
    }
    
    /* Slider styling */
    .stSlider > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        color: #667eea;
        font-weight: 700;
    }
    
    /* Info boxes */
    .stAlert {
        border-radius: 10px;
        border-left: 5px solid #667eea;
    }
    
    /* Divider */
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #667eea, transparent);
    }
    
    /* Chart container */
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-top: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Title
st.markdown("<h1>📊 Production Hierarchy Dashboard</h1>", unsafe_allow_html=True)

# Database connection function
@st.cache_data
def load_data_from_db(db_path, query):
    """Load data from SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.dropna(subset=['date'], inplace=True)
            df.sort_values('date', inplace=True)
        
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Load Alamein data
@st.cache_data
def get_alamein_data():
    db_path = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    query = "SELECT * FROM st_data_plot"
    return load_data_from_db(db_path, query)

# Load Petrosila data
@st.cache_data
def get_petrosila_data():
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    query = "SELECT * FROM st_data"
    return load_data_from_db(db_path, query)

# Color palette for charts
COLOR_PALETTE = [
    '#667eea', '#764ba2', '#f093fb', '#4facfe', '#00f2fe',
    '#43e97b', '#fa709a', '#fee140', '#30cfd0', '#a8edea',
    '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7',
    '#dfe6e9', '#74b9ff', '#a29bfe', '#fd79a8', '#fdcb6e'
]

def get_hierarchy_level(df, selected_fields, selected_zones, selected_unique_ids):
    """Determine the current hierarchy level based on selections"""
    if not selected_fields:
        return "company", "All Company"
    elif len(selected_fields) == 1 and not selected_zones and not selected_unique_ids:
        return "field", selected_fields[0]
    elif selected_zones and len(selected_zones) == 1 and not selected_unique_ids:
        return "zone", selected_zones[0]
    elif selected_fields:
        return "fields", "Selected Fields"
    else:
        return "company", "All Company"

def aggregate_data(df, group_by, metric, date_col='date'):
    """Aggregate data by specified grouping"""
    if df.empty:
        return pd.DataFrame()
    
    if metric == 'wc':
        # Water cut should be averaged
        agg_df = df.groupby([date_col, group_by])[metric].mean().reset_index()
    else:
        # Net and gross should be summed
        agg_df = df.groupby([date_col, group_by])[metric].sum().reset_index()
    
    return agg_df

def create_hierarchical_chart(df, metric, hierarchy_level, level_name, breakdown_by, date_range):
    """Create a hierarchical chart with two subplots"""
    
    # Filter by date range
    df_filtered = df[(df['date'] >= pd.Timestamp(date_range[0])) & (df['date'] <= pd.Timestamp(date_range[1]))].copy()
    
    if df_filtered.empty:
        st.warning("No data available for the selected filters.")
        return None
    
    # Metric display names
    metric_names = {
        'net': 'Net Oil (BOPD)',
        'gross': 'Gross Fluid (BFPD)',
        'wc': 'Water Cut (%)'
    }
    
    # Create subplot figure
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=(
            f'<b>Total {metric_names[metric]} - {level_name}</b>',
            f'<b>Breakdown by {breakdown_by.replace("unique_id", "Well Zone").replace("_", " ").title()}</b>'
        ),
        vertical_spacing=0.12,
        row_heights=[0.5, 0.5]
    )
    
    # First chart: Total aggregated by date
    if metric == 'wc':
        total_by_date = df_filtered.groupby('date')[metric].mean().reset_index()
    else:
        total_by_date = df_filtered.groupby('date')[metric].sum().reset_index()
    
    fig.add_trace(
        go.Scatter(
            x=total_by_date['date'],
            y=total_by_date[metric],
            mode='lines',
            name=f'Total {metric_names[metric]}',
            line=dict(color='#667eea', width=3),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.1)',
            hovertemplate=f'<b>Total {metric_names[metric]}</b><br>Date: %{{x|%Y-%m-%d}}<br>Value: %{{y:.2f}}'
        ),
        row=1, col=1
    )
    
    # Second chart: Breakdown by selected dimension
    breakdown_data = aggregate_data(df_filtered, breakdown_by, metric)
    
    if not breakdown_data.empty:
        unique_items = breakdown_data[breakdown_by].unique()
        
        for idx, item in enumerate(unique_items):
            item_data = breakdown_data[breakdown_data[breakdown_by] == item]
            color = COLOR_PALETTE[idx % len(COLOR_PALETTE)]
            
            fig.add_trace(
                go.Scatter(
                    x=item_data['date'],
                    y=item_data[metric],
                    mode='lines',
                    name=str(item),
                    line=dict(color=color, width=2),
                    hovertemplate=f'<b>{item}</b><br>Date: %{{x|%Y-%m-%d}}<br>Value: %{{y:.2f}}'
                ),
                row=2, col=1
            )
    
    # Update layout
    fig.update_xaxes(
        title_text="Date",
        showgrid=True,
        gridcolor='#e0e0e0',
        showline=True,
        linecolor='#2c3e50',
        row=1, col=1
    )
    
    fig.update_xaxes(
        title_text="Date",
        showgrid=True,
        gridcolor='#e0e0e0',
        showline=True,
        linecolor='#2c3e50',
        row=2, col=1
    )
    
    fig.update_yaxes(
        title_text=metric_names[metric],
        showgrid=True,
        gridcolor='#e0e0e0',
        showline=True,
        linecolor='#2c3e50',
        row=1, col=1
    )
    
    fig.update_yaxes(
        title_text=metric_names[metric],
        showgrid=True,
        gridcolor='#e0e0e0',
        showline=True,
        linecolor='#2c3e50',
        row=2, col=1
    )
    
    fig.update_layout(
        height=900,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.45,
            xanchor="left",
            x=1.02,
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="#2c3e50",
            borderwidth=1
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif", size=12, color="#2c3e50"),
        hovermode='closest',
        margin=dict(l=80, r=150, t=100, b=80)
    )
    
    return fig

# Main application
def main():
    # Company selection
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        company = st.selectbox(
            "🏢 Select Company",
            options=["Alamein", "Petrosilah"],
            index=0
        )
    
    # Load appropriate data
    if company == "Alamein":
        df = get_alamein_data()
    else:
        df = get_petrosila_data()
    
    if df.empty:
        st.error("No data available. Please check database connection.")
        return
    
    with col2:
        metric = st.selectbox(
            "📈 Select Metric",
            options=['net', 'gross', 'wc'],
            format_func=lambda x: {
                'net': 'Net Oil Production',
                'gross': 'Gross Fluid Production',
                'wc': 'Water Cut (%)'
            }[x]
        )
    
    with col3:
        # Get min and max dates from data
        min_date = df['date'].min()
        max_date = df['date'].max()
        
        # Calculate default start date (6 months before today or max_date)
        today = datetime.now()
        six_months_ago = today - timedelta(days=180)  # ~6 months
        
        # Convert to date objects for comparison
        if isinstance(min_date, pd.Timestamp):
            min_date_date = min_date.date()
            max_date_date = max_date.date()
        else:
            min_date_date = min_date
            max_date_date = max_date
        
        today_date = today.date()
        six_months_ago_date = six_months_ago.date()
        
        # Set default start date (ensure it's not before data starts)
        if six_months_ago_date < min_date_date:
            default_start = min_date_date
        else:
            default_start = six_months_ago_date
        
        # Set default end date (use today or max date if data doesn't go to today)
        if today_date > max_date_date:
            default_end = max_date_date
        else:
            default_end = today_date
        
        # Date range slider
        date_range = st.slider(
            "📅 Date Range",
            min_value=min_date_date,
            max_value=max_date_date,
            value=(default_start, default_end),
            format="DD-MMM-YYYY"
        )
        
        # Convert to pandas Timestamps for filtering
        date_range = (pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1]))

    st.markdown("</div>", unsafe_allow_html=True)
    # Hierarchical filters
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    st.markdown("### 🔍 Hierarchical Filters")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        all_fields = ['All'] + sorted(df['field'].dropna().unique().tolist())
        selected_fields_list = st.multiselect(
            "Select Fields",
            options=all_fields,
            default=['All']
        )
        
        if 'All' in selected_fields_list:
            selected_fields = []
        else:
            selected_fields = selected_fields_list
    
    # Filter data for zones based on selected fields
    if selected_fields:
        zone_df = df[df['field'].isin(selected_fields)]
    else:
        zone_df = df
    
    with col2:
        all_zones = ['All'] + sorted(zone_df['zone'].dropna().unique().tolist())
        selected_zones_list = st.multiselect(
            "Select Zones",
            options=all_zones,
            default=['All']
        )
        
        if 'All' in selected_zones_list:
            selected_zones = []
        else:
            selected_zones = selected_zones_list
    
    # Filter data for unique_id based on selected fields and zones
    if selected_fields:
        unique_id_df = df[df['field'].isin(selected_fields)]
    else:
        unique_id_df = df
    
    if selected_zones:
        unique_id_df = unique_id_df[unique_id_df['zone'].isin(selected_zones)]
    
    with col3:
        all_unique_ids = ['All'] + sorted(unique_id_df['unique_id'].dropna().unique().tolist())
        selected_unique_ids_list = st.multiselect(
            "Select Well Zones",
            options=all_unique_ids,
            default=['All']
        )
        
        if 'All' in selected_unique_ids_list:
            selected_unique_ids = []
        else:
            selected_unique_ids = selected_unique_ids_list
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Determine breakdown dimension
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    st.markdown("### 📊 Breakdown Selection")
    
    # Determine available breakdown options based on hierarchy
    if not selected_fields:
        # At company level - can break down by fields
        breakdown_options = ['field']
        breakdown_labels = {'field': 'Fields'}
    elif selected_fields and not selected_zones:
        # At field level - can break down by zones or unique_id
        breakdown_options = ['zone', 'unique_id']
        breakdown_labels = {'zone': 'Zones', 'unique_id': 'Well Zones'}
    elif selected_zones:
        # At zone level - can break down by unique_id
        breakdown_options = ['unique_id']
        breakdown_labels = {'unique_id': 'Well Zones'}
    else:
        breakdown_options = ['field']
        breakdown_labels = {'field': 'Fields'}
    
    breakdown_by = st.radio(
        "Select breakdown dimension for the second chart:",
        options=breakdown_options,
        format_func=lambda x: breakdown_labels.get(x, x),
        horizontal=True
    )
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Filter the dataframe
    df_filtered = df.copy()
    
    if selected_fields:
        df_filtered = df_filtered[df_filtered['field'].isin(selected_fields)]
    
    if selected_zones:
        df_filtered = df_filtered[df_filtered['zone'].isin(selected_zones)]
    
    if selected_unique_ids:
        df_filtered = df_filtered[df_filtered['unique_id'].isin(selected_unique_ids)]
    
    # Determine hierarchy level for title
    hierarchy_level, level_name = get_hierarchy_level(
        df_filtered, selected_fields, selected_zones, selected_unique_ids
    )
    
    # Display summary metrics
    st.markdown("<div class='filter-container'>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    df_date_filtered = df_filtered[
        (df_filtered['date'] >= pd.Timestamp(date_range[0])) &
        (df_filtered['date'] <= pd.Timestamp(date_range[1]))
    ]
    
    with col1:
        total_net = df_date_filtered['net'].sum()
        st.metric("Total Net Oil", f"{total_net:,.0f} BBL")
    
    with col2:
        total_gross = df_date_filtered['gross'].sum()
        st.metric("Total Gross Fluid", f"{total_gross:,.0f} BBL")
    
    with col3:
        avg_wc = df_date_filtered['wc'].mean()
        st.metric("Average Water Cut", f"{avg_wc:.1f}%")
    
    with col4:
        num_unique_ids = df_date_filtered['unique_id'].nunique()
        st.metric("Active Well Zones", f"{num_unique_ids}")
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Create and display the chart
    st.markdown("<div class='chart-container'>", unsafe_allow_html=True)
    
    fig = create_hierarchical_chart(
        df_filtered,
        metric,
        hierarchy_level,
        level_name,
        breakdown_by,
        date_range
    )
    
    if fig:
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Data table
    with st.expander("📋 View Raw Data"):
        display_cols = ['date', 'field', 'zone', 'unique_id', metric]
        display_cols = [col for col in display_cols if col in df_date_filtered.columns]
        st.dataframe(
            df_date_filtered[display_cols].sort_values('date', ascending=False),
            use_container_width=True,
            height=400
        )


main()