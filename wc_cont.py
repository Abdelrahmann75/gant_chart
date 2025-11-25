import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from scipy.interpolate import griddata
import numpy as np
import os
from datetime import datetime, timedelta
from pathlib import Path


# Custom CSS
st.markdown("""
    <style>
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 20px;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        padding: 20px;
        background: white;
        border-radius: 15px;
        margin-bottom: 30px;
    }
    h2 {
        color: #34495e;
        border-left: 5px solid #3498db;
        padding-left: 15px;
        margin-top: 20px;
    }
    h3 {
        color: #2c3e50;
        font-weight: 600;
    }
    
    /* Custom Tab Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 10px;
        border-radius: 15px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        white-space: pre-wrap;
        background-color: rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        color: white;
        font-size: 18px;
        font-weight: 600;
        border: 2px solid transparent;
        padding: 10px 30px;
        transition: all 0.3s ease;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.3);
        transform: translateY(-2px);
    }
    
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #667eea !important;
        border: 2px solid white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 30px;
    }
    
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 12px 30px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.3);
    }
    .metric-box {
        background: white;
        border-radius: 15px;
        padding: 25px;
        margin: 10px;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        border-left: 5px solid #3498db;
        transition: transform 0.3s ease;
    }
    .metric-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 35px rgba(0,0,0,0.15);
    }
    .date-selector {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .filter-box {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border: 2px solid #667eea30;
    }
    .company-selector {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
    }
    .stSelectbox label, .stMultiSelect label {
        color: #2c3e50;
        font-weight: 600;
        font-size: 14px;
    }
    div[data-testid="stMetricValue"] {
        font-size: 28px;
        color: #3498db;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        color: #2c3e50;
        font-weight: 600;
    }
    .slider-container {
        background: white;
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    }
    .date-display {
        background: linear-gradient(135deg, #667eea15 0%, #764ba215 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-size: 18px;
        font-weight: 700;
        color: #2c3e50;
        margin: 15px 0;
        border: 2px solid #667eea;
    }
    </style>
    """, unsafe_allow_html=True)

# Function to load data from SQLite database
@st.cache_data
def load_data(db_path, query):
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
        st.error(f"❌ Error loading data: {e}")
        return pd.DataFrame()

# Function to convert coordinates to numeric
def convert_coordinates_to_numeric(df):
    """Convert xcord and ycord to numeric, handling any string values"""
    numeric_cols = ['xcord', 'ycord', 'wc', 'wc_last', 'net', 'gross', 'oil', 'pressure']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# Load Alamein production data
@st.cache_data
def get_data_alam_single():
    db_path = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    
    query_alam = "SELECT * FROM st_data"
    df = load_data(db_path, query_alam)
    return convert_coordinates_to_numeric(df)

# Load Alamein header data
@st.cache_data
def get_header_alam():
    db_path = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    query = """SELECT unique_id, well_bore, zone, alias, field, 
                      xcord, ycord, type FROM header_id"""
    df = load_data(db_path, query)
    return convert_coordinates_to_numeric(df)

# Load Petrosilah production data
@st.cache_data
def get_data_silah_single():
    
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    query_silah = "SELECT * FROM st_data"
    df = load_data(db_path, query_silah)
    return convert_coordinates_to_numeric(df)

# Load Petrosilah header data
@st.cache_data
def get_header_silah():
    
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    query = """SELECT well_zone as unique_id, well_bore, zone, alias, 
                      field, xcord, ycord, type FROM header_id"""
    df = load_data(db_path, query)
    return convert_coordinates_to_numeric(df)

# Load Petrosilah reservoir pressure data
@st.cache_data
def get_pressure_data_silah():
    
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    query = """SELECT 
        rd.well_zone,
        rd.date,
        rd.pressure,
        h.well_bore,
        h.zone,
        h.field
    FROM 
        reservoir_data as rd
    LEFT JOIN header_id as h
    ON rd.well_zone = h.well_zone"""
    df = load_data(db_path, query)
    return convert_coordinates_to_numeric(df)

# Load Alamein reservoir pressure data (when available)
@st.cache_data
def get_pressure_data_alam():
    # For now, return empty dataframe - will be implemented when data is available
    return pd.DataFrame()

