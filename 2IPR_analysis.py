import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from dateutil.relativedelta import relativedelta
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
    .stSelectbox, .stSlider, .stMultiselect {
        background-color: white;
        border-radius: 5px;
        padding: 10px;
    }
    .stDataFrame {
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Function to load data from SQLite database with custom queries
@st.cache_resource
def load_data(db_path, prod_query, dfl_query):
    try:
        conn = sqlite3.connect(db_path)
        prod_df = pd.read_sql_query(prod_query, conn)
        dfl_df = pd.read_sql_query(dfl_query, conn)
        conn.close()
        
        # Convert 'date' column to datetime.date and sort for both dataframes
        for d in [prod_df, dfl_df]:
            if 'date' in d.columns:
                d['date'] = pd.to_datetime(d['date']).dt.date
                d.dropna(subset=['date'], inplace=True)
                d.sort_values('date', inplace=True)
        return prod_df, dfl_df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Load Alamein data with its specific queries
@st.cache_resource
def get_data_alam():
    
    db_path = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    # For Alamein, use these queries
    prod_query = "SELECT * FROM st_data_plot"
    dfl_query = "SELECT * FROM view_dfl"
    return load_data(db_path, prod_query, dfl_query)

# Load Petrosila data with its specific queries
@st.cache_resource
def get_data_silah():
    
    db_path = Path(__file__).parent.parent / "data" / "petrosila.db"
    # For Petrosila, you can specify different queries if needed
    prod_query = "SELECT * FROM st_data"     # Example: different production table/query
    dfl_query = "SELECT * FROM view_dfl"       # Example: same DFL query as before (adjust if needed)
    return load_data(db_path, prod_query, dfl_query)

# Updated common filter function to include filtering on the new 'type' column
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

def group_data(filtered_df, group_cols):
    available_cols = [col for col in group_cols if col in filtered_df.columns]
    if available_cols:
        # Use sum(min_count=1) to avoid NaN being converted to 0; for wc, take the average.
        agg_dict = {col: lambda x: x.sum(min_count=1) for col in available_cols}
        if 'wc' in available_cols:
            agg_dict['wc'] = lambda x: x.mean(skipna=True)
        return filtered_df.groupby('date').agg(agg_dict).reset_index()
    else:
        return filtered_df.copy()

def display_filters():
    df_alam_prod, df_alam_dfl = get_data_alam()
    df_sila_prod, df_sila_dfl = get_data_silah()

    with st.container():
        st.markdown("<div class='filter-frame'>", unsafe_allow_html=True)
        # Three columns for Company, Date Range, and Type filters
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            options = ["Petrosilah", "Alamein"]
            default_index = options.index("Alamein")
            company_selection = st.selectbox("**Select Company:**", options=options, index=default_index)
            if company_selection == "Alamein":
                prod_df = df_alam_prod.copy()
                dfl_df = df_alam_dfl.copy()
            else:
                prod_df = df_sila_prod.copy()
                dfl_df = df_sila_dfl.copy()
        with col2:
            min_date = prod_df['date'].min()
            max_date = prod_df['date'].max()
            choose_range = max_date - relativedelta(months=5)
            selected_date_range = st.slider("**Select Date Range**", min_value=min_date, max_value=max_date, value=(choose_range, max_date))
        with col3:
            # Create a multiselect filter for the 'type' column if it exists
            if 'type' in prod_df.columns:
                type_options = sorted(prod_df['type'].dropna().unique())
                selected_types = st.multiselect("**Select Type:**", type_options)
            else:
                selected_types = []
        st.markdown("</div>", unsafe_allow_html=True)

        # Additional filters (Field, Well Bore, Zone) in a separate row with three columns.
        col4, col5, col6 = st.columns([1, 1, 1])
        with col4:
            fields = prod_df['field'].unique()
            selected_fields = st.multiselect("**Select Fields**", list(fields))
        with col5:
            # Filter the well bores based on the selected Fields and Types (if any)
            well_filter = prod_df.copy()
            if selected_fields:
                well_filter = well_filter[well_filter['field'].isin(selected_fields)]
            if selected_types:
                well_filter = well_filter[well_filter['type'].isin(selected_types)]
            filtered_wells = well_filter['well_bore'].unique()
            selected_well_bores = st.multiselect("**Select Well Bores**", list(filtered_wells))
        with col6:
            # Filter zones using the selected fields, types, and well bores (if any)
            zone_filter = prod_df.copy()
            if selected_fields:
                zone_filter = zone_filter[zone_filter['field'].isin(selected_fields)]
            if selected_types:
                zone_filter = zone_filter[zone_filter['type'].isin(selected_types)]
            if selected_well_bores:
                zone_filter = zone_filter[zone_filter['well_bore'].isin(selected_well_bores)]
            filtered_zones = zone_filter['zone'].unique()
            selected_zones = st.multiselect("**Select Zones**", list(filtered_zones))
        st.markdown("---", unsafe_allow_html=True)

    # Apply common filters including the new type filter
    filtered_prod_common = apply_common_filters(prod_df, selected_date_range, selected_fields, selected_well_bores, selected_zones, selected_types)
    filtered_dfl_common = apply_common_filters(dfl_df, selected_date_range, selected_fields, selected_well_bores, selected_zones, selected_types)
    
    filtered_prod = group_data(filtered_prod_common, ['net', 'inj_rate', 'wc', 'gross'])
    if company_selection == "Alamein":
        filtered_dfl = group_data(filtered_dfl_common, ['dfl', 'pi'])
    else:
        filtered_dfl = group_data(filtered_dfl_common, ['nlap', 'pi'])
    
    return filtered_prod, filtered_dfl, company_selection, selected_well_bores, selected_zones

filtered_prod, filtered_dfl, company_selection, selected_well_bores, selected_zones = display_filters()

# Build a title string from the selected Well Bore and Zone filters
selected_well_zone = ""
if selected_well_bores or selected_zones:
    parts = []
    if selected_well_bores:
        parts.append(", ".join(selected_well_bores))
    if selected_zones:
        parts.append(", ".join(selected_zones))
    selected_well_zone = " | ".join(parts)

production_title = selected_well_zone
dfl_title = selected_well_zone

##########################################
# Production Plot (filtered_prod)
##########################################
if not filtered_prod.empty:
    prod_df = filtered_prod.copy()
    prod_df['date'] = pd.to_datetime(prod_df['date'])
    
    # Compute common x-axis settings from production data
    min_date = prod_df['date'].min()
    max_date = prod_df['date'].max()
    common_x_range = [min_date, max_date]
    
    # Compute total days and then calculate dtick (in milliseconds)
    total_days = (max_date - min_date).days
    desired_ticks = 15  # adjust the number of ticks as desired
    ticks = pd.date_range(start=min_date, end=max_date, periods=desired_ticks)
    tickvals = ticks.tolist()
    ticktext = [d.strftime('%d-%b-%Y') for d in ticks]
    
    fig_prod = go.Figure()
    fig_prod.add_trace(go.Scatter(
        x=prod_df['date'],
        y=prod_df['net'],
        mode='lines',
        name='Net',
        line=dict(color='green', width=1.5)
    ))
    fig_prod.add_trace(go.Scatter(
        x=prod_df['date'],
        y=prod_df['gross'],
        mode='lines',
        name='Gross',
        line=dict(color='black', width=1.5)
    ))
    fig_prod.add_trace(go.Scatter(
        x=prod_df['date'],
        y=prod_df['inj_rate'],
        mode='lines',
        name='Inj Rate',
        line=dict(color='orange', width=1.5),
        yaxis='y1'
    ))
    fig_prod.add_trace(go.Scatter(
        x=prod_df['date'],
        y=prod_df['wc'],
        mode='lines',
        name='WC',
        line=dict(color='blue', width=1.5),
        yaxis='y2'
    ))
    
    fig_prod.update_layout(
        title={
            'text': f"<b>{production_title}</b>",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=21)
        },
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgrey',
            linecolor='black',
            tickfont=dict(family='Arial', size=19, color='black'),
            titlefont=dict(family='Arial', size=19, color='black'),
            ticks='outside',
            tickangle=90,
            tickformat='%d-%b-%Y',
            tickmode='array',
            tickvals=tickvals,
            range=common_x_range,
            ticktext=ticktext,
            autorange=False
        ),
        yaxis=dict(
            title="Net Oil & Gross Fluid (BBLS/day) & INJ BWPD",
            showgrid=True,
            gridcolor='lightgrey',
            linecolor='black',
            ticks='outside',
            titlefont=dict(family='Arial', size=19, color='black'),
            tickfont=dict(family='Arial', size=19, color='black'),
            rangemode='tozero'  # Force y-axis to start at zero
        ),
        yaxis2=dict(
            title="WC (%)",
            overlaying='y',
            side='right',
            showgrid=False,
            ticks='outside',
            tickmode='array',
            tickvals=[i * 10 for i in range(11)],
            range=[0, 100],
            tickfont=dict(color='blue', size=21),
            titlefont=dict(color='blue',size=21),
            rangemode='tozero'  # Force secondary y-axis to start at zero
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=21)
        ),
        plot_bgcolor='white',
        margin=dict(l=50, r=50, t=120, b=80),
        height=600,
        uirevision='static'
             # Maintains the default zoom on updates
    )
    
    # Calculate cumulative values
    net_sum = int(prod_df['net'].sum())
    inj_sum = int(prod_df['inj_rate'].sum())
    
    
    # fig_prod.add_annotation(
    #     x=0.01, y=1.15,
    #     xref="paper", yref="paper",
    #     text=f"<b>CUM Oil: {net_sum:,} BBLS</b>",
    #     showarrow=False,
    #     font=dict(size=14, color="green", family="Arial"),
    #     align="left",
    #     bgcolor="white",
    #     bordercolor="green",
    #     borderwidth=2,
    #     borderpad=10
    # ) 
  
    # fig_prod.add_annotation(
    #     x=0.35, y=1.15,
    #     xref="paper", yref="paper",
    #     text=f"<b>CUM Injected: {inj_sum:,} BBLS</b>",
    #     showarrow=False,
    #     font=dict(size=14, color="orange", family="Arial"),
    #     align="left",
    #     bgcolor="white",
    #     bordercolor="orange",
    #     borderwidth=2,
    #     borderpad=10
    # ) 
    
    st.plotly_chart(fig_prod, use_container_width=True)
    
