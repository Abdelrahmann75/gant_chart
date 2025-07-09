import base64
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
from streamlit_plotly_events import plotly_events
from streamlit.components.v1 import html
import plotly.graph_objects as go

# --- Set page layout and title ---
st.set_page_config(layout="wide", page_title="Well File PDF Viewer & Bubble Map")

# --- Custom CSS styling ---
st.markdown("""
    <style>
    .main { background-color: #f5f5f5; padding: 20px; border-radius: 10px; }
    h1 { color: #2c3e50; text-align: center; }
    h2 { color: #34495e; }
    .stButton button {
        background-color: #3498db; color: white;
        border-radius: 5px; padding: 10px 20px; font-size: 16px;
    }
    .metric-box {
        background-color: white; border-radius: 10px;
        padding: 20px; margin: 10px;
        box-shadow: 0 0 10px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- Helper function to get PDF base URL ---
def get_pdf_base_path():
    """
    Get the base URL for PDF files in Azure Blob Storage.
    """
    return "https://iprdashboard.blob.core.windows.net/pdf-excel/"

# --- Data Loaders ---
@st.cache_data
def load_vi_map(db_path):
    """
    Load the vi_map table: date, well_bore, oil, wc, field
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT date, well_bore, oil, wc, field FROM vi_map", conn)
        conn.close()
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    except Exception as e:
        st.warning(f"Could not load vi_map from {db_path}: {e}")
        return pd.DataFrame(columns=["date", "well_bore", "oil", "wc", "field"])

@st.cache_data
def load_header_data(db_path):
    """
    Load header_id table: well_bore, zone, xcord, ycord, type
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT well_bore, zone, xcord, ycord, type FROM header_id", conn)
        conn.close()
        return df.drop_duplicates("well_bore")
    except Exception as e:
        st.warning(f"Could not load header_id from {db_path}: {e}")
        return pd.DataFrame(columns=["well_bore", "zone", "xcord", "ycord", "type"])

@st.cache_data
def load_well_files(db_path):
    """
    Load well_files_vis table: well_bore, file_path, file_type
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT well_bore, file_path, file_type FROM well_files_vis", conn)
        conn.close()
        return df.dropna(subset=["file_path", "file_type"])
    except Exception as e:
        st.warning(f"Could not load well_files_vis from {db_path}: {e}")
        return pd.DataFrame(columns=["well_bore", "file_path", "file_type"])

# --- Helper to display PDF inline in Streamlit using iframe ---
def display_pdf(well_list: list[str], files_df: pd.DataFrame):
    """
    For each well in well_list, look up its PDF path in files_df and show it in an iframe.
    """
    pdf_base_url = get_pdf_base_path()
    
    for well in well_list:
        pdf_row = files_df[
            (files_df['well_bore'] == well) &
            (files_df['file_type'].str.lower() == 'pdf')
        ]
        if not pdf_row.empty:
            # Get the filename from database
            filename = pdf_row.iloc[0]['file_path']
            
            # Construct the full URL
            full_url = f"{pdf_base_url}{filename}"
            
            st.write(f"**{well}** ‣ {filename}")
            st.write(f"Loading PDF from: {full_url}")
            
            # Embed PDF using iframe
            try:
                html(
                    f'<iframe src="{full_url}" width="100%" height="1000px" '
                    f'style="border:1px solid #ddd; background:white;"></iframe>',
                    height=1000
                )
            except Exception as e:
                st.error(f"Error embedding PDF {filename}: {e}")
        else:
            st.write(f"No PDF found for well **{well}**.")

# --- Filtering Logic ---
def apply_common_filters(df, selected_date_range, selected_fields, selected_zones, selected_types):
    """
    Apply date / field / zone / type filters to the base dataframe.
    """
    if selected_fields is None or len(selected_fields) == 0:
        selected_fields = df['field'].dropna().unique()

    if selected_zones is None or len(selected_zones) == 0:
        selected_zones = df['zone'].dropna().unique()

    if selected_types is None or len(selected_types) == 0:
        if 'type' in df.columns:
            selected_types = df['type'].dropna().unique()

    # Filter by date range
    filtered_df = df[
        (df['date'] >= selected_date_range[0]) &
        (df['date'] <= selected_date_range[1])
    ]
    # Filter by field
    filtered_df = filtered_df[filtered_df['field'].isin(selected_fields)]

    # Filter by zone if available
    if 'zone' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['zone'].isin(selected_zones)]
    # Filter by type if available
    if 'type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['type'].isin(selected_types)]

    return filtered_df