# Function to get last WC value for each well in date range
def get_last_wc_per_well(filtered_data):
    """Get the LAST (most recent) water cut value for each well within the filtered period."""
    if 'wc' not in filtered_data.columns:
        return pd.DataFrame()
    
    filtered_data_sorted = filtered_data.sort_values('date')
    last_wc = filtered_data_sorted.groupby('unique_id').agg({
        'wc': 'last',
        'date': 'last'
    }).reset_index()
    last_wc.columns = ['unique_id', 'wc_last', 'last_date']
    return last_wc

# Function to create contour map with FIXED colors and extended grid
def create_contour_map(data, title="Water Cut Contour Map"):
    data = convert_coordinates_to_numeric(data.copy())
    data = data.dropna(subset=['xcord', 'ycord', 'wc_last'])
    data['wc_last'] = data['wc_last'].clip(0, 100)
    
    if data.empty or len(data) < 3:
        st.warning("⚠️ Not enough data points to create contour map (minimum 3 required)")
        return None
    
    try:
        # EXTENDED GRID with 20% padding on each side
        x_range = data['xcord'].max() - data['xcord'].min()
        y_range = data['ycord'].max() - data['ycord'].min()
        x_padding = x_range * 0.2
        y_padding = y_range * 0.2
        
        xi = np.linspace(data['xcord'].min() - x_padding, data['xcord'].max() + x_padding, 120)
        yi = np.linspace(data['ycord'].min() - y_padding, data['ycord'].max() + y_padding, 120)
        xi_grid, yi_grid = np.meshgrid(xi, yi)
        
        # Interpolate data
        zi = griddata(
            (data['xcord'].values, data['ycord'].values), 
            data['wc_last'].values,
            (xi_grid, yi_grid),
            method='cubic',
            fill_value=data['wc_last'].mean()
        )
        
        zi = np.clip(zi, 0, 100)
        
        fig = go.Figure()
        
        # REVERSED COLOR SCALE: High WC = Blue, Low WC = Green/Yellow
        fig.add_trace(go.Contour(
            x=xi,
            y=yi,
            z=zi,
           # Reversed: Red=low, Yellow=mid, Green=high but we reverse it
            # Custom colorscale: Low WC = Green/Yellow, High WC = Blue
            colorscale=[
                [0.0, '#00ff00'],   # 0% = Bright Green (low WC - good!)
                [0.3, '#ffff00'],   # 30% = Yellow
                [0.5, '#ff9900'],   # 50% = Orange
                [0.7, '#ff0000'],   # 70% = Red
                [1.0, '#0000ff']    # 100% = Blue (high WC - bad!)
            ],
            contours=dict(
                coloring='heatmap',
                showlabels=True,
                labelfont=dict(size=10, color='white'),
                start=0,
                end=100,
                size=10
            ),
            colorbar=dict(
                title="Water Cut (%)<br>Last Value",
                titleside="right",
                tickmode="linear",
                tick0=0,
                dtick=10,
                len=0.75
            ),
            zmin=0,
            zmax=100,
            hovertemplate='X: %{x:.2f}<br>Y: %{y:.2f}<br>WC: %{z:.2f}%<extra></extra>'
        ))
        
        # Add scatter points for actual wells
        fig.add_trace(go.Scatter(
            x=data['xcord'],
            y=data['ycord'],
            mode='markers+text',
            marker=dict(
                size=12,
                color='black',
                symbol='circle',
                line=dict(color='white', width=2)
            ),
            text=data['unique_id'],
            textposition='top center',
            textfont=dict(size=9, color='black', family='Arial Black'),
            hovertemplate='<b>%{text}</b><br>' +
                          'X: %{x:.2f}<br>' +
                          'Y: %{y:.2f}<br>' +
                          'Last WC: %{customdata[0]:.2f}%<br>' +
                          'Date: %{customdata[1]}<extra></extra>',
            customdata=np.column_stack((data['wc_last'], data['last_date'].dt.strftime('%Y-%m-%d'))),
            name='Wells'
        ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50', 'family': 'Arial Black'}
            },
            xaxis_title="X Coordinate",
            yaxis_title="Y Coordinate",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=700,
            hovermode='closest',
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray', scaleanchor="x", scaleratio=1)
        )
        
        return fig
    
    except Exception as e:
        st.error(f"❌ Error creating contour map: {e}")
        return None