else:
    st.info("No production data available for the selected filters.")

st.markdown("---")

##########################################
# DFL Plot (filtered_dfl) with markers and common x-axis
##########################################
if not filtered_dfl.empty:
    dfl_df = filtered_dfl.copy()
    dfl_df['date'] = pd.to_datetime(dfl_df['date'])
    
    fig_dfl = go.Figure()
    if company_selection == "Alamein":
        # For Alamein, DFL on primary axis and PI on secondary axis
        if 'dfl' in dfl_df.columns:
            fig_dfl.add_trace(go.Scatter(
                x=dfl_df['date'],
                y=dfl_df['dfl'],
                mode='lines+markers',
                name='DFL',
                line=dict(color='purple', width=1.5)
            ))
        if 'pi' in dfl_df.columns:
            fig_dfl.add_trace(go.Scatter(
                x=dfl_df['date'],
                y=dfl_df['pi'],
                mode='lines+markers',
                name='PI',
                line=dict(color='red', width=1.5),
                yaxis='y2'  # Secondary y-axis
            ))
        layout_yaxis = dict(
            title="DFL",
            titlefont=dict(family='Arial', size=16, color='black', weight='bold'),
            tickfont=dict(family='Arial', size=16, color='black'),
            color='black',
            rangemode='tozero'  # Force axis to start at zero
        )
        layout_yaxis2 = dict(
            title="PI",
            titlefont=dict(family='Arial', size=19, color='red', weight='bold'),
            tickfont=dict(family='Arial', size=19, color='red'),
            color='red',
            overlaying='y',
            side='right',
            rangemode='tozero'  # Force axis to start at zero
        )
    else:
        # For Petrosilah, plot NLAP on primary y-axis and PI on secondary y-axis
        if 'nlap' in dfl_df.columns:
            fig_dfl.add_trace(go.Scatter(
                x=dfl_df['date'],
                y=dfl_df['nlap'],
                mode='lines+markers',
                name='NLAP',
                line=dict(color='purple', width=1.5)
            ))
        if 'pi' in dfl_df.columns:
            fig_dfl.add_trace(go.Scatter(
                x=dfl_df['date'],
                y=dfl_df['pi'],
                mode='lines+markers',
                name='PI',
                line=dict(color='red', width=1.5),
                yaxis='y2'
            ))
        layout_yaxis = dict(
            title="NLAP",
            titlefont=dict(family='Arial', size=16, color='black', weight='bold'),
            tickfont=dict(family='Arial', size=16, color='black'),
            color='black',
            rangemode='tozero'
        )
        layout_yaxis2 = dict(
            title="PI",
            titlefont=dict(family='Arial', size=19, color='red', weight='bold'),
            tickfont=dict(family='Arial', size=19, color='red'),
            color='red',
            overlaying='y',
            side='right',
            rangemode='tozero'
        )
    
    fig_dfl.update_layout(
        title={
            'text': f"<b>{dfl_title}</b>",
            'y': 0.9,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(size=19)
        },
        xaxis=dict(
            showgrid=True,
            gridcolor='lightgrey',
            linecolor='black',
            tickfont=dict(family='Arial', size=19, color='black'),
            titlefont=dict(family='Arial', size=19, color='black'),
            ticks='outside',
            tickangle=90,
            tickformat='%d-%b-%Y',
            range=common_x_range,
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
            autorange=False
        ),
        yaxis=layout_yaxis,
        yaxis2=layout_yaxis2,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=21)
        ),
        plot_bgcolor='white',
        margin=dict(l=50, r=50, t=120, b=80),
        height=600,
        uirevision='static'
    )
    
    st.plotly_chart(fig_dfl, use_container_width=True)
    
else:
    st.info("No DFL data available for the selected filters.")
