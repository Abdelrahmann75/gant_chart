import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
import os
import base64
import fitz  # PyMuPDF
from streamlit.components.v1 import html
from datetime import timedelta, datetime
from pathlib import Path

# Enhanced Custom CSS for Modern Styling
st.markdown(
    """
    <style>
    /* Main Container Styling */
    .main {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 2rem;
    }
    
    /* Header Styling */
    h1 {
        color: #1a365d;
        text-align: center;
        font-weight: 800;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    
    h2 {
        color: #2d3748;
        font-weight: 700;
    }
    
    h3 {
        color: #2c5282;
        font-weight: 600;
    }
    
    /* Card/Container Styling */
    .filter-container {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
        border: 1px solid #e2e8f0;
    }
    
    .company-selector {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
        margin-bottom: 1.5rem;
    }
    
    .company-selector label {
        color: white !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
    }
    
    /* Date Selection Section */
    .date-selector {
        background: white;
        border-radius: 15px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 4px 10px rgba(0,0,0,0.08);
        border: 1px solid #e2e8f0;
    }
    
    .date-selector h3 {
        color: #2c5282 !important;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .date-selector label {
        color: #2d3748 !important;
        font-weight: 600 !important;
    }
    
    /* Filter Section Styling */
    .filter-section {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        border-radius: 15px;
        padding: 2rem;
        margin-top: 1.5rem;
        box-shadow: 0 10px 25px rgba(168, 237, 234, 0.3);
    }
    
    .filter-section h3 {
        color: #2c5282 !important;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .filter-section label {
        color: #2d3748 !important;
        font-weight: 600 !important;
    }
    
    /* Metric Box Styling */
    .metric-box {
        background: linear-gradient(135deg, #ffffff 0%, #f7fafc 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin: 0.5rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        border-left: 5px solid #3182ce;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    .metric-box:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(0,0,0,0.15);
    }
    
    .metric-box h3 {
        color: #2d3748;
        font-size: 1rem;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    
    .metric-box h2 {
        color: #1a365d;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    
    /* Button Styling */
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        border: none;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
    }
    
    /* Radio Button Styling */
    .stRadio > label {
        font-weight: 600 !important;
        color: #2d3748 !important;
    }
    
    /* Selectbox Styling */
    .stSelectbox > label {
        font-weight: 600 !important;
        color: #2d3748 !important;
    }
    
    /* Multiselect Styling */
    .stMultiSelect > label {
        font-weight: 600 !important;
        color: #2d3748 !important;
    }
    
    /* Info/Success/Warning Boxes */
    .stAlert {
        border-radius: 10px;
        border-left-width: 5px;
    }
    
    /* Divider Styling */
    hr {
        margin: 2rem 0;
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #cbd5e0, transparent);
    }
    
    /* Column Spacing */
    [data-testid="column"] {
        padding: 0.5rem;
    }
    
    /* Chart Container */
    .chart-container {
        background: white;
        border-radius: 15px;
        padding: 1.5rem;
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        margin: 1rem 0;
    }
    
    /* Section Headers */
    .section-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 10px;
        margin: 1.5rem 0 1rem 0;
        font-weight: 700;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Function to load data from SQLite database using a provided query
@st.cache_data
def load_data(db_path, query):
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(query, conn)
        conn.close()
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df.dropna(subset=['date'], inplace=True)
            df.sort_values('date', inplace=True)
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

# Load Alamein data (using its own query)
@st.cache_data
def get_data_alam_single():
    
    db_path = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    query_alam = "SELECT * FROM st_data"
    return load_data(db_path, query_alam)

# Load Petrosilah data (using its own query)
@st.cache_data
def get_data_silah_single():
    
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    query_silah = "SELECT * FROM st_data"  
    return load_data(db_path, query_silah)

# Apply common filters to a dataframe
def apply_common_filters(df, selected_date_range, selected_fields, selected_well_bores, selected_zones, selected_types):
    filtered_df = df[(df['date'] >= selected_date_range[0]) & (df['date'] <= selected_date_range[1])]
    if selected_fields:
        filtered_df = filtered_df[filtered_df['field'].isin(selected_fields)]
    if selected_well_bores:
        filtered_df = filtered_df[filtered_df['well_bore'].isin(selected_well_bores)]
    if selected_zones:
        filtered_df = filtered_df[filtered_df['zone'].isin(selected_zones)]
    if selected_types and 'type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['type'].isin(selected_types)]
    return filtered_df

# Display filter widgets and return the filtered production data and some selections
def display_filters():
    # Load both datasets
    df_alam_prod = get_data_alam_single()
    df_sila_prod = get_data_silah_single()
    
    st.markdown('<div class="filter-container">', unsafe_allow_html=True)
    
    # Company and Type Selection Row
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        st.markdown('<div class="company-selector">', unsafe_allow_html=True)
        options = ["Petrosilah", "Alamein"]
        default_index = options.index("Alamein")
        company_selection = st.selectbox("🏢 Select Company", options, index=default_index)
        prod_df = df_alam_prod if company_selection == "Alamein" else df_sila_prod
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("")  # Spacer
        
    with col3:
        type_options = sorted(prod_df['type'].dropna().unique()) if 'type' in prod_df.columns else []
        selected_types = st.multiselect("⚙️ **Select Type**", type_options)

    
    st.markdown("### 📅 Date Range Selection")
    
    min_date = prod_df['date'].min()
    max_date = prod_df['date'].max()
    
    date_col1, date_col2 = st.columns([1, 2])
    
    with date_col1:
        date_input_method = st.radio(
            "**Choose Method:**",
            options=["📊 Date Range Slider", "📝 Manual Date Input"],
            help="Select how you want to choose your date range"
        )
    
    with date_col2:
        if date_input_method == "📊 Date Range Slider":
            st.info("🎯 Use the slider below to select your date range")
            selected_date_range = st.slider(
                "**Select Date Range:**", 
                min_value=min_date, 
                max_value=max_date, 
                value=(min_date, max_date),
                format="YYYY-MM-DD",
                help="Drag the handles to select start and end dates"
            )
            
            # Display selected dates
            days_selected = (selected_date_range[1] - selected_date_range[0]).days + 1
            st.success(f"✅ **Selected Period:** {selected_date_range[0]} to {selected_date_range[1]} ({days_selected} days)")
            
        else:  # Manual Date Input
            st.info("✏️ Select start and end dates manually")
            
            manual_col1, manual_col2 = st.columns(2)
            
            with manual_col1:
                start_date = st.date_input(
                    '📆 **Start Date:**',
                    min_value=min_date,
                    max_value=max_date,
                    value=min_date,
                    help="Select the start date for analysis"
                )
                
            with manual_col2:
                end_date = st.date_input(
                    '📆 **End Date:**',
                    min_value=min_date,
                    max_value=max_date,
                    value=max_date,
                    help="Select the end date for analysis"
                )
            
            # Validate date range
            if start_date > end_date:
                st.error("❌ Start date must be before or equal to end date!")
                st.stop()
            else:
                selected_date_range = (start_date, end_date)
                days_selected = (end_date - start_date).days + 1
                st.success(f"✅ **Selected Period:** {selected_date_range[0]} to {selected_date_range[1]} ({days_selected} days)")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Additional Filters Section
    st.markdown('<div class="filter-section">', unsafe_allow_html=True)
    st.markdown("### 🔍 Additional Filters")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        fields = prod_df['field'].unique()
        selected_fields = st.multiselect("🗺️ **Select Fields**", fields)
        
    with col5:
        well_filter = prod_df.copy()
        if selected_fields:
            well_filter = well_filter[well_filter['field'].isin(selected_fields)]
        if selected_types:
            well_filter = well_filter[well_filter['type'].isin(selected_types)]
        selected_well_bores = st.multiselect("🔧 **Select Well Bores**", well_filter['well_bore'].unique())
        
    with col6:
        zone_filter = prod_df.copy()
        if selected_fields:
            zone_filter = zone_filter[zone_filter['field'].isin(selected_fields)]
        if selected_types:
            zone_filter = zone_filter[zone_filter['type'].isin(selected_types)]
        if selected_well_bores:
            zone_filter = zone_filter[zone_filter['well_bore'].isin(selected_well_bores)]
        selected_zones = st.multiselect("🎯 **Select Zones**", zone_filter['zone'].unique())
    
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
        
    filtered_prod = apply_common_filters(prod_df, selected_date_range, selected_fields, selected_well_bores, selected_zones, selected_types)
    return filtered_prod, company_selection, selected_well_bores, selected_zones

# Get filtered production data and some selections
filtered_prod, company_selection, selected_well_bores, selected_zones = display_filters()

# Build a title string from selected well bores and zones
selected_well_zone = ""
if selected_well_bores or selected_zones:
    parts = []
    if selected_well_bores:
        parts.append(", ".join(selected_well_bores))
    if selected_zones:
        parts.append(", ".join(selected_zones))
    selected_well_zone = " | ".join(parts)

# Add separator
st.divider()

# ------------------ Output Code: Metrics and Charts ------------------
st.markdown('<div class="section-header">📊 Production Metrics & Analysis</div>', unsafe_allow_html=True)

if not filtered_prod.empty:
    # Fill missing production values with 0
    filtered_prod = filtered_prod.fillna({'net': 0, 'gross': 0, 'wc': 0, 'inj_rate': 0})
    
    # Calculate total metrics
    total_net_raw = filtered_prod['net'].sum()
    total_gross_raw = filtered_prod['gross'].sum()
    total_water_raw = (filtered_prod['gross'] - filtered_prod['net']).sum()
    total_injection_raw = filtered_prod['inj_rate'].sum()

    # Determine unit scaling for net production
    if total_net_raw >= 1000000:
        display_total_net = total_net_raw / 1000000.0
        net_unit = "MM BO"
    else:
        display_total_net = total_net_raw
        net_unit = "BO"

    # Determine unit scaling for gross production
    if total_gross_raw >= 100000:
        display_total_gross = total_gross_raw / 1000000.0
        gross_unit = "MM BF"
    else:
        display_total_gross = total_gross_raw
        gross_unit = "BF"

    # Determine unit scaling for water produced
    if total_water_raw >= 1000000:
        display_total_water = total_water_raw / 1000000.0
        water_unit = "MM BW"
    else:
        display_total_water = total_water_raw
        water_unit = "BW"

    # Determine unit scaling for injection volume
    if total_injection_raw >= 1000000:
        display_total_injection = total_injection_raw / 1000000.0
        inj_unit = "MM BW"
    else:
        display_total_injection = total_injection_raw
        inj_unit = "BW"

    # Display metrics in four columns
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-box"><h3>💹 Total Net Oil</h3><h2>{display_total_net:,.2f} {net_unit}</h2></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-box"><h3>💹 Total Gross</h3><h2>{display_total_gross:,.2f} {gross_unit}</h2></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-box"><h3>💧 Water Produced</h3><h2>{display_total_water:,.2f} {water_unit}</h2></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-box"><h3>💧 Injection Volume</h3><h2>{display_total_injection:,.2f} {inj_unit}</h2></div>', unsafe_allow_html=True)

    st.divider()

    # --- Bar Chart 1: Production Analysis by Well Bore ---
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">🛢️ Production Analysis</div>', unsafe_allow_html=True)
    
    prod_choice = st.radio("**Select Production Type:**", options=["Net Oil", "Gross Oil", "Water Cut"], index=0, horizontal=True)
    
    if prod_choice == "Net Oil":
        production_col = "net"
        unit_base = "BOPD"
        agg_function = "sum"
    elif prod_choice == "Gross Oil":
        production_col = "gross"
        unit_base = "BF"
        agg_function = "sum"
    else:  # Water Cut
        production_col = "wc"
        unit_base = "%"
        agg_function = "mean"

    # Group by well bore and zone
    if agg_function == "sum":
        df_zone = filtered_prod.groupby(["well_bore", "zone"], as_index=False)[production_col].sum()
        scale_bar = 1000000 if df_zone[production_col].max() >= 1000000 else 1
        df_zone["production_display"] = df_zone[production_col] / scale_bar
    else:  # mean for water cut
        df_zone = filtered_prod.groupby(["well_bore", "zone"], as_index=False)[production_col].mean()
        scale_bar = 1
        df_zone["production_display"] = df_zone[production_col]

    # Remove rows with zero production
    df_zone = df_zone[df_zone["production_display"] > 0]

    # Order wells by total production/average
    if agg_function == "sum":
        df_total = df_zone.groupby("well_bore", as_index=False)["production_display"].sum()
    else:
        df_total = df_zone.groupby("well_bore", as_index=False)["production_display"].mean()
    
    df_total = df_total.sort_values("production_display", ascending=False)
    well_order = df_total["well_bore"].tolist()
    
    if prod_choice == "Water Cut":
        prod_label_bar = f"Average {prod_choice} ({unit_base})"
    else:
        prod_label_bar = f"{prod_choice} ({'MM ' if scale_bar==1000000 else ''}{unit_base})"

    # Format display text based on scaling
    if prod_choice == "Water Cut":
        df_zone["display_text"] = df_zone["production_display"].apply(lambda x: f'<b>{x:.1f}%</b>' if x != 0 else "")
    elif scale_bar == 1:
        df_zone["display_text"] = df_zone["production_display"].apply(lambda x: f'<b>{int(x)}</b>' if x != 0 else "")
    else:
        df_zone["display_text"] = df_zone["production_display"].apply(lambda x: f'<b>{x:.2f}</b>' if x != 0 else "")

    fig_prod = px.bar(
        df_zone, 
        x="well_bore", 
        y="production_display", 
        color="zone",
        text="display_text",
        category_orders={"well_bore": well_order},
        labels={"production_display": prod_label_bar, "well_bore": "Well Bore", "zone": "Zone"}
    )

    fig_prod.update_traces(
        textposition='outside',
        textfont=dict(
            family="Arial Black",
            size=16,
            color="black"
        )
    )
    
    chart_title = f"Total {prod_choice} by Well Bore (Values in {prod_label_bar})" if prod_choice != "Water Cut" else f"Average {prod_choice} by Well Bore"

    fig_prod.update_layout(
        title=chart_title,
        xaxis_title="Well Bore",
        yaxis_title=prod_label_bar,
        hovermode="closest",
        legend_title="Zone",
        barmode="stack",
        xaxis=dict(
            tickfont=dict(family="Arial Black", size=16, color="black"),
            title_font=dict(family="Arial Black", size=16, color="black"),
            tickangle=90
        ),
        yaxis=dict(
            tickfont=dict(family="Arial Black", size=16, color="black"),
            title_font=dict(family="Arial Black", size=16, color="black")
        ),
        height=600,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    st.plotly_chart(fig_prod, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # --- Bar Chart 2: Injection Rate Analysis by Well Bore ---
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    st.markdown('<div class="section-header">💉 Injection Analysis</div>', unsafe_allow_html=True)
    
    df_inj = filtered_prod.groupby(["well_bore", "zone"], as_index=False)[["inj_rate"]].sum()
    scale_inj_bar = 1000000 if df_inj["inj_rate"].max() >= 1000000 else 1
    df_inj["inj_display"] = df_inj["inj_rate"] / scale_inj_bar
    inj_label_bar = f"Injection Rate ({'MM ' if scale_inj_bar==1000000 else ''}BW)"
    df_inj = df_inj[df_inj["inj_display"] > 0]
    
    if not df_inj.empty:
        df_inj_total = df_inj.groupby("well_bore", as_index=False)["inj_display"].sum()
        df_inj_total = df_inj_total.sort_values("inj_display", ascending=False)
        well_order_inj = df_inj_total["well_bore"].tolist()
        
        if scale_inj_bar == 1:
            df_inj["display_text"] = df_inj["inj_display"].apply(lambda x: f'<b>{int(x)}</b>' if x != 0 else "")
        else:
            df_inj["display_text"] = df_inj["inj_display"].apply(lambda x: f'<b>{x:.2f}</b>' if x != 0 else "")
        
        fig_inj = px.bar(
            df_inj, 
            x="well_bore", 
            y="inj_display", 
            color="zone",
            text="display_text", 
            category_orders={"well_bore": well_order_inj},
            labels={"inj_display": inj_label_bar, "well_bore": "Well Bore", "zone": "Zone"}
        )
        
        fig_inj.update_traces(
            textposition='outside',
            textfont=dict(family="Arial Black", size=14, color="black")
        )
        
        fig_inj.update_layout(
            title=f"Total Injection by Well Bore (Values in {inj_label_bar})",
            xaxis_title="Well Bore",
            yaxis_title=inj_label_bar,
            hovermode="closest",
            legend_title="Zone",
            barmode="stack",
            xaxis=dict(
                tickfont=dict(family="Arial Black", size=12),
                title_font=dict(family="Arial Black", size=14),
                tickangle=90
            ),
            yaxis=dict(
                tickfont=dict(family="Arial Black", size=12),
                title_font=dict(family="Arial Black", size=14)
            ),
            height=600,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_inj, use_container_width=True)
    else:
        st.info("💡 No injection data available for the selected filters.")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
else:
    st.warning("⚠️ No production data available for the selected filters.")
    st.info("💡 Try adjusting your filter selections to see data.")