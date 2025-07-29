import base64
import sqlite3
import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path
from streamlit_plotly_events import plotly_events
from streamlit.components.v1 import html
import plotly.graph_objects as go
from urllib.parse import quote

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
    Load well_files_vis table: well_bore, file_path, file_type, file_category
    """
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT well_bore, file_path, file_type, file_category FROM well_files_vis", conn)
        conn.close()
        return df.dropna(subset=["file_path", "file_type", "file_category"])
    except Exception as e:
        st.warning(f"Could not load well_files_vis from {db_path}: {e}")
        return pd.DataFrame(columns=["well_bore", "file_path", "file_type", "file_category"])

def display_file(well_list: list[str], files_df: pd.DataFrame, file_category: str):
    """
    Fixed version - Auto-opens both WBS and CPI PDFs instantly
    Smaller popup windows positioned below each other
    """
    pdf_base_url = "https://iprdashboard.blob.core.windows.net/pdf-excel/"
    
    for well in well_list:
        st.write(f"### 📋 Well: **{well}**")
        
        # Get both WBS and CPI files for this well
        wbs_file = files_df[
            (files_df['well_bore'] == well) &
            (files_df['file_type'].str.lower() == 'pdf') &
            (files_df['file_category'].str.lower() == 'wbs')
        ]
        
        cpi_file = files_df[
            (files_df['well_bore'] == well) &
            (files_df['file_type'].str.lower() == 'pdf') &
            (files_df['file_category'].str.lower() == 'cpi')
        ]
        
        # Create unique ID for this well
        safe_well = well.replace('-', '_').replace(' ', '_').replace('.', '_').replace('/', '_')
        
        # Prepare URLs and filenames
        wbs_url = ""
        cpi_url = ""
        wbs_filename = "Not available"
        cpi_filename = "Not available"
        
        if not wbs_file.empty:
            wbs_filename = wbs_file.iloc[0]['file_path']
            encoded_wbs = quote(wbs_filename)
            wbs_url = f"{pdf_base_url}{encoded_wbs}"
        
        if not cpi_file.empty:
            cpi_filename = cpi_file.iloc[0]['file_path']
            encoded_cpi = quote(cpi_filename)
            cpi_url = f"{pdf_base_url}{encoded_cpi}"
        
        # Show file status
        col1, col2 = st.columns(2)
        with col1:
            if wbs_url:
                st.success(f"✅ **WBS**: {wbs_filename}")
            else:
                st.error("❌ **WBS**: Not available")
        
        with col2:
            if cpi_url:
                st.success(f"✅ **CPI**: {cpi_filename}")
            else:
                st.error("❌ **CPI**: Not available")
        
        # Only show button if at least one PDF exists
        if wbs_url or cpi_url:
            # Create the button and JavaScript
            button_html = f"""
            <div style="text-align: center; margin: 20px 0;">
                <button id="openBtn_{safe_well}" onclick="openPDFs_{safe_well}()" 
                        style="
                            padding: 15px 30px; 
                            background: linear-gradient(45deg, #007bff, #0056b3); 
                            color: white; 
                            border: none; 
                            border-radius: 8px; 
                            cursor: pointer; 
                            font-weight: bold;
                            font-size: 16px;
                            box-shadow: 0 3px 6px rgba(0,0,0,0.2);
                        ">
                    🚀 Open PDFs for {well}
                </button>
            </div>
            
            <script>
            function openPDFs_{safe_well}() {{
                console.log('Opening PDFs for {well}');
                
                // Calculate window sizes - smaller for well sketches
                var windowWidth = 700;
                var windowHeight = 500;
                var screenWidth = window.screen.width;
                var screenHeight = window.screen.height;
                
                // Center horizontally, stack vertically
                var leftPos = Math.max(0, (screenWidth - windowWidth) / 2);
                var topPos1 = Math.max(0, (screenHeight - (windowHeight * 2 + 60)) / 2);
                var topPos2 = topPos1 + windowHeight + 60;
                
                // Open WBS first
                {f'var wbsWindow = window.open("{wbs_url}", "WBS_{safe_well}", "width=" + windowWidth + ",height=" + windowHeight + ",left=" + leftPos + ",top=" + topPos1 + ",scrollbars=yes,resizable=yes,toolbar=no,menubar=no");' if wbs_url else ''}
                
                // Open CPI after short delay
                setTimeout(function() {{
                    {f'var cpiWindow = window.open("{cpi_url}", "CPI_{safe_well}", "width=" + windowWidth + ",height=" + windowHeight + ",left=" + leftPos + ",top=" + topPos2 + ",scrollbars=yes,resizable=yes,toolbar=no,menubar=no");' if cpi_url else ''}
                }}, 500);
                
                // Change button text
                document.getElementById("openBtn_{safe_well}").innerHTML = "✅ PDFs Opened";
                document.getElementById("openBtn_{safe_well}").style.background = "linear-gradient(45deg, #28a745, #20893a)";
            }}
            </script>
            """
            
            st.components.v1.html(button_html, height=100)
            
            # Add direct links as backup
            st.write("**Direct Links:**")
            link_cols = st.columns(2)
            with link_cols[0]:
                if wbs_url:
                    st.markdown(f"[🔗 WBS Direct Link]({wbs_url})")
            with link_cols[1]:
                if cpi_url:
                    st.markdown(f"[🔗 CPI Direct Link]({cpi_url})")
        
        else:
            st.warning(f"No PDF files found for well **{well}**")
        
        # Add separator between wells
        st.divider()
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

    filtered_df = df[
        (df['date'] >= selected_date_range[0]) &
        (df['date'] <= selected_date_range[1])
    ]
    filtered_df = filtered_df[filtered_df['field'].isin(selected_fields)]

    if 'zone' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['zone'].isin(selected_zones)]
    if 'type' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['type'].isin(selected_types)]

    return filtered_df

# --- UI Filters ---
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
    h1, h2, h3 = st.columns([1, 1, 1])
    with h1:
        company_selection = st.selectbox("**Select Company:**", list(company_options.keys()))
    db_path = company_options[company_selection]

    prod_df = load_vi_map(db_path)
    header_df = load_header_data(db_path)

    if prod_df.empty or header_df.empty:
        st.warning("No data available for this company.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), company_selection, []

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
            filtered_for_wells = prod_df[prod_df['field'].isin(selected_fields)]
            selected_well_bores = st.multiselect(
                "**Select Well Bores:**",
                filtered_for_wells['well_bore'].dropna().unique()
            )
        with col5:
            filtered_for_zones = header_df.copy()
            if selected_well_bores:
                filtered_for_zones = filtered_for_zones[
                    filtered_for_zones['well_bore'].isin(selected_well_bores)
                ]
            zone_options = sorted(filtered_for_zones['zone'].dropna().unique())
            selected_zones = st.multiselect("**Select Zones:**", zone_options)

    filtered_prod = apply_common_filters(
        prod_df,
        selected_date_range,
        selected_fields,
        selected_zones,
        selected_types
    )

    all_files_df = load_well_files(db_path)

    if selected_well_bores:
        filtered_files = all_files_df[
            all_files_df['well_bore'].isin(selected_well_bores)
        ]
    else:
        filtered_files = pd.DataFrame()

    return filtered_prod, all_files_df, filtered_files, header_df, company_selection, selected_well_bores

def display_bubble_map(header_df, vi_df, fields, date_range, all_files_df):
    """
    1) Build a single Plotly figure containing producers + WIs with a visible WC colorbar.
    2) On click, grab well_bore from customdata or fallback to matching (x, y).
    3) Update session state to trigger file display in main logic.
    """
    df = apply_common_filters(vi_df, date_range, fields, [], [])
    oilw = df.groupby("well_bore").agg({"oil": "sum", "wc": "mean"}).reset_index()
    oilw.columns = ["well_bore", "cumm", "avg_wc"]
    oilw["avg_wc"] = oilw["avg_wc"].round(2)

    date_diff = (date_range[1] - date_range[0]).days
    if date_diff > 30:
        oilw["cumm"] = oilw["cumm"] / 1000
        oilw["cumm_fmt"] = oilw["cumm"].apply(lambda x: f"{int(x):,} Mbbl")
    else:
        oilw["cumm_fmt"] = oilw["cumm"].apply(lambda x: f"{int(x):,} bbl")

    merged = header_df.merge(oilw, on="well_bore", how="inner")
    merged["xcord"] = pd.to_numeric(merged["xcord"], errors="coerce")
    merged["ycord"] = pd.to_numeric(merged["ycord"], errors="coerce")
    merged.dropna(subset=["xcord", "ycord"], inplace=True)

    merged["custom_text"] = merged.apply(
        lambda row: (
            f"<span style='font-size:18px;'><b>{row['well_bore']}</b></span>"
            if row["type"] == "WI"
            else
            f"<span style='font-size:18px;'>"
            f"<b>{row['well_bore']}</b><br>"
            f"<b>Oil:</b> {row['cumm_fmt']}<br>"
            f"<b>WC:</b> {row['avg_wc']}%"
            f"</span>"
        ),
        axis=1,
    )

    producers = merged[merged["type"] == "producer"].copy()
    wis = merged[merged["type"] == "WI"].copy()
    overlap_coords = set(zip(wis["xcord"], wis["ycord"]))
    producers = producers[
        ~producers[["xcord", "ycord"]].apply(tuple, axis=1).isin(overlap_coords)
    ]

    producers["has_oil"] = producers["cumm"].notna() & (producers["cumm"] > 0)
    producers_colored = producers[producers["has_oil"]].copy()
    producers_na = producers[~producers["has_oil"]].copy()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=producers_colored["xcord"],
            y=producers_colored["ycord"],
            mode="markers+text",
            marker=dict(
                size=40,
                color=producers_colored["avg_wc"],
                colorscale=[[0.0, "green"], [0.5, "white"], [1.0, "lightblue"]],
                cmin=0,
                cmax=100,
                colorbar=dict(
                    title="WC (%)",
                    titlefont=dict(size=16),
                    tickfont=dict(size=14),
                    thickness=25,
                    len=0.6,
                    x=1.02,
                    xanchor="left",
                ),
                coloraxis="coloraxis"
            ),
            text=producers_colored["custom_text"],
            textposition="top center",
            name="Producers",
            customdata=producers_colored[["well_bore"]].values,
            hoverinfo="text"
        )
    )

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

    x_min, x_max = merged["xcord"].min(), merged["xcord"].max()
    y_min, y_max = merged["ycord"].min(), merged["ycord"].max()
    x_range = x_max - x_min if (x_max - x_min) != 0 else 1
    y_range = y_max - y_min if (y_max - y_min) != 0 else 1
    x_pad = x_range * 0.1
    y_pad = y_range * 0.1

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
        dragmode="pan",
    )

    selected_points = plotly_events(
        fig,
        click_event=True,
        key=f"bubble_map_{date_range[0]}_{date_range[1]}",
        override_width=1800,
        override_height=1000
    )

    if selected_points:
        first = selected_points[0]
        well_clicked = None

        if "customdata" in first and first["customdata"]:
            well_clicked = first["customdata"][0]
        else:
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

        if well_clicked:
            st.session_state['well_clicked'] = well_clicked
            st.markdown("---")
            st.write(f"**You clicked on well:** {well_clicked}")
    else:
        st.write("No well selected yet. Click any bubble above to view its WBS and CPI files.")

# --- Main App Logic ---
st.title("Well File WBS & CPI Viewer with Bubble Map")

filtered_prod, all_files_df, filtered_files, header_df, company_selection, selected_well_bores = display_filters()
# Reset clicked well if it's no longer in selected well bores
if 'well_clicked' in st.session_state:
    if st.session_state['well_clicked'] not in selected_well_bores:
        del st.session_state['well_clicked']

if 'well_clicked' not in st.session_state:
    st.session_state['well_clicked'] = None

if not filtered_prod.empty:
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

# --- Determine which well(s) to show files for ---
if st.session_state.get("well_clicked"):
    active_wells = [st.session_state['well_clicked']]
elif selected_well_bores:
    active_wells = selected_well_bores
else:
    active_wells = []

# --- Show WBS and CPI files for active well(s) ---
if active_wells:
    st.markdown("---")
    st.subheader("WBS Viewer for Selected Well(s)")
    display_file(active_wells, all_files_df, "WBS")
    st.subheader("CPI Viewer for Selected Well(s)")
    display_file(active_wells, all_files_df, "CPI")
else:
    st.info("Select a well or click a bubble to view its WBS and CPI files.")