# --- UI Filters (returns both all_files_df and filtered_files_df) ---
def display_filters():
    """
    1) Let user pick company
    2) Load production + header + well_files tables
    3) Show date / type / field / well_bore filters
    4) Return:
       - filtered_prod : filtered production DataFrame
       - all_files_df   : well_files_vis (unfiltered)
       - filtered_files : only those files whose well_bore is in selected multiselect
       - header_df      : header (coordinates + type)
       - company_sel    : which DB was chosen
       - selected_wells : wells chosen in the multiselect
    """
    db2 = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    db1 = Path(__file__).parent.parent / "data" / "petrosila.db"
    company_options = {"Petrosilah": db1, "Alamein": db2}
    h1,h2,h3 = st.columns([1, 1, 1])
    with h1:
        company_selection = st.selectbox("**Select Company:**", list(company_options.keys()))
    db_path = company_options[company_selection]

    # Load production and header
    prod_df = load_vi_map(db_path)
    header_df = load_header_data(db_path)

    if prod_df.empty or header_df.empty:
        st.warning("No data available for this company.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), company_selection, []

    # Merge in zone/type to production df (for filtering)
    prod_df = prod_df.merge(header_df[['well_bore', 'zone', 'type']], on='well_bore', how='left')

    with st.container():
        col1, col2, col3 = st.columns([1, 1, 1])
        with col1:
            min_date = prod_df['date'].min()
            max_date = prod_df['date'].max()
            selected_date_range = st.slider(
                "**Select Date Range**",
                min_date, max_date,
                (min_date, max_date)
            )
        with col2:
            type_options = sorted(prod_df['type'].dropna().unique()) if 'type' in prod_df else []
            selected_types = st.multiselect("**Select Type:**", type_options)
        with col3:
            field_options = sorted(prod_df['field'].dropna().unique())
            selected_fields = st.multiselect("**Select Fields:**", field_options,
                                             default=field_options[:1] if field_options else [])

        col4, col5, col6 = st.columns([1, 1, 1])
        with col4:
            # Show only wells in the chosen fields
            filtered_for_wells = prod_df[prod_df['field'].isin(selected_fields)]
            selected_well_bores = st.multiselect(
                "**Select Well Bores:**",
                filtered_for_wells['well_bore'].dropna().unique()
            )
        with col5:
            # Zone dropdown depends on either all header_df or selected wells
            filtered_for_zones = header_df.copy()
            if selected_well_bores:
                filtered_for_zones = filtered_for_zones[
                    filtered_for_zones['well_bore'].isin(selected_well_bores)
                ]
            zone_options = sorted(filtered_for_zones['zone'].dropna().unique())
            selected_zones = st.multiselect("**Select Zones:**", zone_options)
        # col6 is empty for now

    # Now apply filters to production
    filtered_prod = apply_common_filters(
        prod_df,
        selected_date_range,
        selected_fields,
        selected_zones,
        selected_types
    )

    # Load *all* well files (unfiltered)
    all_files_df = load_well_files(db_path)

    # Among those files, keep only rows whose well_bore is in the multiselect
    if selected_well_bores:
        filtered_files = all_files_df[
            all_files_df['well_bore'].isin(selected_well_bores)
        ]
    else:
        filtered_files = pd.DataFrame()  # none selected

    return filtered_prod, all_files_df, filtered_files, header_df, company_selection, selected_well_bores

def display_bubble_map(header_df, vi_df, fields, date_range, all_files_df):
    """
    1) Build a single Plotly figure containing producers + WIs with a visible WC colorbar.
    2) On click, grab well_bore from customdata or fallback to matching (x, y).
    3) Show that well's PDF.
    """
    # 1) Apply common filters to vi_df (date_range, fields, etc.)
    df = apply_common_filters(vi_df, date_range, fields, [], [])

    # 2) Compute cumulative oil + average WC per well
    oilw = df.groupby("well_bore").agg({"oil": "sum", "wc": "mean"}).reset_index()
    oilw.columns = ["well_bore", "cumm", "avg_wc"]
    oilw["avg_wc"] = oilw["avg_wc"].round(2)

    # 3) Format the cumulative oil as Mbbl or bbl depending on date span
    date_diff = (date_range[1] - date_range[0]).days
    if date_diff > 30:
        oilw["cumm"] = oilw["cumm"] / 1000
        oilw["cumm_fmt"] = oilw["cumm"].apply(lambda x: f"{int(x):,} Mbbl")
    else:
        oilw["cumm_fmt"] = oilw["cumm"].apply(lambda x: f"{int(x):,} bbl")

    # 4) Merge coordinates + type from header_df into oilw
    merged = header_df.merge(oilw, on="well_bore", how="inner")
    merged["xcord"] = pd.to_numeric(merged["xcord"], errors="coerce")
    merged ["ycord"] = pd.to_numeric(merged["ycord"], errors="coerce")
    merged.dropna(subset=["xcord", "ycord"], inplace=True)

    # 5) Build custom hover‐text, showing only "WC" (no literal "Water Cut")
    merged["custom_text"] = merged.apply(
        lambda row: (
            # If it's a WI, just show the well_bore in large font
            f"<span style='font-size:18px;'><b>{row['well_bore']}</b></span>"
            if row["type"] == "WI"
            else
            # Otherwise show well_bore + Oil + WC
            f"<span style='font-size:18px;'>"
            f"<b>{row['well_bore']}</b><br>"
            f"<b>Oil:</b> {row['cumm_fmt']}<br>"
            f"<b>WC:</b> {row['avg_wc']}%"
            f"</span>"
        ),
        axis=1,
    )

    # 6) Separate "producer" vs "WI" and remove any coordinate overlaps
    producers = merged[merged["type"] == "producer"].copy()
    wis = merged[merged["type"] == "WI"].copy()

    # If a WI and a producer share exact (x,y), remove the producer so only WI shows
    overlap_coords = set(zip(wis["xcord"], wis["ycord"]))
    producers = producers[
        ~producers[["xcord", "ycord"]].apply(tuple, axis=1).isin(overlap_coords)
    ]

    # 7) Mark which producers actually have oil vs shut-in (NaN cumm)
    producers["has_oil"] = producers["cumm"].notna() & (producers["cumm"] > 0)

    producers_colored = producers[producers["has_oil"]].copy()  # will map color by avg_wc
    producers_na = producers[~producers["has_oil"]].copy()      # black for shut-in

    # 8) Build one Plotly Figure, starting with the producers_with_oil trace:
    fig = go.Figure()

    # 8a) Producers WITH oil → colored by avg_wc, using shared coloraxis
    fig.add_trace(
        go.Scatter(
            x=producers_colored["xcord"],
            y=producers_colored["ycord"],
            mode="markers+text",
            marker=dict(
                size=40,
                color=producers_colored["avg_wc"],      # map color to WC
                colorscale=[[0.0, "green"], [0.5, "white"], [1.0, "lightblue"]],
                cmin=0,
                cmax=100,
                colorbar=dict(
                    title="WC (%)",
                    titlefont=dict(size=16),
                    tickfont=dict(size=14),
                    thickness=25,
                    len=0.6,
                    x=1.02,          # push colorbar slightly to the right
                    xanchor="left",
                ),
                coloraxis="coloraxis"  # reference the shared coloraxis
            ),
            text=producers_colored["custom_text"],
            textposition="top center",
            name="Producers",
            customdata=producers_colored[["well_bore"]].values,
            hoverinfo="text"
        )
    )

    # 8b) Producers WITHOUT oil (shut-in) → black markers
    fig.add_trace(
        go.Scatter(
            x=producers_na["xcord"],
            y=producers_na["ycord"],
            mode="markers+text",
            marker=dict(size=40, color="black"),
            text=producers_na["custom_text"],
            textposition="top center",
            name="Shut-in",
            customdata=producers_na[["well_bore"]].values,
            hoverinfo="text"
        )
    )

    # 8c) WIs → orange markers
    fig.add_trace(
        go.Scatter(
            x=wis["xcord"],
            y=wis["ycord"],
            mode="markers+text",
            marker=dict(size=40, color="orange"),
            text=wis["custom_text"],
            textposition="top center",
            name="WI",
            customdata=wis[["well_bore"]].values,
            hoverinfo="text"
        )
    )

    # 9) Compute dynamic padding for the axis ranges
    x_min, x_max = merged["xcord"].min(), merged["xcord"].max()
    y_min, y_max = merged["ycord"].min(), merged["ycord"].max()
    x_range = x_max - x_min if (x_max - x_min) != 0 else 1
    y_range = y_max - y_min if (y_max - y_min) != 0 else 1
    x_pad = x_range * 0.1
    y_pad = y_range * 0.1

    # 10) Set up the overall layout, including the shared coloraxis:
    fig.update_layout(
        title=dict(
            text="Bubble Map – WC Gradient | Black = Shut-in Wells",
            x=0.5,
            xanchor="center",
            font=dict(size=20),
        ),
        xaxis=dict(
            title="X Coordinates",
            autorange=True,
            range=[x_min - x_pad, x_max + x_pad],
            gridcolor="grey",
            showgrid=True,
            titlefont=dict(size=16),
            tickfont=dict(size=14),
        ),
        yaxis=dict(
            title="Y Coordinates",
            autorange=True,
            range=[y_min - y_pad, y_max + y_pad],
            gridcolor="grey",
            showgrid=True,
            titlefont=dict(size=16),
            tickfont=dict(size=14),
        ),
        plot_bgcolor="#d3d3d3",
        coloraxis=dict(
            cmin=0,
            cmax=100,
            colorscale=[[0.0, "green"], [0.5, "white"], [1.0, "lightblue"]],
            colorbar=dict(
                title="WC (%)",
                titlefont=dict(size=16),
                tickfont=dict(size=14),
                thickness=25,
                len=0.6,
                x=1.02,
                xanchor="left"
            )
        ),
        legend=dict(
            title="Well Type",
            font=dict(size=14),
            orientation="h",
            x=0.5,
            xanchor="center",
            y=-0.1
        ),
        width=1800,
        height=1000,
        dragmode="pan",  # default to pan so users aren't forced to zoom
    )

    # 11) Render the chart via plotly_events (larger size, no flicker)
    selected_points = plotly_events(
        fig,
        click_event=True,
        key=f"bubble_map_{date_range[0]}_{date_range[1]}",
        override_width=1800,
        override_height=1000
    )

    # 12) Handle click: extract well_bore from customdata (fallback to coordinate match)
    if selected_points:
        first = selected_points[0]
        well_clicked = None

        # First try: pull well_bore from customdata
        if "customdata" in first and first["customdata"]:
            well_clicked = first["customdata"][0]
        else:
            # Fallback: match x,y against merged
            x_sel = first.get("x", None)
            y_sel = first.get("y", None)
            if x_sel is not None and y_sel is not None:
                match = merged[
                    (abs(merged["xcord"] - x_sel) < 1e-6)
                    & (abs(merged["ycord"] - y_sel) < 1e-6)
                ]
                if not match.empty:
                    well_clicked = match["well_bore"].iloc[0]
                else:
                    st.warning("No matching well_bore found for those coordinates.")

        # If a well_bore was found, display its PDF
        if well_clicked:
            st.markdown("---")
            st.write(f"**You clicked on well:** {well_clicked}")
            pdf_rows = all_files_df[all_files_df["well_bore"] == well_clicked]
            if not pdf_rows.empty:
                st.subheader(f"PDF Viewer for Clicked Well: {well_clicked}")
                display_pdf([well_clicked], pdf_rows)
            else:
                st.info(f"No PDF found for well {well_clicked}.")
    else:
        st.write("No well selected yet. Click any bubble above to view its PDF.")

# --- Main App Logic ---
st.title("Well File PDF Viewer & Bubble Map")

# Get filtered results
filtered_prod, all_files_df, filtered_files, header_df, company_selection, selected_well_bores = display_filters()

# --- Bubble Map Section ---
# Define a session state to track clicked well (for consistent PDF logic)
if 'well_clicked' not in st.session_state:
    st.session_state['well_clicked'] = None

if not filtered_prod.empty:
    # Filter fields only after well_bore selection for consistency
    if selected_well_bores:
        filtered_prod = filtered_prod[filtered_prod['well_bore'].isin(selected_well_bores)]
    fields = filtered_prod['field'].dropna().unique()
    date_range = (filtered_prod['date'].min(), filtered_prod['date'].max())

    if len(fields) > 0:
        display_bubble_map(header_df, filtered_prod, fields, date_range, all_files_df)
    else:
        st.warning("No valid fields in filtered data to plot bubble map.")
else:
    st.info("No production data to display bubble map.")

# --- Determine which well(s) to show PDF for ---
if st.session_state.get("well_clicked"):
    active_wells = [st.session_state['well_clicked']]
elif selected_well_bores:
    active_wells = selected_well_bores
else:
    active_wells = []

# --- Show PDFs for active well(s) ---
if active_wells:
    st.markdown("---")
    st.subheader("PDF Viewer for Selected Well(s)")
    display_pdf(active_wells, all_files_df)
else:
    st.info("Select a well or click a bubble to view its PDF(s).")