# Function to create bubble map
def create_bubble_map(data, size_by, color_by, title="Bubble Map"):
    data = convert_coordinates_to_numeric(data.copy())
    data = data.dropna(subset=['xcord', 'ycord', size_by, color_by])
    
    if data.empty:
        st.warning("⚠️ Not enough data points to create bubble map")
        return None
    
    data[size_by] = data[size_by].abs()
    
    if color_by == 'wc_last':
        data[color_by] = data[color_by].clip(0, 100)
        color_range = [0, 100]
        # Same color scheme as contour map
        color_scale = [
            [0.0, '#00ff00'],
            [0.3, '#ffff00'],
            [0.5, '#ff9900'],
            [0.7, '#ff0000'],
            [1.0, '#0000ff']
        ]
        colorbar_title = "Water Cut (%)<br>Last Value"
    else:
        color_range = [0, data[color_by].max()]
        color_scale = 'Viridis'
        colorbar_title = color_by.replace('_', ' ').title()
    
    try:
        size_normalized = 10 + (data[size_by] - data[size_by].min()) / (data[size_by].max() - data[size_by].min() + 1e-10) * 50
        
        fig = go.Figure()
        
        if color_by == 'wc_last':
            hover_template = ('<b>%{text}</b><br>' +
                            'X: %{x:.2f}<br>' +
                            'Y: %{y:.2f}<br>' +
                            f'{size_by.upper()}: ' + '%{customdata[0]:,.0f}<br>' +
                            'Last WC: %{customdata[1]:.2f}%<br>' +
                            'Date: %{customdata[2]}<extra></extra>')
            customdata_array = np.column_stack((data[size_by], data[color_by], data['last_date'].dt.strftime('%Y-%m-%d')))
        else:
            hover_template = ('<b>%{text}</b><br>' +
                            'X: %{x:.2f}<br>' +
                            'Y: %{y:.2f}<br>' +
                            f'{size_by.upper()}: ' + '%{customdata[0]:,.0f}<br>' +
                            f'{color_by.upper()}: ' + '%{customdata[1]:,.2f}<extra></extra>')
            customdata_array = np.column_stack((data[size_by], data[color_by]))
        
        fig.add_trace(go.Scatter(
            x=data['xcord'],
            y=data['ycord'],
            mode='markers+text',
            marker=dict(
                size=size_normalized,
                color=data[color_by],
                colorscale=color_scale,
                showscale=True,
                line=dict(color='white', width=2),
                colorbar=dict(
                    title=colorbar_title,
                    titleside="right",
                    tickmode="auto",
                    nticks=6,
                    len=0.75,
                    thickness=20,
                    tickformat=".0f" if color_by != 'wc_last' else ".1f"
                ),
                cmin=color_range[0],
                cmax=color_range[1]
            ),
            text=data['unique_id'],
            textposition='top center',
            textfont=dict(size=9, color='black', family='Arial Black'),
            hovertemplate=hover_template,
            customdata=customdata_array,
            name='Wells'
        ))
        
        fig.update_layout(
            title={
                'text': title,
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 20, 'color': '#2c3e50', 'family': 'Arial Black'}
            },
            xaxis_title="X Coordinate",
            yaxis_title="Y Coordinate",
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=700,
            hovermode='closest',
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray', scaleanchor="x", scaleratio=1)
        )
        
        return fig
    
    except Exception as e:
        st.error(f"❌ Error creating bubble map: {e}")
        return None

