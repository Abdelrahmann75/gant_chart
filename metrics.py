import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from pathlib import Path
# Custom CSS for styling
st.markdown(
    """
    <style>
    .main {
        background-color: #f5f5f5;
        padding: 20px;
        border-radius: 10px;
    }
    h1 {
        color: #2c3e50;
        text-align: center;
    }
    h2 {
        color: #34495e;
    }
    .stButton button {
        background-color: #3498db;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .metric-box {
        background-color: white;
        border-radius: 10px;
        padding: 20px;
        margin: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Function to load data from SQLite database using a provided query
@st.cache_resource
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
@st.cache_resource
def get_data_alam_single():
    db_path = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    # Query specific to Alamein production data table
    query_alam = "SELECT * FROM st_data"
    return load_data(db_path, query_alam)

# Load Petrosilah data (using its own query)
@st.cache_resource
def get_data_silah_single():
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    # Query specific to Petrosilah production data table (adjust as needed)
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
    
    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            options = ["Petrosilah", "Alamein"]
            default_index = options.index("Alamein")
            company_selection = st.selectbox("**Select Company:**", options, index=default_index)
            prod_df = df_alam_prod if company_selection == "Alamein" else df_sila_prod
        with col2:
            min_date = prod_df['date'].min()
            max_date = prod_df['date'].max()
            selected_date_range = st.slider("**Select Date Range**", 
                                            min_value=min_date, 
                                            max_value=max_date, 
                                            value=(min_date, max_date))
        with col3:
            type_options = sorted(prod_df['type'].dropna().unique()) if 'type' in prod_df.columns else []
            selected_types = st.multiselect("**Select Type:**", type_options)
        col4, col5, col6 = st.columns([1, 1, 1])
        with col4:
            fields = prod_df['field'].unique()
            selected_fields = st.multiselect("**Select Fields**", fields)
        with col5:
            well_filter = prod_df.copy()
            if selected_fields:
                well_filter = well_filter[well_filter['field'].isin(selected_fields)]
            if selected_types:
                well_filter = well_filter[well_filter['type'].isin(selected_types)]
            selected_well_bores = st.multiselect("**Select Well Bores**", well_filter['well_bore'].unique())
        with col6:
            zone_filter = prod_df.copy()
            if selected_fields:
                zone_filter = zone_filter[zone_filter['field'].isin(selected_fields)]
            if selected_types:
                zone_filter = zone_filter[zone_filter['type'].isin(selected_types)]
            if selected_well_bores:
                zone_filter = zone_filter[zone_filter['well_bore'].isin(selected_well_bores)]
            selected_zones = st.multiselect("**Select Zones**", zone_filter['zone'].unique())
            
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

# ------------------ Output Code: Metrics and Charts ------------------

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

    # --- Bar Chart 1: Production Analysis by Well Bore ---
    prod_choice = st.radio("Select Production Type for Bar Chart", options=["Net Oil", "Gross Oil"], index=0)
    if prod_choice == "Net Oil":
        production_col = "net"
        unit_base = "BOPD"
    else:
        production_col = "gross"
        unit_base = "BF"

    # Group by well bore and zone
    df_zone = filtered_prod.groupby(["well_bore", "zone"], as_index=False)[production_col].sum()
    scale_bar = 1000000 if df_zone[production_col].max() >= 1000000 else 1
    df_zone["production_display"] = df_zone[production_col] / scale_bar

    # Remove rows with zero production
    df_zone = df_zone[df_zone["production_display"] > 0]

    # Order wells by total production
    df_total = df_zone.groupby("well_bore", as_index=False)["production_display"].sum()
    df_total = df_total.sort_values("production_display", ascending=False)
    well_order = df_total["well_bore"].tolist()
    prod_label_bar = f"{prod_choice} ({'MM ' if scale_bar==1000000 else ''}{unit_base})"

    # Format display text based on scaling
    if scale_bar == 1:
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
            family="Arial Black",  # Bold font family for labels
            size=16,
            color="black"
        )
    )

    fig_prod.update_layout(
        title=f"Total Production by Well Bore (Values in {prod_label_bar})",
        xaxis_title="Well Bore",
        yaxis_title=prod_label_bar,
        hovermode="closest",
        legend_title="Zone",
        barmode="stack",
        xaxis=dict(
            tickfont=dict(
                family="Arial Black",  # Bold tick labels
                size=16,
                color="black"
            ),
            title_font=dict(
                family="Arial Black",  # Bold x-axis title
                size=16,
                color="black"
            ),
            tickangle=90
        ),
        yaxis=dict(
            tickfont=dict(
                family="Arial Black",  # Bold tick labels for y-axis
                size=16,
                color="black"
            ),
            title_font=dict(
                family="Arial Black",  # Bold y-axis title
                size=16,
                color="black"
            )
        )
    )

    st.plotly_chart(fig_prod, use_container_width=True)

    
    # --- Bar Chart 2: Injection Rate Analysis by Well Bore ---
    df_inj = filtered_prod.groupby(["well_bore", "zone"], as_index=False)[["inj_rate"]].sum()
    scale_inj_bar = 1000000 if df_inj["inj_rate"].max() >= 1000000 else 1
    df_inj["inj_display"] = df_inj["inj_rate"] / scale_inj_bar
    inj_label_bar = f"Injection Rate ({'MM ' if scale_inj_bar==1000000 else ''}BW)"
    df_inj = df_inj[df_inj["inj_display"] > 0]
    df_inj_total = df_inj.groupby("well_bore", as_index=False)["inj_display"].sum()
    df_inj_total = df_inj_total.sort_values("inj_display", ascending=False)
    well_order_inj = df_inj_total["well_bore"].tolist()
    
    if scale_inj_bar == 1:
        df_inj["display_text"] = df_inj["inj_display"].apply(lambda x: f'<b>{int(x)}</b>' if x != 0 else "")
    else:
        df_inj["display_text"] = df_inj["inj_display"].apply(lambda x: f'<b>{x:.2f}</b>' if x != 0 else "")
    
    fig_inj = px.bar(df_inj, 
                     x="well_bore", 
                     y="inj_display", 
                     color="zone",
                     text="display_text", 
                     category_orders={"well_bore": well_order_inj},
                     labels={"inj_display": inj_label_bar, "well_bore": "Well Bore", "zone": "Zone"})
    fig_inj.update_traces(textposition='outside')
    fig_inj.update_layout(
        title=f"Total Injection by Well Bore (Values in {inj_label_bar})",
        xaxis_title="Well Bore",
        yaxis_title=inj_label_bar,
        hovermode="closest",
        legend_title="Zone",
        barmode="stack",
        xaxis=dict(tickfont=dict(family="Arial Black", size=12), tickangle=90)
    )
    st.plotly_chart(fig_inj, use_container_width=True)
    
else:
    st.info("No production data available for the selected filters.")
