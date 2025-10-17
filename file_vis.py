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
import numpy as np
from datetime import datetime
import datetime as dt
from utils.login_panel import AuthManager

# Import from arps utilities
from utils.arps_classes_original import Config, DatabaseManager, ARPSModel, PlotManager



#getting user ID
if AuthManager.is_logged_in():
        
        user_id, username = AuthManager.get_current_user()

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

def get_unique_ids_for_wellbore(well_bore: str, company: str, dca_time: str = "monthly") -> list:
    """
    Get all unique_id(s) associated with a well_bore from production data
    """
    try:
        if company == "Alamein":
            conn = DatabaseManager.get_connection(Config.MAIN_DB_PATH)
            if dca_time == "daily":
                query = f"SELECT DISTINCT unique_id FROM st_data_plot WHERE well_bore = '{well_bore}'"
            else:
                query = f"SELECT DISTINCT unique_id FROM monthly_data WHERE well_bore = '{well_bore}'"
        else:  # Petrosila
            conn = DatabaseManager.get_connection(Config.PETROSILA_DB_PATH)
            query = f"SELECT DISTINCT unique_id FROM st_data WHERE well_bore = '{well_bore}'"
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df['unique_id'].dropna().unique().tolist()
    except Exception as e:
        st.warning(f"Error getting unique_ids for {well_bore}: {e}")
        return []

def load_forecast_cases_for_well(unique_ids: list) -> pd.DataFrame:
    """
    Load forecast cases where well_name matches any of the unique_ids
    """
    try:
        cases_df = DatabaseManager.load_forecast_cases()
        if cases_df.empty:
            return pd.DataFrame()
        
        # Filter cases where well_name is in unique_ids list
        filtered_cases = cases_df[cases_df['well_name'].isin(unique_ids)]
        return filtered_cases
    except Exception as e:
        st.warning(f"Error loading forecast cases: {e}")
        return pd.DataFrame()