# Function to create pressure plot
def create_pressure_plot(data, plot_type, title="Static Pressure Over Time"):
    data = convert_coordinates_to_numeric(data.copy())
    data = data.dropna(subset=['date', 'pressure', 'well_zone'])
    
    if data.empty:
        st.warning("⚠️ No pressure data available")
        return None
    
    # Sort by date
    data = data.sort_values('date')
    
    # Get unique well zones and assign colors
    unique_wells = data['well_zone'].unique()
    colors = px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    color_map = {well: colors[i % len(colors)] for i, well in enumerate(unique_wells)}
    
    fig = go.Figure()
    
    for well in unique_wells:
        well_data = data[data['well_zone'] == well]
        
        if plot_type == "Lines + Markers":
            fig.add_trace(go.Scatter(
                x=well_data['date'],
                y=well_data['pressure'],
                mode='lines+markers',
                name=well,
                line=dict(color=color_map[well], width=2),
                marker=dict(size=8, color=color_map[well], line=dict(color='white', width=1)),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Date: %{x|%Y-%m-%d}<br>' +
                              'Pressure: %{y:.2f}<extra></extra>'
            ))
        else:  # Dots Only
            fig.add_trace(go.Scatter(
                x=well_data['date'],
                y=well_data['pressure'],
                mode='markers',
                name=well,
                marker=dict(size=10, color=color_map[well], line=dict(color='white', width=1)),
                hovertemplate='<b>%{fullData.name}</b><br>' +
                              'Date: %{x|%Y-%m-%d}<br>' +
                              'Pressure: %{y:.2f}<extra></extra>'
            ))
    
    fig.update_layout(
        title={
            'text': title,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 20, 'color': '#2c3e50', 'family': 'Arial Black'}
        },
        xaxis_title="Date",
        yaxis_title="Pressure (psi)",
        plot_bgcolor='white',
        paper_bgcolor='white',
        height=700,
        hovermode='closest',
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='lightgray'),
        legend=dict(
            title="Well Zone",
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    )
    
    return fig

# Function to format date for display
def format_date_range(start_date, end_date):
    return f"{start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')}"

# Main app
def main():
    st.markdown("<h1>🛢️ Well Production Analysis Dashboard</h1>", unsafe_allow_html=True)
    
    # Company Selection at the top
    st.markdown("<div class='company-selector'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        company = st.selectbox(
            "🏢 Select Company:",
            ["Alamein", "Petrosilah"],
            index=0,
            key="company_selector"
        )
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Load appropriate data based on company
    if company == "Alamein":
        production_data = get_data_alam_single()
        header_data = get_header_alam()
        pressure_data = get_pressure_data_alam()
    else:
        production_data = get_data_silah_single()
        header_data = get_header_silah()
        pressure_data = get_pressure_data_silah()
    
    if production_data.empty or header_data.empty:
        st.error("❌ Unable to load data. Please check database connections.")
        return
    
    available_columns = production_data.columns.tolist()
    
    # Display data info metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        st.metric("📊 Total Records", f"{len(production_data):,}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        st.metric("🎯 Total Wells", f"{header_data['unique_id'].nunique():,}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
        date_range = (production_data['date'].max() - production_data['date'].min()).days
        st.metric("📅 Data Range (days)", f"{date_range:,}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Create main tabs
    st.markdown("---")
    tab1, tab2 = st.tabs(["🗺️ Maps Analysis", "📊 Static Pressure"])
    
    # TAB 1: Maps Analysis (contains Contour and Bubble as sub-tabs)
    with tab1:
        # Date range selection
        st.markdown("<div class='slider-container'>", unsafe_allow_html=True)
        st.markdown("### 📅 Date Range Selection")
        
        min_date = production_data['date'].min()
        max_date = production_data['date'].max()
        
        date_method = st.radio(
            "Selection Method:",
            ["📊 Date Slider", "✏️ Manual Input"],
            horizontal=True,
            key="maps_date_method"
        )
        
        if date_method == "📊 Date Slider":
            selected_range = st.slider(
                "Select Date Range:",
                min_value=min_date.to_pydatetime(),
                max_value=max_date.to_pydatetime(),
                value=(min_date.to_pydatetime(), max_date.to_pydatetime()),
                format="YYYY-MM-DD",
                key="maps_date_slider"
            )
            start_date = selected_range[0].date()
            end_date = selected_range[1].date()
            st.markdown(
                f"<div class='date-display'>📅 Selected Range: {format_date_range(start_date, end_date)} ({(end_date - start_date).days} days)</div>",
                unsafe_allow_html=True
            )
        else:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=min_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                    key="maps_start_manual"
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=max_date.date(),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                    key="maps_end_manual"
                )
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Filter data by date range
        filtered_data = production_data[
            (production_data['date'] >= pd.Timestamp(start_date)) & 
            (production_data['date'] <= pd.Timestamp(end_date))
        ].copy()
        
        if filtered_data.empty:
            st.warning("⚠️ No data available for the selected date range.")
            return
        
        # Filters section
        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### 🔍 Filter Options")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            fields = ['All'] + sorted(header_data['field'].dropna().unique().tolist())
            selected_field = st.selectbox("Field", fields, key="maps_field")
        
        with col2:
            zones = ['All'] + sorted(header_data['zone'].dropna().unique().tolist())
            selected_zone = st.selectbox("Zone", zones, key="maps_zone")
        
        with col3:
            well_types = ['All'] + sorted(header_data['type'].dropna().unique().tolist())
            selected_type = st.selectbox("Well Type", well_types, key="maps_type")
        
        with col4:
            unique_ids = ['All'] + sorted(header_data['unique_id'].dropna().unique().tolist())
            selected_well = st.selectbox("Well ID", unique_ids, key="maps_well")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Apply filters
        filtered_header = header_data.copy()
        if selected_field != 'All':
            filtered_header = filtered_header[filtered_header['field'] == selected_field]
        if selected_zone != 'All':
            filtered_header = filtered_header[filtered_header['zone'] == selected_zone]
        if selected_type != 'All':
            filtered_header = filtered_header[filtered_header['type'] == selected_type]
        if selected_well != 'All':
            filtered_header = filtered_header[filtered_header['unique_id'] == selected_well]
        
        # Build aggregation
        agg_dict = {}
        if 'net' in available_columns:
            agg_dict['net'] = 'sum'
        if 'gross' in available_columns:
            agg_dict['gross'] = 'sum'
        
        last_wc_data = get_last_wc_per_well(filtered_data)
        
        if agg_dict:
            agg_data = filtered_data.groupby('unique_id').agg(agg_dict).reset_index()
            new_cols = {'unique_id': 'unique_id'}
            if 'net' in agg_dict:
                new_cols['net'] = 'net_total'
            if 'gross' in agg_dict:
                new_cols['gross'] = 'gross_total'
            agg_data.columns = [new_cols.get(col, col) for col in agg_data.columns]
            agg_data = convert_coordinates_to_numeric(agg_data)
        else:
            agg_data = pd.DataFrame({'unique_id': last_wc_data['unique_id']})
        
        if not last_wc_data.empty:
            agg_data = agg_data.merge(last_wc_data, on='unique_id', how='outer')
        
        if 'wc_last' in agg_data.columns:
            agg_data['wc_last'] = agg_data['wc_last'].clip(0, 100)
        
        final_data = filtered_header.merge(agg_data, on='unique_id', how='inner')
        final_data = convert_coordinates_to_numeric(final_data)
        final_data = final_data.dropna(subset=['xcord', 'ycord'])
        
        if final_data.empty:
            st.warning("⚠️ No wells match the selected filters with valid data.")
            return
        
        # Display metrics
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
            st.metric("🎯 Filtered Wells", f"{len(final_data):,}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
            if 'wc_last' in final_data.columns:
                avg_wc = final_data['wc_last'].mean()
                st.metric("💧 Avg Last WC", f"{avg_wc:.2f}%")
            else:
                st.metric("💧 Water Cut", "N/A")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
            if 'net_total' in final_data.columns:
                total_net = final_data['net_total'].sum()
                st.metric("📊 Total Net", f"{total_net:,.0f}")
            elif 'gross_total' in final_data.columns:
                total_gross = final_data['gross_total'].sum()
                st.metric("📊 Total Gross", f"{total_gross:,.0f}")
            else:
                st.metric("📊 Production", "N/A")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
            if 'gross_total' in final_data.columns and 'net_total' in final_data.columns:
                total_gross = final_data['gross_total'].sum()
                st.metric("🛢️ Total Gross", f"{total_gross:,.0f}")
            else:
                date_days = (end_date - start_date).days
                st.metric("📅 Period (days)", f"{date_days}")
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Sub-tabs for Contour and Bubble maps
        st.markdown("---")
        subtab1, subtab2 = st.tabs(["🗺️ Water Cut Contour Map", "🫧 Production Bubble Map"])
        
        # Contour Map Sub-tab
        with subtab1:
            st.markdown("## 🗺️ Interactive Contour Map")
            st.markdown("*Visualize **last water cut value** across well locations (Green=Low WC, Blue=High WC)*")
            
            if 'wc_last' in final_data.columns:
                title = f"{company} - Water Cut Distribution - Last Values ({start_date} to {end_date})"
                fig = create_contour_map(final_data, title)
                
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                    st.info("ℹ️ **Color Guide:** 🟢 Green = Low WC (Good) → 🟡 Yellow → 🟠 Orange → 🔴 Red → 🔵 Blue = High WC (Bad)")
                
                with st.expander("📋 View Detailed Well Data"):
                    display_cols = ['unique_id', 'well_bore', 'zone', 'field', 'type', 'xcord', 'ycord', 'wc_last', 'last_date']
                    available_display_cols = [col for col in display_cols if col in final_data.columns]
                    display_data = final_data[available_display_cols].copy()
                    if 'wc_last' in display_data.columns:
                        display_data['wc_last'] = display_data['wc_last'].round(2)
                    if 'last_date' in display_data.columns:
                        display_data['last_date'] = display_data['last_date'].dt.strftime('%Y-%m-%d')
                        display_data = display_data.sort_values('wc_last', ascending=False)
                    
                    st.dataframe(display_data, use_container_width=True, height=400)
                    csv = display_data.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Data as CSV",
                        data=csv,
                        file_name=f"{company}_wc_contour_{start_date}_{end_date}.csv",
                        mime="text/csv"
                    )
            else:
                st.warning("⚠️ Water cut data not available")
        
        # Bubble Map Sub-tab
        with subtab2:
            st.markdown("## 🫧 Interactive Bubble Map")
            st.markdown("*Explore production metrics with customizable bubble sizes and colors*")
            
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                size_options = []
                if 'net_total' in final_data.columns:
                    size_options.append('net_total')
                if 'gross_total' in final_data.columns:
                    size_options.append('gross_total')
                if 'wc_last' in final_data.columns:
                    size_options.append('wc_last')
                
                if not size_options:
                    st.error("No data available for bubble size")
                    return
                
                size_by = st.selectbox(
                    "🔘 Bubble Size:",
                    size_options,
                    format_func=lambda x: {
                        'net_total': '📊 Net Production',
                        'gross_total': '🛢️ Gross Production',
                        'wc_last': '💧 Last Water Cut'
                    }.get(x, x),
                    key="bubble_size"
                )
            
            with col2:
                color_options = []
                if 'wc_last' in final_data.columns:
                    color_options.append('wc_last')
                if 'net_total' in final_data.columns:
                    color_options.append('net_total')
                if 'gross_total' in final_data.columns:
                    color_options.append('gross_total')
                
                if not color_options:
                    st.error("No data available for bubble color")
                    return
                
                color_by = st.selectbox(
                    "🎨 Bubble Color:",
                    color_options,
                    format_func=lambda x: {
                        'wc_last': '💧 Last Water Cut (0-100%)',
                        'net_total': '📊 Net Production',
                        'gross_total': '🛢️ Gross Production'
                    }.get(x, x),
                    key="bubble_color"
                )
            
            title = f"{company} - Production Bubble Map ({start_date} to {end_date})"
            fig = create_bubble_map(final_data, size_by, color_by, title)
            
            if fig:
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    size_label = size_by.replace('_', ' ').title()
                    if size_by == 'wc_last':
                        size_label = "Last Water Cut"
                    st.info(f"**🔘 Bubble Size:** {size_label}")
                with col2:
                    color_label = color_by.replace('_', ' ').title()
                    if color_by == 'wc_last':
                        color_label = "Last Water Cut"
                    st.info(f"**🎨 Bubble Color:** {color_label}")
            
            with st.expander("📋 View Detailed Well Data"):
                display_cols = ['unique_id', 'well_bore', 'zone', 'field', 'type', 'xcord', 'ycord']
                if 'wc_last' in final_data.columns:
                    display_cols.extend(['wc_last', 'last_date'])
                if 'net_total' in final_data.columns:
                    display_cols.append('net_total')
                if 'gross_total' in final_data.columns:
                    display_cols.append('gross_total')
                
                available_display_cols = [col for col in display_cols if col in final_data.columns]
                display_data = final_data[available_display_cols].copy()
                
                for col in ['wc_last', 'net_total', 'gross_total']:
                    if col in display_data.columns:
                        display_data[col] = display_data[col].round(2)
                
                if 'last_date' in display_data.columns:
                    display_data['last_date'] = display_data['last_date'].dt.strftime('%Y-%m-%d')
                
                display_data = display_data.sort_values(size_by, ascending=False)
                st.dataframe(display_data, use_container_width=True, height=400)
                
                csv = display_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download Data as CSV",
                    data=csv,
                    file_name=f"{company}_bubble_map_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
    
    # TAB 2: Static Pressure
    with tab2:
        st.markdown("## 📊 Static Pressure Analysis")
        
        if pressure_data.empty:
            st.warning(f"⚠️ No pressure data available for {company} yet. Coming soon!")
            return
        
        # Filters for pressure tab
        st.markdown("<div class='filter-box'>", unsafe_allow_html=True)
        st.markdown("### 🔍 Filter Options")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            p_fields = ['All'] + sorted(pressure_data['field'].dropna().unique().tolist())
            p_selected_field = st.selectbox("Field", p_fields, key="pressure_field")
        
        with col2:
            p_zones = ['All'] + sorted(pressure_data['zone'].dropna().unique().tolist())
            p_selected_zone = st.selectbox("Zone", p_zones, key="pressure_zone")
        
        with col3:
            p_wells = ['All'] + sorted(pressure_data['well_zone'].dropna().unique().tolist())
            p_selected_well = st.selectbox("Well Zone", p_wells, key="pressure_well")
        
        with col4:
            p_wellbores = ['All'] + sorted(pressure_data['well_bore'].dropna().unique().tolist())
            p_selected_wellbore = st.selectbox("Well Bore", p_wellbores, key="pressure_wellbore")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Apply pressure filters
        filtered_pressure = pressure_data.copy()
        if p_selected_field != 'All':
            filtered_pressure = filtered_pressure[filtered_pressure['field'] == p_selected_field]
        if p_selected_zone != 'All':
            filtered_pressure = filtered_pressure[filtered_pressure['zone'] == p_selected_zone]
        if p_selected_well != 'All':
            filtered_pressure = filtered_pressure[filtered_pressure['well_zone'] == p_selected_well]
        if p_selected_wellbore != 'All':
            filtered_pressure = filtered_pressure[filtered_pressure['well_bore'] == p_selected_wellbore]
        
        if filtered_pressure.empty:
            st.warning("⚠️ No data matches the selected filters")
            return
        
        # Plot type selector
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            plot_type = st.radio(
                "📈 Plot Style:",
                ["Dots Only", "Lines + Markers"],
                horizontal=True,
                key="pressure_plot_type"
            )
        
        with col2:
            st.metric("🎯 Wells in Plot", f"{filtered_pressure['well_zone'].nunique()}")
        
        with col3:
            st.metric("📊 Data Points", f"{len(filtered_pressure):,}")
        
        # Create and display pressure plot
        title = f"{company} - Static Pressure Over Time"
        fig = create_pressure_plot(filtered_pressure, plot_type, title)
        
        if fig:
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("ℹ️ **Note:** Each well zone is colored uniquely. Use the legend to show/hide specific wells.")
        
        # Data table
        with st.expander("📋 View Pressure Data"):
            display_data = filtered_pressure[['well_zone', 'well_bore', 'zone', 'field', 'date', 'pressure']].copy()
            display_data['date'] = display_data['date'].dt.strftime('%Y-%m-%d')
            display_data['pressure'] = display_data['pressure'].round(2)
            display_data = display_data.sort_values(['well_zone', 'date'])
            
            st.dataframe(display_data, use_container_width=True, height=400)
            
            csv = display_data.to_csv(index=False)
            st.download_button(
                label="📥 Download Pressure Data as CSV",
                data=csv,
                file_name=f"{company}_pressure_data.csv",
                mime="text/csv"
            )


main()