def display_production_analysis(well_bore: str, company: str):
    """
    Display production analysis chart for a selected well_bore
    Similar to the existing wells analysis in arps.py
    """
    st.markdown("---")
    st.subheader(f"Production Analysis: {well_bore}")
    
    # Determine resolution based on company
    if company == "Petrosila":
        dca_time = "daily"
        unit_tag = "bbl/day"
        st.info("Petrosila data - Daily resolution")
    else:  # Alamein
        resolution_option = st.radio(
            "Select Resolution:",
            options=["Monthly", "Daily"],
            index=0,
            key=f"resolution_{well_bore}",
            horizontal=True
        )
        dca_time = "daily" if resolution_option == "Daily" else "monthly"
        unit_tag = "bbl/day" if dca_time == "daily" else "bbl/month"
    
    # Get unique_id(s) for this well_bore
    unique_ids = get_unique_ids_for_wellbore(well_bore, company, dca_time)
    
    if not unique_ids:
        st.warning(f"No unique_id found for well_bore: {well_bore}")
        return
    
    st.info(f"Found unique_id(s): {', '.join(unique_ids)}")
    
    # Load forecast cases for these unique_ids
    cases_df = load_forecast_cases_for_well(unique_ids)
    
    if cases_df.empty:
        st.info(f"âš ï¸ No forecast cases found for this well in the database. Create a case in the 'Existing Wells Analysis' tab first.")
        return
    
    # Filter cases by dca_time if multiple resolutions exist
    if 'dca_time' in cases_df.columns:
        available_dca_times = cases_df['dca_time'].dropna().unique()
        if dca_time in available_dca_times:
            cases_df = cases_df[cases_df['dca_time'] == dca_time]
        elif len(available_dca_times) > 0:
            st.warning(f"âš ï¸ No cases found with {dca_time} resolution. Showing {available_dca_times[0]} instead.")
            dca_time = available_dca_times[0]
            unit_tag = "bbl/day" if dca_time == "daily" else "bbl/month"
            cases_df = cases_df[cases_df['dca_time'] == dca_time]
    
    # Let user select a case
    case_labels = cases_df['case_label'].unique().tolist()
    
    if len(case_labels) == 0:
        st.warning("No valid cases available")
        return
    
    selected_case = st.selectbox(
        "Select Forecast Case:",
        case_labels,
        key=f"case_select_{well_bore}"
    )
    
    # Get case data
    case_data = cases_df[cases_df['case_label'] == selected_case].iloc[0]
    
    # Display case info
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Case Label", case_data['case_label'])
        st.metric("Well Name", case_data['well_name'])
    with col_info2:
        st.metric(f"Initial Rate (qi)", f"{case_data['qi']:.1f} {unit_tag}")
        st.metric(f"Decline Rate (di)", f"{case_data['di']:.4f}")
    with col_info3:
        st.metric("Hyperbolic Factor (b)", f"{case_data['b']:.2f}")
        st.metric("Effective Date", str(case_data['eff_date']))
    
    # Load production data for this unique_id
    try:
        unique_id = case_data['well_name']
        df_prod = DatabaseManager.load_production_data_by_selection(
            selection_type="well",
            entity_identifier=unique_id,
            company=company,
            dca_time=dca_time
        )
        
        if df_prod is None or df_prod.empty:
            st.warning(f"No production data found for {unique_id}")
            return
        
        # Convert date column
        df_prod['date'] = pd.to_datetime(df_prod['date'])
        
        # Aggregate by date (sum if multiple entries per date)
        plot_df = df_prod.groupby('date')['net'].sum().reset_index()
        plot_df.columns = ['date', 'net']
        
        # Get case parameters
        qi_forecast = float(case_data['qi'])
        qi_regressed = float(case_data.get('qi_regressed', qi_forecast))
        di = float(case_data['di'])
        b = float(case_data['b'])
        eff_date = pd.to_datetime(case_data['eff_date'])
        ti_selected = pd.to_datetime(case_data.get('ti_selected', eff_date))
        q_abandon = float(case_data.get('q_abandon', 10.0 if dca_time == 'daily' else 300.0))
        end_of_lease = case_data.get('end_of_lease', dt.date(2039, 12, 31))
        if isinstance(end_of_lease, str):
            end_of_lease = pd.to_datetime(end_of_lease).date()
        end_of_lease = pd.to_datetime(end_of_lease)
        
        # Create forecast profile
        forecast_freq = "D" if dca_time == "daily" else "MS"
        
        forecast_profile = ARPSModel.create_production_profile(
            start_date=eff_date,
            end_date=end_of_lease,
            qi=qi_forecast,
            di=di,
            b=b,
            q_abandon=q_abandon,
            frequency=forecast_freq
        )
        
        # Create history match profile
        history_end = eff_date - pd.Timedelta(days=1) if dca_time == 'daily' else eff_date - pd.DateOffset(months=1)
        
        history_profile = ARPSModel.create_production_profile(
            start_date=ti_selected,
            end_date=history_end,
            qi=qi_regressed,
            di=di,
            b=b,
            q_abandon=0,
            frequency=forecast_freq
        )
        
        # Prepare data for plotting
        if not forecast_profile.empty:
            rate_column = 'rate' if 'rate' in forecast_profile.columns else forecast_profile.columns[1]
            forecast_plot = forecast_profile[[forecast_profile.columns[0], rate_column]].copy()
            forecast_plot.columns = ['date', 'rate']
        else:
            forecast_plot = pd.DataFrame(columns=['date', 'rate'])
        
        if not history_profile.empty:
            rate_column = 'rate' if 'rate' in history_profile.columns else history_profile.columns[1]
            history_plot = history_profile[[history_profile.columns[0], rate_column]].copy()
            history_plot.columns = ['date', 'rate']
        else:
            history_plot = None
        
        # Create combined plot
        st.subheader(" Historical Production + ARPS Forecast")
        
        st.info("""
        **Plot explanation:**
        - **Green dots**: Historical production data
        - **Red dots**: ARPS history match using regressed qi
        -  **Blue solid line**: Future forecast using forecast qi
        """)
        
        fig_combined = PlotManager.create_combined_plot(
            historical_df=plot_df,
            forecast_profile=forecast_plot,
            title=f"Production Analysis: {well_bore}",
            unit=unit_tag,
            history_match_df=history_plot
        )
        
        st.plotly_chart(fig_combined, use_container_width=True, key=f"combined_plot_{well_bore}_{selected_case}")
        
        # Calculate EUR
        st.subheader("EUR Summary")
        
        historical_cutoff = eff_date.date()
        cutoff_timestamp = pd.Timestamp(historical_cutoff)
        historical_cum = df_prod[df_prod['date'] < cutoff_timestamp]['net'].sum()
        
        if not forecast_profile.empty:
            forecast_eur = ARPSModel.calculate_eur(forecast_profile, 0.0)
            total_eur = ARPSModel.calculate_eur(forecast_profile, historical_cum)
        else:
            forecast_eur = 0.0
            total_eur = historical_cum
        
        col_eur1, col_eur2, col_eur3 = st.columns(3)
        with col_eur1:
            st.metric("Historical Production", f"{historical_cum/1_000:.3f} Mstb")
        with col_eur2:
            st.metric("Forecast EUR", f"{forecast_eur/1_000:.3f} Mstb")
        with col_eur3:
            st.metric("**Total EUR**", f"{total_eur/1_000:.3f} Mstb")
        
    except Exception as e:
        st.error(f"Error generating production analysis: {e}")
        import traceback
        st.code(traceback.format_exc())

def display_file(well_list: list[str], files_df: pd.DataFrame):
    """
    Display three buttons (WBS, CPI, Well History) side by side for each well
    """
    pdf_base_url = "https://iprdashboard.blob.core.windows.net/pdf-excel/"
    
    for well in well_list:
        st.write(f"‹ Well: **{well}**")
        
        # Get files for this well
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
        
        history_file = files_df[
            (files_df['well_bore'] == well) &
            (files_df['file_type'].str.lower() == 'xlsx') &
            (files_df['file_category'].str.lower() == 'well_history')
        ]
        
        # Create unique ID for this well
        safe_well = well.replace('-', '_').replace(' ', '_').replace('.', '_').replace('/', '_')
        
        # Prepare URLs and filenames
        wbs_url = ""
        cpi_url = ""
        history_url = ""
        wbs_filename = "Not available"
        cpi_filename = "Not available"
        history_filename = "Not available"
        
        if not wbs_file.empty:
            wbs_filename = wbs_file.iloc[0]['file_path']
            encoded_wbs = quote(wbs_filename)
            wbs_url = f"{pdf_base_url}{encoded_wbs}"
        
        if not cpi_file.empty:
            cpi_filename = cpi_file.iloc[0]['file_path']
            encoded_cpi = quote(cpi_filename)
            cpi_url = f"{pdf_base_url}{encoded_cpi}"
            
        if not history_file.empty:
            history_filename = history_file.iloc[0]['file_path']
            encoded_history = quote(history_filename)
            history_url = f"{pdf_base_url}{encoded_history}"
        
        # Show file status in columns
        col1, col2, col3 = st.columns(3)
        with col1:
            if wbs_url:
                st.success(f"âœ… **WBS**: {wbs_filename}")
            else:
                st.error("âŒ **WBS**: Not available")
        
        with col2:
            if cpi_url:
                st.success(f"âœ… **CPI**: {cpi_filename}")
            else:
                st.error("âŒ **CPI**: Not available")
                
        with col3:
            if history_url:
                st.success(f"âœ… **Well History**: {history_filename}")
            else:
                st.error("âŒ **Well History**: Not available")
        
        # Create the three buttons side by side
        button_html = f"""
        <div style="display: flex; justify-content: center; gap: 20px; margin: 20px 0; flex-wrap: wrap;">
            {f'''
            <button id="wbsBtn_{safe_well}" onclick="openWBS_{safe_well}()" 
                    style="
                        padding: 15px 25px; 
                        background: linear-gradient(45deg, #28a745, #20893a); 
                        color: white; 
                        border: none; 
                        border-radius: 8px; 
                        cursor: pointer; 
                        font-weight: bold;
                        font-size: 14px;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.2);
                        min-width: 150px;
                    ">
                "„ Open WBS
            </button>
            ''' if wbs_url else '''
            <button style="
                        padding: 15px 25px; 
                        background: #6c757d; 
                        color: white; 
                        border: none; 
                        border-radius: 8px; 
                        font-weight: bold;
                        font-size: 14px;
                        min-width: 150px;
                        cursor: not-allowed;
                    " disabled>
                "„ WBS N/A
            </button>
            '''}
            
            {f'''
            <button id="cpiBtn_{safe_well}" onclick="openCPI_{safe_well}()" 
                    style="
                        padding: 15px 25px; 
                        background: linear-gradient(45deg, #007bff, #0056b3); 
                        color: white; 
                        border: none; 
                        border-radius: 8px; 
                        cursor: pointer; 
                        font-weight: bold;
                        font-size: 14px;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.2);
                        min-width: 150px;
                    ">
                "Š Open CPI
            </button>
            ''' if cpi_url else '''
            <button style="
                        padding: 15px 25px; 
                        background: #6c757d; 
                        color: white; 
                        border: none; 
                        border-radius: 8px; 
                        font-weight: bold;
                        font-size: 14px;
                        min-width: 150px;
                        cursor: not-allowed;
                    " disabled>
                "Š CPI N/A
            </button>
            '''}
            
            {f'''
            <button id="historyBtn_{safe_well}" onclick="openHistory_{safe_well}()" 
                    style="
                        padding: 15px 25px; 
                        background: linear-gradient(45deg, #ffc107, #e0a800); 
                        color: black; 
                        border: none; 
                        border-radius: 8px; 
                        cursor: pointer; 
                        font-weight: bold;
                        font-size: 14px;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.2);
                        min-width: 150px;
                    ">
                "ˆ Well History
            </button>
            ''' if history_url else '''
            <button style="
                        padding: 15px 25px; 
                        background: #6c757d; 
                        color: white; 
                        border: none; 
                        border-radius: 8px; 
                        font-weight: bold;
                        font-size: 14px;
                        min-width: 150px;
                        cursor: not-allowed;
                    " disabled>
                "ˆ History N/A
            </button>
            '''}
        </div>
        
        <script>
        function openWBS_{safe_well}() {{
            console.log('Opening WBS for {well}');
            var windowWidth = 700;
            var windowHeight = 500;
            var screenWidth = window.screen.width;
            var screenHeight = window.screen.height;
            var leftPos = Math.max(0, (screenWidth - windowWidth) / 2);
            var topPos = Math.max(0, (screenHeight - windowHeight) / 2);
            
            var wbsWindow = window.open("{wbs_url}", "WBS_{safe_well}", 
                "width=" + windowWidth + ",height=" + windowHeight + 
                ",left=" + leftPos + ",top=" + topPos + 
                ",scrollbars=yes,resizable=yes,toolbar=no,menubar=no");
            
            document.getElementById("wbsBtn_{safe_well}").innerHTML = "WBS Opened";
        }}
        
        function openCPI_{safe_well}() {{
            console.log('Opening CPI for {well}');
            var windowWidth = 700;
            var windowHeight = 500;
            var screenWidth = window.screen.width;
            var screenHeight = window.screen.height;
            var leftPos = Math.max(0, (screenWidth - windowWidth) / 2);
            var topPos = Math.max(0, (screenHeight - windowHeight) / 2);
            
            var cpiWindow = window.open("{cpi_url}", "CPI_{safe_well}", 
                "width=" + windowWidth + ",height=" + windowHeight + 
                ",left=" + leftPos + ",top=" + topPos + 
                ",scrollbars=yes,resizable=yes,toolbar=no,menubar=no");
            
            document.getElementById("cpiBtn_{safe_well}").innerHTML = "CPI Opened";
        }}
        
        function openHistory_{safe_well}() {{
            console.log('Opening Well History for {well}');
            var windowWidth = 1000;
            var windowHeight = 700;
            var screenWidth = window.screen.width;
            var screenHeight = window.screen.height;
            var leftPos = Math.max(0, (screenWidth - windowWidth) / 2);
            var topPos = Math.max(0, (screenHeight - windowHeight) / 2);
            
            // Create iframe URL for Excel online viewer
            var excelViewerUrl = "https://view.officeapps.live.com/op/embed.aspx?src=" + encodeURIComponent("{history_url}");
            
            // Create a new window with iframe content
            var historyWindow = window.open("", "History_{safe_well}", 
                "width=" + windowWidth + ",height=" + windowHeight + 
                ",left=" + leftPos + ",top=" + topPos + 
                ",scrollbars=yes,resizable=yes,toolbar=yes,menubar=no");
            
            // Write iframe content to the new window
            historyWindow.document.write(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Well History - {well}</title>
                    <style>
                        body {{ margin: 0; padding: 0; }}
                        iframe {{ width: 100%; height: 100vh; border: none; }}
                    </style>
                </head>
                <body>
                    <iframe src="${{excelViewerUrl}}" 
                            title="Well History - {well}"
                            allowfullscreen>
                        <p>Your browser doesn't support iframes. 
                        <a href="{history_url}" target="_blank">Click here to download the file</a></p>
                    </iframe>
                </body>
                </html>
            `);
            historyWindow.document.close();
            
            document.getElementById("historyBtn_{safe_well}").innerHTML = "History Opened";
        }}
        </script>
        """
        
        st.components.v1.html(button_html, height=120)
        
        # Add direct links as backup
        if wbs_url or cpi_url or history_url:
            st.write("**Direct Links:**")
            link_cols = st.columns(3)
            with link_cols[0]:
                if wbs_url:
                    st.markdown(f"— WBS Direct Link]({wbs_url})")
            with link_cols[1]:
                if cpi_url:
                    st.markdown(f"— CPI Direct Link]({cpi_url})")
            with link_cols[2]:
                if history_url:
                    st.markdown(f"— Well History Direct Link]({history_url})")
        
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
    db2 =  Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
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

            text="Bubble Map WC Gradient | Black = Shut-in Wells",
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
        st.write("No well selected yet. Click any bubble above to view its files.")

# --- Main App Logic ---
st.title("Well File Viewer - WBS, CPI & Well History")

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

# --- Show files for active well(s) ---
if active_wells:
    st.markdown("---")
    st.subheader(" Well Files Viewer")
    display_file(active_wells, all_files_df)
    
    # ===== NEW: Production Analysis Section =====
    # Show production analysis for the first active well (or clicked well)
    well_to_analyze = active_wells[0]
    display_production_analysis(well_to_analyze, company_selection)
    
else:
    st.info("Select a well or click a bubble to view its files (WBS, CPI, Well History).")