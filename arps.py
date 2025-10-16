import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date
import plotly.graph_objs as go
import plotly.express as px
from scipy.optimize import curve_fit
import os
import calendar
import datetime
from dateutil.relativedelta import relativedelta
from utils.arps_classes_original import Config, DatabaseManager, ARPSModel, PlotManager
import time
import zipfile
import io
from typing import List, Dict, Tuple
from utils.css_style import load_custom_css_main
from streamlit import session_state as state
from utils.login_panel import AuthManager


# =================== MAIN APPLICATION ===================
def main():
    
    load_custom_css_main()
    st.markdown('<div class="main-header"><h1>🌟 Polaris Production Planner</h1></div>', unsafe_allow_html=True)
   
    tab1, tab2, tab3 = st.tabs([
        "📊 Existing Wells Analysis",
        "🔮 New Wells Forecasting",
        "📈 Scenario Comparison"
    ])
   
    with tab1:
        render_existing_wells_analysis()
    with tab2:
        render_new_wells_forecasting()
    with tab3:
        render_scenario_comparison()

def render_existing_wells_analysis():
    """Render existing wells analysis interface with enhanced history matching visualization"""
    st.header("📊 Existing Wells Analysis & Forecasting")
    if AuthManager.is_logged_in():
        
        user_id, username = AuthManager.get_current_user()
        
    
    # Load forecast cases first
    cases_df = DatabaseManager.load_forecast_cases()
    existing_cases = cases_df[cases_df['case_label'].str.contains('existing', case=False, na=False)] if not cases_df.empty else pd.DataFrame()
   
    # =================== CASE SELECTION SECTION ===================
    col1, col2 = st.columns([1, 1])
   
    with col1:
        st.subheader("🔧 Case Selection")
        case_mode = st.radio(
            "Select Mode:",
            options=["Create New Case", "Load Existing Case"],
            key="case_mode_selection"
        )
   
    # Initialize variables
    selected_case_data = None
    case_params = None
    case_date_range = None
    df = None
    selected_company = None
    dca_time = "monthly"
   
        # EXISTING CASE MODE - Load using entity_identifier and selection_type
    # EXISTING CASE MODE - Load using entity_identifier and selection_type
    if case_mode == "Load Existing Case":
        with col2:
            if not existing_cases.empty:
                selected_case = st.selectbox(
                    "Select Existing Case:",
                    existing_cases['case_label'].unique(),
                    key="existing_case_select"
                )

                # Reset session state when switching cases
                if 'last_selected_case' not in st.session_state:
                    st.session_state.last_selected_case = None
                if st.session_state.last_selected_case != selected_case:
                    st.session_state.lasso_params = {}
                    st.session_state.last_selected_case = selected_case

                if selected_case:
                    # Get all rows for this case
                    selected_case_data = existing_cases[existing_cases['case_label'] == selected_case]

                    if not selected_case_data.empty:
                        first_row = selected_case_data.iloc[0]
                        selection_type = first_row.get("selection_type", "well")
                        entity_identifier = first_row.get("entity_identifier", first_row.get("well_name", "Unknown"))
                        selected_company = first_row.get("company_name", entity_identifier)
                        
                        # ===== NEW: Let user choose dca_time if multiple exist =====
                        available_dca_times = selected_case_data['dca_time'].dropna().unique().tolist()
                        
                        if len(available_dca_times) > 1:
                            # Multiple dca_time values exist - let user choose
                            dca_time = st.selectbox(
                                "Select Resolution:",
                                options=available_dca_times,
                                key="case_dca_time_selector",
                                format_func=lambda x: "Daily" if x == "daily" else "Monthly"
                            )
                            st.info(f"📊 This case has both Daily and Monthly data. Showing: {dca_time.capitalize()}")
                            
                            # Filter case data to only include rows matching selected dca_time
                            selected_case_data = selected_case_data[selected_case_data['dca_time'] == dca_time]
                        else:
                            # Only one dca_time exists - use it
                            dca_time = available_dca_times[0] if available_dca_times else "monthly"
                        
                        # Override for Petrosila
                        if selected_company == "Petrosila":
                            dca_time = "daily"

                        unit_tag = "bbl/day" if dca_time == "daily" else "bbl/month"
                        df_list = []

                        # -------------------- MAIN LOADING LOGIC --------------------
                        # Now load data based on the SELECTED dca_time
                        if selection_type == "company":
                            df = DatabaseManager.load_production_data(
                                company=selected_company,
                                dca_time=dca_time
                            )

                        elif selection_type == "field":
                            df = DatabaseManager.load_production_data_by_selection(
                                selection_type="field",
                                entity_identifier=entity_identifier,
                                company=selected_company,
                                dca_time=dca_time
                            )

                        elif selection_type == "multi_field":
                            fields = [f.strip() for f in entity_identifier.split("|") if f.strip()]
                            for field_name in fields:
                                try:
                                    sub_df = DatabaseManager.load_production_data_by_selection(
                                        selection_type="field",
                                        entity_identifier=field_name,
                                        company=selected_company,
                                        dca_time=dca_time
                                    )
                                    if sub_df is not None and not sub_df.empty:
                                        df_list.append(sub_df)
                                except Exception as e:
                                    st.warning(f"⚠️ Could not load field '{field_name}': {e}")
                            df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

                        elif selection_type == "multi_well":
                            wells = [w.strip() for w in entity_identifier.split("|") if w.strip()]
                            for well in wells:
                                try:
                                    sub_df = DatabaseManager.load_production_data_by_selection(
                                        selection_type="well",
                                        entity_identifier=well,
                                        company=selected_company,
                                        dca_time=dca_time
                                    )
                                    if sub_df is not None and not sub_df.empty:
                                        df_list.append(sub_df)
                                except Exception as e:
                                    st.warning(f"⚠️ Could not load well '{well}': {e}")
                            df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

                        elif selection_type == "well":
                            # Load all wells in same case_label WITH THE SELECTED dca_time
                            case_wells = selected_case_data["well_name"].dropna().unique().tolist()
                            for well in case_wells:
                                try:
                                    sub_df = DatabaseManager.load_production_data_by_selection(
                                        selection_type="well",
                                        entity_identifier=well,
                                        company=selected_company,
                                        dca_time=dca_time
                                    )
                                    if sub_df is not None and not sub_df.empty:
                                        df_list.append(sub_df)
                                except Exception as e:
                                    st.warning(f"⚠️ Could not load well '{well}': {e}")
                            df = pd.concat(df_list, ignore_index=True) if df_list else pd.DataFrame()

                        else:
                            df = pd.DataFrame()  # fallback safety

                        # -------------------- VALIDATION --------------------
                        if df is not None and not df.empty:
                            case_date_range = (df["date"].min(), df["date"].max())
                            st.success(f"✅ Loaded data for case '{selected_case}' ({selection_type}: {entity_identifier}) - Resolution: {dca_time}")
                        else:
                            st.error(f"⚠️ No production data found for {selection_type}: {entity_identifier} with {dca_time} resolution")
                            return

                        # -------------------- STORE CASE METADATA --------------------
                        case_params = {
                            "case_label": first_row["case_label"],
                            "case_id": first_row.get("case_id", None),
                            "dca_time": dca_time,  # ===== Use the SELECTED dca_time =====
                            "company_name": selected_company,
                            "selection_type": selection_type,
                            "entity_identifier": entity_identifier,
                            "full_case_data": selected_case_data,  # ===== Already filtered by dca_time =====
                        }

            else:
                st.info("No existing cases available. Please create a new case.")
                case_mode = "Create New Case"
   
    # NEW CASE MODE
    if case_mode == "Create New Case":
        with col2:
            st.subheader("🏢 Company Selection & Resolution")
            div1, div2 = st.columns([1, 1])
            with div1:
                selected_company = st.selectbox(
                    "Select Company:",
                    options=["Alamein", "Petrosila"],
                    index=0,
                    key="company_selector"
                )
      
            forecast_resolution_options = ["Monthly", "Daily"] if selected_company == "Alamein" else ["Daily"]
            forecast_resolution = st.radio(
                "Forecast Resolution",
                options=forecast_resolution_options,
                index=0,
                key="new_case_resolution"
            )
            if selected_company == "Petrosila":
                st.info("Petrosila only supports daily resolution.")
       
        dca_time = "daily" if forecast_resolution == "Daily" else "monthly"
        unit_tag = "bbl/day" if dca_time == "daily" else "bbl/month"
        
        # Load ALL production data initially
        df = DatabaseManager.load_production_data(
            company=selected_company,
            dca_time=dca_time
        )
        
       
    
   
    # =================== DATA FILTERS SECTION ===================
    st.subheader("🔍 Data Filters")
   
    col1, col2, col3, col4 = st.columns(4)
   
    with col1:
        if case_mode == "Load Existing Case" and case_date_range:
            
            date_range = st.slider(
                "Date Range (Case Wells)",
                min_value=case_date_range[0],
                max_value=case_date_range[1],
                value=case_date_range,
                key="case_date_range_slider"
            )
        else:
            date_range = st.slider(
                "Date Range",
                min_value=df['date'].min(),
                max_value=df['date'].max(),
                value=(df['date'].min(), df['date'].max()),
                key="new_case_date_range_slider"
            )
   
    with col2:
        available_fields = df['field'].unique() if 'field' in df.columns else []
        
        # Set default fields based on case selection
        if case_mode == "Load Existing Case" and case_params:
            # Determine fields based on selection_type
            if case_params['selection_type'] == "field":
                default_fields = [case_params['entity_identifier']]
            elif case_params['selection_type'] == "multi_field":
                default_fields = case_params['entity_identifier'].split("|")
            else:
                # For well-based cases, get fields from loaded data
                if 'field' in df.columns:
                    default_fields = df['field'].unique().tolist()
                else:
                    default_fields = []
        else:
            default_fields = []
    
        selected_fields = st.multiselect(
            "Fields",
            available_fields,
            default=default_fields,
            key="fields_select"
        )

    with col3:
        available_wells = df['unique_id'].unique()
        if selected_fields and 'field' in df.columns:
            available_wells = df[df['field'].isin(selected_fields)]['unique_id'].unique()
   
        # Set default wells based on case selection
        if case_mode == "Load Existing Case" and case_params:
            # Determine wells based on selection_type
            if case_params['selection_type'] == "well":
                # 🧠 Load all wells that belong to this case_label
                default_wells = case_params['full_case_data']['well_name'].unique().tolist()
                

            elif case_params['selection_type'] == "multi_well":
                default_wells = case_params['entity_identifier'].split("|")
            else:
                # For field-based cases, show all wells in loaded data
                default_wells = df['unique_id'].unique().tolist()
            
            # Filter to only include wells that exist in available data
            default_wells = [w for w in default_wells if w in available_wells]
        else:
            default_wells = []
        
        
        selected_wells = st.multiselect(
            "Well IDs",
            available_wells,
            default=default_wells,
            key="wells_select"
        )
       
        # Clear lasso_params when wells change
        wells_key = "_".join(sorted(selected_wells)) if selected_wells else ""
        if 'last_selected_wells' not in st.session_state:
            st.session_state.last_selected_wells = ""
        if st.session_state.last_selected_wells != wells_key:
            keys_to_clear = ['lasso_params']
            widget_patterns = ['existing_qi_forecast_', 'existing_qi_regressed_',
                             'existing_di_', 'existing_b_', 'ti_selected_', 'existing_eff_date_',
                             'existing_q_abandon_', 'existing_end_of_lease_']
           
            for key in list(st.session_state.keys()):
                if key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                elif any(pattern in key for pattern in widget_patterns):
                    del st.session_state[key]
           
            st.session_state.last_selected_wells = wells_key
   
    with col4:
        if selected_wells:
            available_zones = df[df['unique_id'].isin(selected_wells)]['zone'].unique() if 'zone' in df.columns else []
        else:
            available_zones = df['zone'].unique() if 'zone' in df.columns else []
       
        default_zones = available_zones.tolist() if case_mode == "Load Existing Case" else []
        selected_zones = st.multiselect(
            "Zones",
            available_zones,
            default=default_zones,
            key="zones_select"
        )
   
    # Apply filters
    filtered_df = df.copy()
   
    # Apply date filter
    start_date = pd.Timestamp(date_range[0]) if hasattr(date_range[0], 'date') else pd.Timestamp(date_range[0])
    end_date = pd.Timestamp(date_range[1]) if hasattr(date_range[1], 'date') else pd.Timestamp(date_range[1])
   
    if filtered_df['date'].dtype == 'object':
        filtered_df['date'] = pd.to_datetime(filtered_df['date'])
   
    filtered_df = filtered_df[
        (filtered_df['date'] >= start_date) &
        (filtered_df['date'] <= end_date)
    ]
   
    # Apply field filter
    if selected_fields and 'field' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['field'].isin(selected_fields)]
   
    # Apply wells filter
    if selected_wells:
        filtered_df = filtered_df[filtered_df['unique_id'].isin(selected_wells)]
   
    # Extract parameters for selected wells (AFTER filtering)
    if case_mode == "Load Existing Case" and case_params and 'full_case_data' in case_params:
        if selected_wells:
            # Get parameters matching the selected wells
            well_case_rows = case_params['full_case_data'][
                case_params['full_case_data']['well_name'].isin(selected_wells)
            ]
            
            if not well_case_rows.empty:
                # ===== CHANGE: Always use the FIRST selected well's parameters =====
                param_row = well_case_rows.iloc[0]
            else:
                # No matching wells found - use first row from full case data
                param_row = case_params['full_case_data'].iloc[0]
        else:
            # No wells selected - use first row from full case data
            param_row = case_params['full_case_data'].iloc[0]
        
        # Now update case_params with parameters from the selected row
        case_params['qi'] = param_row['qi']
        case_params['di'] = param_row['di']
        case_params['b'] = param_row['b']
        case_params['qi_regressed'] = param_row.get('qi_regressed', param_row['qi'])
        case_params['ti_selected'] = param_row['ti_selected']
        case_params['eff_date'] = pd.to_datetime(param_row['eff_date']).date()
        case_params['well_name'] = param_row['well_name']
        case_params['field'] = param_row.get('field', None)
        
        # NEW: Load q_abandon and end_of_lease from database
        case_params['q_abandon'] = param_row.get('q_abandon', 10.0 if dca_time == 'daily' else 300.0)
        case_params['end_of_lease'] = param_row.get('end_of_lease', datetime.date(2039, 12, 31))
        if isinstance(case_params['end_of_lease'], str):
            case_params['end_of_lease'] = pd.to_datetime(case_params['end_of_lease']).date()
    
    # Apply zones filter
    if selected_zones and 'zone' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['zone'].isin(selected_zones)]
   
    if filtered_df.empty:
        st.warning("No data available with current filters.")
        return
   
    # For plotting purposes, create an aggregated version
    plot_df = filtered_df.groupby('date')['net'].sum().reset_index()
    plot_df.columns = ['date', 'net']
   
        # =================== DETERMINE SELECTION TYPE ===================
    if case_mode == "Load Existing Case" and case_params:
        # Use values from loaded case
        selection_type = case_params['selection_type']
        entity_identifier = case_params['entity_identifier']
        display_company = case_params['company_name']
        
        # ===== NEW: Update display based on selected wells =====
        if selected_wells:
            if len(selected_wells) == 1:
                # Single well selected - show that well's name
                display_well_name = selected_wells[0]
                display_entity = selected_wells[0]
            else:
                # Multiple wells selected - show count
                display_well_name = f"MultiWell_{len(selected_wells)}"
                display_entity = f"{len(selected_wells)} wells: " + ", ".join(selected_wells[:3]) + ("..." if len(selected_wells) > 3 else "")
        else:
            # No wells selected - use case defaults
            display_well_name = case_params.get('well_name', entity_identifier)
            display_entity = entity_identifier
    else:
        # Create New Case mode - determine from current selections
        selection_type = "company"
        entity_identifier = selected_company
        display_company = selected_company
        display_well_name = selected_company
        display_entity = selected_company
        
        if selected_wells and len(selected_wells) == 1:
            selection_type = "well"
            entity_identifier = selected_wells[0]
            display_well_name = selected_wells[0]
            display_entity = selected_wells[0]
        elif selected_wells and len(selected_wells) > 1:
            selection_type = "multi_well"
            entity_identifier = "|".join(sorted(selected_wells))
            display_well_name = f"MultiWell_{len(selected_wells)}"
            display_entity = f"{len(selected_wells)} wells combined"
        elif selected_fields and len(selected_fields) == 1:
            selection_type = "field"
            entity_identifier = selected_fields[0]
            display_well_name = f"Field_{selected_fields[0]}"
            display_entity = selected_fields[0]
        elif selected_fields and len(selected_fields) > 1:
            selection_type = "multi_field"
            entity_identifier = "|".join(sorted(selected_fields))
            display_well_name = f"MultiField_{len(selected_fields)}"
            display_entity = f"{len(selected_fields)} fields combined"

    # Display selection info
    if case_mode == "Load Existing Case" and case_params:
        st.info(f"**Case Label**: {case_params['case_label']} | **Selection Type**: {selection_type} | **Entity**: {display_entity} | **Wells Displayed**: {len(selected_wells)} | **Company**: {display_company}")
    else:
        st.info(f"**Selection Type**: {selection_type} | **Entity**: {display_entity} | **Company**: {display_company}")
   
    # =================== MAIN ANALYSIS SECTION ===================
    if case_mode == "Load Existing Case" and case_params and 'qi' in case_params:
        col_left, col_right = st.columns([2, 1])
       
        with col_left:
            st.subheader("📈 Historical Production Data")
            fig_original = PlotManager.create_production_scatter(
        plot_df,
        f"Historical Data: {display_well_name}",  # ===== CHANGED =====
        enable_selection=True,
        unit=unit_tag
    )
    
           
            st.info("💡 Optional: Use lasso tool to select data points for re-fitting ARPS parameters. Deselect to reset to database values.")
            event = st.plotly_chart(fig_original, use_container_width=True, key="existing_case_original_plot", on_select="rerun")
           
            # Initialize lasso parameters storage
            if 'lasso_params' not in st.session_state:
                st.session_state.lasso_params = {}
           
            # Handle lasso selection for parameter refitting
            lasso_updated = False
            selected_data = None
            if event and "points" in event.get("selection", {}):
                selected_points = event["selection"]["points"]
                if selected_points:
                    selected_data = pd.DataFrame({
                        "date": [pd.to_datetime(point["x"]).date() for point in selected_points],
                        "net": [point["y"] for point in selected_points],
                    })
                   
                    selected_data = selected_data.sort_values('date').reset_index(drop=True)
                    time_data = np.arange(len(selected_data))
                    rate_data = np.asarray(selected_data['net'].values, dtype=float)
                    best_qi_fitted, best_di_lasso, best_b_lasso = ARPSModel.fit_arps_parameters(time_data, rate_data)
                    manual_qi_override = float(rate_data[-1])
                   
                    st.warning(f"🎯 Lasso Selection Detected!")
                    st.write(f"**Suggested Qi (Forecast, based on last rate)**: {manual_qi_override:.1f} {unit_tag}")
                    st.write(f"**Suggested Qi Regressed (History Fit)**: {best_qi_fitted:.1f} {unit_tag}")
                    st.write(f"**Suggested Di**: {best_di_lasso:.4f}")
                    st.write(f"**Suggested b**: {best_b_lasso:.2f}")
                    st.info("💡 Parameters have been updated in the input fields below.")
                   
                    # Store aggregate lasso parameters
                    st.session_state.lasso_params['aggregate'] = {
                        'qi_forecast': manual_qi_override,
                        'qi_regressed': best_qi_fitted,
                        'di': best_di_lasso,
                        'b': best_b_lasso,
                        'eff_date': selected_data['date'].max()  # NEW: Suggest eff_date as last selected date
                    }
                    lasso_updated = True
                else:
                    # Clear lasso_params when selection is cleared
                    st.session_state.lasso_params = {}
                    st.info("💡 Lasso selection cleared. Parameters reset to database values.")
           
            st.subheader("🔧 ARPS Parameters")
            
            # Get parameters from case or lasso selection
            if 'aggregate' in st.session_state.lasso_params:
                default_params = st.session_state.lasso_params['aggregate']
            else:
                default_params = {
                    'qi_forecast': float(case_params['qi']),
                    'qi_regressed': float(case_params.get('qi_regressed', case_params['qi'])),
                    'di': float(case_params['di']),
                    'b': float(case_params['b']),
                    'eff_date': case_params['eff_date']
                }
           
            col_qi, col_di, col_b = st.columns(3)
           
            with col_qi:
                qi_forecast = st.number_input(
                    f"Forecast Initial Rate (qi, {unit_tag})",
                    value=default_params['qi_forecast'],
                    step=10.0,
                    key=f"existing_qi_forecast_agg"
                )
                qi_regressed = st.number_input(
                    f"History Fit qi ({unit_tag})",
                    value=default_params['qi_regressed'],
                    step=10.0,
                    key=f"existing_qi_regressed_agg"
                )
            with col_di:
                di = st.number_input(
                    f"Decline Rate (di),{unit_tag}",
                    value=default_params['di'],
                    step=0.0001,
                    format="%.4f",
                    key=f"existing_di_agg"
                )
            with col_b:
                b = st.number_input(
                    "Hyperbolic Factor (b)",
                    value=default_params['b'],
                    step=0.01,
                    format="%.2f",
                    key=f"existing_b_agg"
                )
            
            # NEW: Second row of parameters - History Start, Effective Date, Q Abandon, End of Lease
            col_ti, col_eff, col_q_aband, col_end_lease = st.columns(4)
            
            with col_ti:
                if lasso_updated and selected_data is not None:
                    default_ti_selected = selected_data['date'].min()
                else:
                    default_ti_selected = pd.to_datetime(case_params.get('ti_selected', case_params['eff_date'])).date()
               
                ti_selected = st.date_input(
                    "History Start Date",
                    value=default_ti_selected,
                    key=f'ti_selected_agg',
                    help="Start date for history regression"
                )
            
            with col_eff:
                if lasso_updated and 'eff_date' in default_params:
                    default_eff_date = default_params['eff_date']
                else:
                    default_eff_date = case_params['eff_date']
                
                eff_date_input = st.date_input(
                    "Effective Date (Forecast Start)",
                    value=default_eff_date,
                    key=f'existing_eff_date_agg',
                    help="Date when forecast begins"
                )
            
            with col_q_aband:
                q_abandon = st.number_input(
                    f"Abandonment Rate ({unit_tag})",
                    value=float(case_params.get('q_abandon', 10.0 if dca_time == 'daily' else 300.0)),
                    step=1.0 if dca_time == 'daily' else 10.0,
                    key=f'existing_q_abandon_agg',
                    help="Minimum economic rate"
                )
            
            with col_end_lease:
                end_of_lease = st.date_input(
                    "End of Lease",
                    value=case_params.get('end_of_lease', datetime.date(2039, 12, 31)),
                    key=f'existing_end_of_lease_agg',
                    help="Maximum forecast date"
                )
            
            # Create forecast profile using user-controlled eff_date
            forecast_start_date = pd.to_datetime(eff_date_input)
            forecast_freq = "D" if dca_time == "daily" else "MS"
           
            forecast_profile = ARPSModel.create_production_profile(
                start_date=forecast_start_date,
                end_date=pd.to_datetime(end_of_lease),
                qi=qi_forecast, di=di, b=b,
                q_abandon=q_abandon,
                frequency=forecast_freq
            )
            
            # Create history match profile
            if lasso_updated and selected_data is not None:
                history_start = pd.to_datetime(ti_selected)
                history_end = pd.to_datetime(selected_data['date'].max())  # ✅ From lasso
            
                history_profile = ARPSModel.create_production_profile(
                    start_date=history_start,
                    end_date=history_end,
                    qi=qi_regressed,
                    di=di,
                    b=b,
                    q_abandon=0,
                    frequency=forecast_freq
                )
            else:
                # No lasso selection - use original eff_date from database
                history_start = pd.to_datetime(ti_selected)
                # Use ORIGINAL eff_date from database, not user-modified one
                original_eff_date = pd.to_datetime(case_params['eff_date'])
                delta = pd.Timedelta(days=1) if dca_time == 'daily' else relativedelta(months=1)
                history_end = original_eff_date - delta  # ✅ Use database value
            
                history_profile = ARPSModel.create_production_profile(
                    start_date=history_start,
                    end_date=history_end,
                    qi=qi_regressed, 
                    di=di, 
                    b=b,
                    q_abandon=0,
                    frequency=forecast_freq
                )
           
            # Create combined plot
            st.subheader("🔮 Historical + ARPS Forecast")
           
            st.info("""
            **Plot explanation:**
            - 🟢 **Green dots**: Historical production data
            - 🔴 **Red dots**: ARPS history match using regressed qi
            - 🔵 **Blue solid line**: Future forecast using forecast qi
            """)
           
            if not forecast_profile.empty:
                rate_column = None
                possible_rate_columns = ['rate', 'production_rate', 'net', 'oil_rate', 'q']
                for col in possible_rate_columns:
                    if col in forecast_profile.columns:
                        rate_column = col
                        break
               
                if rate_column is None:
                    rate_column = forecast_profile.columns[1]
               
                forecast_plot = forecast_profile[[forecast_profile.columns[0], rate_column]].copy()
                forecast_plot.columns = ['date', 'rate']
               
                if not history_profile.empty:
                    history_plot = history_profile[[history_profile.columns[0], rate_column]].copy()
                    history_plot.columns = ['date', 'rate']
                else:
                    history_plot = None
               
                fig_combined = PlotManager.create_combined_plot(
        historical_df=plot_df,
        forecast_profile=forecast_plot,
        title=f"Updated View: {display_well_name}",  # ===== CHANGED =====
        unit=unit_tag,
        history_match_df=history_plot
    )
                st.plotly_chart(fig_combined, use_container_width=True, key="existing_case_combined_plot")
           
        
            # Update case parameters
            st.subheader("💾 Update Case Parameters")

            if st.button("🔄 UPDATE Case", type="primary", key="update_existing_case"):
                # ===== CHANGE: Handle different selection types correctly =====
                
                # Determine what to update based on original selection_type
                original_selection_type = case_params['selection_type']
                original_entity_identifier = case_params['entity_identifier']
                
                if original_selection_type in ["field", "multi_field", "company"]:
                    # For field/multi_field/company: Update the entire case as-is
                    # These are aggregate cases, not individual wells
                    success = DatabaseManager.update_forecast_case_aggregate(
                        case_label=case_params['case_label'],
                        selection_type=original_selection_type,
                        entity_identifier=original_entity_identifier,
                        eff_date=eff_date_input,
                        qi=qi_forecast,
                        di=di,
                        b=b,
                        dca_time=dca_time,
                        qi_regressed=qi_regressed,
                        ti_selected=ti_selected,
                        company_name=case_params['company_name'],
                        q_abandon=q_abandon,
                        end_of_lease=end_of_lease,
                        user_id = user_id
                    )
                    
                    if success:
                        st.success(f"✅ Case '{case_params['case_label']}' updated successfully!")
                        st.info(f"💡 Selection Type: {original_selection_type}")
                        st.info(f"💡 Entity: {original_entity_identifier}")
                    else:
                        st.error(f"❌ Failed to update case!")
                
                elif original_selection_type in ["well", "multi_well"]:
                    # For well/multi_well: Update the selected wells
                    if selected_wells:
                        update_success_count = 0
                        update_fail_count = 0
                        
                        for well_name in selected_wells:
                            # Find the database entry for this specific well
                            well_row = case_params['full_case_data'][
                                case_params['full_case_data']['well_name'] == well_name
                            ]
                            
                            if not well_row.empty:
                                # Get the original entity_identifier for this well
                                well_entity_id = well_row.iloc[0].get('entity_identifier', well_name)
                                well_selection_type = well_row.iloc[0].get('selection_type', 'well')
                                
                                success = DatabaseManager.update_forecast_case_aggregate(
                                    case_label=case_params['case_label'],
                                    selection_type=well_selection_type,
                                    entity_identifier=well_entity_id,
                                    eff_date=eff_date_input,
                                    qi=qi_forecast,
                                    di=di,
                                    b=b,
                                    dca_time=dca_time,
                                    qi_regressed=qi_regressed,
                                    ti_selected=ti_selected,
                                    company_name=case_params['company_name'],
                                    q_abandon=q_abandon,
                                    end_of_lease=end_of_lease
                                )
                                
                                if success:
                                    update_success_count += 1
                                else:
                                    update_fail_count += 1
                        
                        # Show results
                        if update_success_count > 0:
                            st.success(f"✅ Updated {update_success_count} well(s) successfully!")
                            if update_fail_count > 0:
                                st.warning(f"⚠️ Failed to update {update_fail_count} well(s)")
                            st.info(f"💡 Updated wells: {', '.join(selected_wells)}")
                        else:
                            st.error(f"❌ Failed to update all {update_fail_count} well(s)!")
                    else:
                        st.warning("⚠️ Please select at least one well to update")
                
                else:
                    # Unknown selection type - use original values
                    st.warning(f"⚠️ Unknown selection type: {original_selection_type}")
                    success = DatabaseManager.update_forecast_case_aggregate(
                        case_label=case_params['case_label'],
                        selection_type=original_selection_type,
                        entity_identifier=original_entity_identifier,
                        eff_date=eff_date_input,
                        qi=qi_forecast,
                        di=di,
                        b=b,
                        dca_time=dca_time,
                        qi_regressed=qi_regressed,
                        ti_selected=ti_selected,
                        company_name=case_params['company_name'],
                        q_abandon=q_abandon,
                        end_of_lease=end_of_lease
                    )
                    
                    if success:
                        st.success(f"✅ Case updated successfully!")
                    else:
                        st.error(f"❌ Failed to update case!")
                
                # Show common update info
                st.info(f"💡 Forecast now starts from: {eff_date_input}")
                st.info(f"💡 Abandonment rate: {q_abandon} {unit_tag}")
                st.info(f"💡 End of lease: {end_of_lease}")
       
        with col_right:
    
            st.subheader("📋 Case Summary")
            st.metric("Case Label", case_params['case_label'])
            st.metric("Current Well/Entity", display_well_name)
            st.metric("Selection Type", selection_type)
            
            # Show details based on selection type
            with st.expander("View Case Details"):
                st.write(f"**Currently Viewing**: {display_entity}")
                
                if selection_type in ["well", "multi_well"]:
                    case_wells = case_params['full_case_data']['well_name'].unique().tolist()
                    st.write(f"**Total wells in case**: {len(case_wells)}")
                    st.write(f"**Currently selected**: {len(selected_wells)}")
                    
                    # Show selected wells
                    if selected_wells:
                        st.write("**Selected wells:**")
                        for well in selected_wells:
                            st.write(f"  ✓ {well}")
                    
                    # Show other wells with a checkbox toggle
                    other_wells = [w for w in case_wells if w not in selected_wells]
                    if other_wells:
                        show_other = st.checkbox(
                            f"Show other wells in case ({len(other_wells)})", 
                            key="show_other_wells"
                        )
                        if show_other:
                            for well in other_wells:
                                st.write(f"  • {well}")
                                
                elif selection_type in ["field", "multi_field"]:
                    fields_in_entity = entity_identifier.split("|") if "|" in entity_identifier else [entity_identifier]
                    st.write(f"**Fields in case**: {len(fields_in_entity)}")
                    for field in fields_in_entity:
                        st.write(f"- {field}")
                else:
                    st.write(f"**Company-level case**: {entity_identifier}") 
            # Calculate EUR
            if not forecast_profile.empty:
                st.subheader("📊 EUR Summary")
               
                historical_cutoff = forecast_start_date.date()
                cutoff_timestamp = pd.Timestamp(historical_cutoff)
                historical_cum = filtered_df[filtered_df['date'] < cutoff_timestamp]['net'].sum()
                forecast_eur = ARPSModel.calculate_eur(forecast_profile, 0.0)
                total_eur = ARPSModel.calculate_eur(forecast_profile, historical_cum)
               
                st.metric("Historical Production", f"{historical_cum/1_000:.3f} Mstb")
                st.metric("Forecast EUR", f"{forecast_eur/1_000:.3f} Mstb")
                st.metric("**Total EUR**", f"{total_eur/1_000:.3f} Mstb")
               
                st.subheader("📋 Data Details")
                with st.expander("View Filtered Data"):
                    st.dataframe(filtered_df, use_container_width=True)
   
    else:
        # NEW CASE MODE with Enhanced Plotting
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.subheader("🎯 Production Data - Make Lasso Selection")
            
            if selection_type == "well":
                title = f"Production: {entity_identifier}"
            elif selection_type == "multi_well":
                title = f"Production: {len(selected_wells)} Wells Combined"
            elif selection_type == "field":
                title = f"Production: Field {entity_identifier}"
            elif selection_type == "multi_field":
                title = f"Production: {len(selected_fields)} Fields Combined"
            else:
                title = f"Production: {display_company} (All Data)"
           
            fig = PlotManager.create_production_scatter(plot_df, title, enable_selection=True, unit=unit_tag)
           
            event = st.plotly_chart(fig, use_container_width=True, key="new_case_prod_plot", on_select="rerun")
           
            selected_data = None
            if event and "points" in event.get("selection", {}):
                selected_points = event["selection"]["points"]
                selected_data = pd.DataFrame({
                    "date": [pd.to_datetime(point["x"]).date() for point in selected_points],
                    "net": [point["y"] for point in selected_points],
                })
        
        if selected_data is not None and not selected_data.empty:
            try:
                selected_data = selected_data.sort_values('date').reset_index(drop=True)
                first_selected_date = selected_data['date'].iloc[0]
               
                time_data = np.arange(len(selected_data))
                rate_data = np.asarray(selected_data['net'].values, dtype=float)
               
                # Get FITTED parameters from optimization
                best_qi_fitted, best_di, best_b = ARPSModel.fit_arps_parameters(time_data, rate_data)
               
                # Get MANUAL qi (last historical rate for forecast continuity)
                manual_qi = float(rate_data[-1])
               
            except Exception as e:
                st.error(f"Error in ARPS analysis: {e}")
                return
           
            with col_left:
                st.subheader("🔧 ARPS Parameters")
               
                # Show both fitted and manual qi values
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.info(f"**Fitted qi (from optimization)**: {best_qi_fitted:.1f} {unit_tag}")
                    st.info(f"**di (decline rate)**: {best_di:.4f},{unit_tag}")
                    st.info(f"**b (hyperbolic factor)**: {best_b:.2f}")
               
                with col_info2:
                    st.warning(f"**Manual qi (last historical rate)**: {manual_qi:.1f} {unit_tag}")
                    st.write("This will be used for forecast continuity")
               
                # Parameter adjustments - First Row
                st.markdown("**Parameter Adjustments**")
               
                col1, col2, col3, col4 = st.columns(4)
               
                with col1:
                    qi = st.number_input(
                        "Forecast qi",
                        value=manual_qi,
                        step=10.0,
                        key="new_qi",
                        help=f"Starting from last historical production ({unit_tag})"
                    )
               
                with col2:
                    qi_hist = st.number_input(
                        "History qi",
                        value=best_qi_fitted,
                        step=10.0,
                        key="history_qi",
                        help=f"Best fit qi for the history ({unit_tag})"
                    )
               
                with col3:
                    di = st.number_input(
                        f"Decline Rate,{unit_tag}",
                        value=float(best_di),
                        step=0.0001,
                        format="%.4f",
                        key="new_di",
                        help=f"Decline Rate (di),{unit_tag}"
                    )
               
                with col4:
                    b = st.number_input(
                        "Hyperbolic b",
                        value=float(best_b),
                        step=0.01,
                        format="%.2f",
                        key="new_b",
                        help="Hyperbolic Factor (b)"
                    )
               
                # Parameter adjustments - Second Row (NEW)
                col5, col6, col7, col8 = st.columns(4)
               
                with col5:
                    first_date = st.date_input(
                        "History Start Date",
                        value=first_selected_date,
                        key='new_first_date',
                        help="Start date for history regression"
                    )
               
                with col6:
                    # NEW: User can control effective date
                    last_selected_date = selected_data['date'].iloc[-1]
                    default_eff_date = last_selected_date + relativedelta(days=1) if dca_time == "daily" else last_selected_date + relativedelta(months=1)
                    
                    eff_date_new = st.date_input(
                        "Effective Date (Forecast Start)",
                        value=default_eff_date,
                        key='new_eff_date',
                        help="Date when forecast begins"
                    )
               
                with col7:
                    # NEW: Abandonment rate
                    default_q_abandon = 10.0 if dca_time == 'daily' else 300.0
                    q_abandon_new = st.number_input(
                        f"Abandonment Rate ({unit_tag})",
                        value=default_q_abandon,
                        step=1.0 if dca_time == 'daily' else 10.0,
                        key='new_q_abandon',
                        help="Minimum economic rate"
                    )
               
                with col8:
                    # NEW: End of lease
                    end_of_lease_new = st.date_input(
                        "End of Lease",
                        value=datetime.date(2039, 12, 31),
                        key='new_end_of_lease',
                        help="Maximum forecast date"
                    )
               
                # Generate forecast profile using user-controlled dates
                forecast_start_date = pd.to_datetime(eff_date_new)
                forecast_freq = "D" if dca_time == "daily" else "MS"
               
                forecast_profile = ARPSModel.create_production_profile(
                    start_date=forecast_start_date,
                    end_date=pd.to_datetime(end_of_lease_new),
                    qi=qi, di=di, b=b,
                    q_abandon=q_abandon_new,
                    frequency=forecast_freq
                )
               
                # Create history match profile for new case
                history_start = pd.to_datetime(first_date)
                # History ALWAYS ends at last selected lasso date, independent of eff_date
                last_selected_date = selected_data['date'].iloc[-1]
                history_end = pd.to_datetime(last_selected_date)  # ✅ Fixed to lasso

                history_profile = ARPSModel.create_production_profile(
                    start_date=history_start,
                    end_date=history_end,
                    qi=qi_hist, 
                    di=di, 
                    b=b,
                    q_abandon=0,
                    frequency=forecast_freq
)
               
                # Create combined plot for new case
                st.subheader("📈 Historical + History Match + Forecast")
               
                st.info("""
                **Plot explanation:**
                - 🟢 **Green dots**: Historical production data
                - 🔷 **Blue diamonds**: Selected points used for regression
                - 🔴 **Red dots**: ARPS history match using fitted qi
                - 🔵 **Blue solid line**: Future forecast using adjusted qi
                """)
                
                # Calculate and display regression quality metrics
                st.subheader("📊 Regression Quality")
               
                # Generate history match data for comparison
                time_regression = np.arange(len(selected_data))
                if b == 0:
                    predicted_rates = qi_hist * np.exp(-di * time_regression)
                else:
                    predicted_rates = qi_hist / ((1 + b * di * time_regression) ** (1 / b))
               
                # Calculate R-squared
                ss_res = np.sum((rate_data - predicted_rates) ** 2)
                ss_tot = np.sum((rate_data - np.mean(rate_data)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
               
                # Calculate RMSE
                rmse = np.sqrt(np.mean((rate_data - predicted_rates) ** 2))
               
                col_r2, col_rmse, col_points = st.columns(3)
                with col_r2:
                    st.metric("R² (History Match)", f"{r_squared:.3f}")
                with col_rmse:
                    st.metric(f"RMSE ({unit_tag})", f"{rmse:.1f}")
                with col_points:
                    st.metric("Selected Points", len(selected_data))
               
                # Show data quality assessment
                if r_squared >= 0.8:
                    st.success("✅ Excellent history match quality!")
                elif r_squared >= 0.6:
                    st.warning("⚠️ Good history match - consider selecting more representative points")
                else:
                    st.error("❌ Poor history match - try selecting different data points")
               
                # Create combined plot with history match
                fig_enhanced = PlotManager.create_combined_plot(
                    historical_df=plot_df,
                    forecast_profile=forecast_profile,
                    title=f"{title} + ARPS Analysis",
                    unit=unit_tag,
                    history_match_df=history_profile
                )
                st.plotly_chart(fig_enhanced, use_container_width=True, key="new_case_combined_plot")
           
            # Calculate EUR
            eff_date_timestamp = pd.Timestamp(eff_date_new)
            historical_cum = filtered_df[filtered_df['date'] < eff_date_timestamp]['net'].sum()
           
            total_eur = ARPSModel.calculate_eur(forecast_profile, historical_cum)
            forecast_eur = ARPSModel.calculate_eur(forecast_profile, 0.0)
            selected_cum = selected_data['net'].sum()
           
            with col_right:
                st.subheader("📋 Analysis Results")
                st.metric(f"Initial Rate (qi)", f"{qi:.1f} {unit_tag}")
                st.metric(f"Decline Rate (di)", f"{di:.4f},{unit_tag}")
                st.metric(f"Hyperbolic Factor (b)", f"{b:.2f}")
                st.metric("Effective Date", f"{eff_date_new}")
                st.metric(f"Abandonment Rate", f"{q_abandon_new} {unit_tag}")
               
                st.subheader("📊 EUR Breakdown")
                st.metric("Total Historical Production", f"{historical_cum/1_000:.3f} Mstb")
                st.metric("Forecast EUR", f"{forecast_eur/1_000:.3f} Mstb")
                st.metric("**Total EUR**", f"{total_eur/1_000:.3f} Mstb")
               
                with st.expander("🔍 Lasso Selection Details"):
                    st.write(f"**Selected Points**: {len(selected_data)} data points")
                    st.write(f"**Selected Date Range**: {selected_data['date'].min()} to {selected_data['date'].max()}")
                    st.write(f"**Selected Area Production**: {selected_cum/1_000:.3f} Mstb")
                    st.write(f"**Manual Qi (last rate)**: {manual_qi:.1f} {unit_tag}")
                    st.write(f"**Forecast runs until**: {end_of_lease_new}")
               
                st.subheader("💾 Save New Case")
                
                # Determine well name based on selection type
                if selection_type == "well":
                    save_well_name = entity_identifier
                elif selection_type == "multi_well":
                    save_well_name = f"MultiWell_{len(selected_wells)}"
                elif selection_type == "field":
                    save_well_name = f"Field_{entity_identifier}"
                elif selection_type == "multi_field":
                    save_well_name = f"MultiField_{len(selected_fields)}"
                else:
                    save_well_name = f"Company_{display_company}"
               
                save_col1, save_col2 = st.columns(2)
                with save_col1:
                    well_name = st.text_input("Case Name", value=save_well_name, key="save_well_name_input_new")
                with save_col2:
                    case_label = st.text_input("Case Label", value=save_well_name, key="save_case_label_input_new")
               
                if st.button("💾 Save to Database", type="primary", key="save_new_case"):
                    # Determine field for saving
                    selected_field = None
                    if selection_type == "field":
                        selected_field = entity_identifier
                    elif selected_fields and len(selected_fields) == 1:
                        selected_field = selected_fields[0]
                    elif selected_fields and len(selected_fields) > 1:
                        selected_field = "|".join(sorted(selected_fields))
                   
                    final_case_label = case_label
                    if "existing" not in final_case_label.lower():
                        final_case_label = f"Existing_{final_case_label}"
                   
                    success = DatabaseManager.save_forecast_case_aggregate(
                        well_name=well_name,
                        case_label=final_case_label,
                        selection_type=selection_type,
                        entity_identifier=entity_identifier,
                        eff_date=eff_date_new,  # NEW: User-controlled
                        qi=qi,
                        di=di,
                        b=b,
                        qi_regressed=qi_hist,
                        ti_selected=pd.to_datetime(first_date).date(),
                        well_type="existing",
                        field=selected_field,
                        dca_time=dca_time,
                        company_name=display_company,
                        q_abandon=q_abandon_new,  # NEW
                        end_of_lease=end_of_lease_new,
                          user_id = user_id  # NEW
                    )
                    if success:
                        st.success("✅ Case saved successfully!")
                        st.info(f"💡 Forecast starts from: {eff_date_new}")
                        st.info(f"💡 Selection Type: {selection_type}")
                        st.info(f"💡 Entity Identifier: {entity_identifier}")
                        st.info(f"💡 Abandonment rate: {q_abandon_new} {unit_tag}")
                        st.info(f"💡 End of lease: {end_of_lease_new}")
                    else:
                        st.error("❌ Failed to save case.")

def render_new_wells_forecasting():
    """Render new wells forecasting interface with daily profiles"""
    st.header("🔮 New Wells Development Forecasting")
    unique_fields = DatabaseManager.load_unique_fields()["field"].tolist()
   
    # Load existing forecast cases
    cases_df = DatabaseManager.load_forecast_cases()
   
    # Add new cases section
    st.subheader("➕ Add New Development Cases")
   
    with st.expander("Add Multiple Cases"):
        n_rows = st.number_input("Number of rows", min_value=1, max_value=20, value=5, key="new_wells_rows")
       
        template = pd.DataFrame({
            "well_name": [None] * n_rows,
            "case_label": [None] * n_rows,
            "field": [None] * n_rows,
            "eff_date": [None] * n_rows,
            "qi": [None] * n_rows,
            "di": [None] * n_rows,
            "b": [None] * n_rows,
            "q_abandon": [10.0] * n_rows,  # NEW
            "end_of_lease": [datetime.date(2039, 12, 31)] * n_rows,  # NEW
            "dca_time": ["daily"] * n_rows
        })
       
        edited = st.data_editor(
            template,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key="new_wells_data_editor",
            column_config={
                "well_name": st.column_config.TextColumn("Well Name", required=True),
                "case_label": st.column_config.TextColumn("Case Label", required=True),
                "field": st.column_config.SelectboxColumn(
                    "Field",
                    options=unique_fields,
                    required=True
                ),
                "eff_date": st.column_config.DateColumn("Start Date", required=True),
                "qi": st.column_config.NumberColumn("Initial Rate (bbl/day)", min_value=0.0, required=True),
                "di": st.column_config.NumberColumn(f"Decline Rate (di)", min_value=0.0, format="%.6f", required=True),
                "b": st.column_config.NumberColumn("Hyperbolic Factor (b)", min_value=0.0, required=True),
                "q_abandon": st.column_config.NumberColumn("Abandonment Rate (bbl/day)", min_value=0.0, required=True),  # NEW
                "end_of_lease": st.column_config.DateColumn("End of Lease", required=True),  # NEW
                "dca_time": st.column_config.TextColumn("Resolution", disabled=True, default="daily")
            }
        )
       
        if st.button("💾 Save New Cases", key="save_new_wells_cases"):
            saved_count = 0
            for _, row in edited.iterrows():
                if all(pd.notna([row['well_name'], row['case_label'], row['eff_date'], row['qi'], 
                                row['di'], row['b'], row['dca_time'], row['q_abandon'], row['end_of_lease']])):
                    case_label = row['case_label']
                    if not case_label.lower().startswith("new_"):
                        case_label = f"new_{case_label}"
                    
                    # New wells are always single well type
                    success = DatabaseManager.save_forecast_case_aggregate(
                        well_name=row['well_name'],
                        case_label=case_label,
                        selection_type="well",
                        entity_identifier=row['well_name'],
                        eff_date=row['eff_date'],
                        qi=row['qi'],
                        di=row['di'],
                        b=row['b'],
                        qi_regressed=row['qi'],
                        ti_selected=row['eff_date'],
                        well_type="new",
                        field=row['field'],
                        dca_time=row['dca_time'],
                        company_name="Alamein",
                        q_abandon=row['q_abandon'],  # NEW
                        end_of_lease=row['end_of_lease']  # NEW
                    )
                    if success:
                        saved_count += 1
                    else:
                        st.warning(f"Failed to save case: {case_label}")
           
            if saved_count > 0:
                st.success(f"✅ Saved {saved_count} new wells!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ No cases saved. Please ensure all required fields are filled.")
   
    # Forecast visualization section
    st.subheader("📊 Forecast Visualization")
   
    if not cases_df.empty:
        col1, col2 = st.columns(2)
       
        with col1:
            selected_cases = st.multiselect(
                "Select Cases to Plot",
                cases_df[cases_df['well_type'] == "new"]["case_label"].unique(),
                key="new_wells_selected_cases"
            )
       
        with col2:
            end_date = st.date_input(
                "Forecast End Date",
                value=Config.DEFAULT_FORECAST_END_DATE,
                key="new_wells_end_date"
            )
            q_abandon = st.number_input(
                "Abandonment Rate (bbl/day)",
                min_value=0.0,
                value=Config.DEFAULT_ABANDONMENT_RATE_DAILY,
                key="new_wells_q_abandon"
            )
       
        if st.button("📈 Generate Forecast", key="new_wells_generate_forecast") and selected_cases:
            all_profiles = []
            eur_summary = []
           
            for case_label in selected_cases:
                case_data = cases_df[cases_df["case_label"] == case_label]
                if case_data.empty:
                    st.warning(f"No data found for case: {case_label}")
                    continue
               
                case_profiles = []
                for _, row in case_data.iterrows():
                    if any(pd.isna([row['eff_date'], row['qi'], row['di'], row['b']])):
                        st.warning(f"Invalid data for case {case_label}, well {row['well_name']}. Skipping.")
                        continue
                   
                    dca_time = row.get("dca_time", "daily") or "daily"
                    if dca_time != "daily":
                        st.warning(f"Unexpected dca_time '{dca_time}' for case {case_label}. Forcing to daily.")
                        dca_time = "daily"
                   
                    # Get q_abandon and end_of_lease from row or use defaults
                    row_q_abandon = row.get('q_abandon', q_abandon)
                    if pd.isna(row_q_abandon):
                        row_q_abandon = q_abandon
                    
                    row_end_of_lease = row.get('end_of_lease', end_date)
                    if pd.isna(row_end_of_lease):
                        row_end_of_lease = end_date
                   
                    try:
                        profile = ARPSModel.create_production_profile(
                            start_date=pd.to_datetime(row["eff_date"]),
                            end_date=pd.to_datetime(row_end_of_lease),
                            qi=float(row["qi"]),
                            di=float(row["di"]),
                            b=float(row["b"]),
                            q_abandon=float(row_q_abandon),
                            frequency="D"
                        )
                    except Exception as e:
                        st.error(f"Error generating profile for case {case_label}, well {row['well_name']}: {e}")
                        continue
                   
                    if not profile.empty:
                        profile["case_label"] = case_label
                        profile["well_name"] = row["well_name"]
                        profile["dca_time"] = dca_time
                        case_profiles.append(profile)
                       
                        eur = ARPSModel.calculate_eur(profile)
                        eur_summary.append({
                            "Case": case_label,
                            "Well": row["well_name"],
                            "EUR (MMstb)": round(eur / 1_000, 3),
                            "Start Date": row["eff_date"],
                            "Resolution": dca_time.capitalize()
                        })
                    else:
                        st.warning(f"Empty profile generated for case {case_label}, well {row['well_name']}")
               
                if case_profiles:
                    combined = pd.concat(case_profiles)
                    aggregated = combined.groupby("date", as_index=False)["rate"].sum()
                    aggregated["case_label"] = case_label
                    aggregated["cumulative"] = aggregated["rate"].cumsum()
                    aggregated["dca_time"] = "daily"
                    all_profiles.append(aggregated)
           
            if not all_profiles:
                st.error("❌ No valid profiles generated. Please check your case data.")
                return
           
            # Display EUR summary
            col1, col2 = st.columns(2)
           
            with col1:
                st.subheader("📊 EUR Summary")
                eur_df = pd.DataFrame(eur_summary)
                if not eur_df.empty:
                    styled_eur = (
                        eur_df.style
                        .format({"EUR (MMstb)": "{:.2f}"})
                        .background_gradient(
                            cmap='Oranges',
                            subset=['EUR (MMstb)'],
                            low=0.1,
                            high=0.8
                        )
                        .set_table_styles([
                            {'selector': 'thead th', 'props': [
                                ('background-color', '#ff8c00'),
                                ('color', 'white'),
                                ('font-weight', 'bold'),
                                ('text-align', 'center'),
                                ('font-size', '14px')
                            ]},
                            {'selector': 'tbody td', 'props': [
                                ('text-align', 'center'),
                                ('padding', '8px'),
                                ('border', '1px solid #ddd')
                            ]},
                            {'selector': 'table', 'props': [
                                ('border-collapse', 'collapse'),
                                ('margin', '0 auto'),
                                ('width', '100%')
                            ]}
                        ])
                    )
                    st.write(styled_eur.to_html(), unsafe_allow_html=True)
           
            with col2:
                st.subheader("📈 Total EUR by Case")
                if not eur_df.empty:
                    total_eur = eur_df.groupby("Case")["EUR (MMstb)"].sum().reset_index()
                    styled_total = (
                        total_eur.style
                        .format({"EUR (MMstb)": "{:.2f}"})
                        .background_gradient(cmap='Oranges', subset=['EUR (MMstb)'], low=0.2, high=0.9)
                        .set_table_styles([
                            {'selector': 'thead th', 'props': [
                                ('background-color', '#ff6600'),
                                ('color', 'white'),
                                ('font-weight', 'bold'),
                                ('text-align', 'center')
                            ]}
                        ])
                    )
                    st.write(styled_total.to_html(), unsafe_allow_html=True)
           
            # Create plots
            combined_df = pd.concat(all_profiles)
           
            fig1 = go.Figure()
            colors = px.colors.qualitative.Set1
           
            for i, case in enumerate(selected_cases):
                case_data = combined_df[combined_df["case_label"] == case]
                if case_data.empty:
                    continue
                fig1.add_trace(go.Scatter(
                    x=case_data["date"],
                    y=case_data["rate"],
                    mode="lines",
                    name=case,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
           
            fig1.update_layout(
                title="Daily Production Forecast",
                xaxis_title="Date",
                yaxis_title="Rate (bbl/day)",
                hovermode="x unified",
                plot_bgcolor="white",
                height=500
            )
           
            fig2 = go.Figure()
           
            for i, case in enumerate(selected_cases):
                case_data = combined_df[combined_df["case_label"] == case]
                if case_data.empty:
                    continue
                fig2.add_trace(go.Scatter(
                    x=case_data["date"],
                    y=case_data["cumulative"],
                    mode="lines",
                    name=case,
                    line=dict(color=colors[i % len(colors)], width=2)
                ))
           
            fig2.update_layout(
                title="Cumulative Production Forecast",
                xaxis_title="Date",
                yaxis_title="Cumulative Volume (bbl)",
                hovermode="x unified",
                plot_bgcolor="white",
                height=500
            )
           
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(fig1, use_container_width=True)
            with col2:
                st.plotly_chart(fig2, use_container_width=True)
   
    # Show existing cases
    with st.expander("📋 View Existing Cases"):
        if not cases_df.empty:
            st.dataframe(cases_df[cases_df['well_type'] == "new"], use_container_width=True)
        else:
            st.info("No existing new well cases available.")

def render_scenario_comparison():
    """Render comprehensive scenario comparison dashboard"""
    st.header("📈 Production Scenario Comparison Dashboard")
    st.info("Compare different development scenarios with sophisticated filtering and combination logic.")
   
    cases_df = DatabaseManager.load_forecast_cases()
   
    if cases_df.empty:
        st.warning("No forecast cases available. Please add some cases first.")
        return
   
    st.subheader("🔍 Dashboard Filters")
   
    existing_cases = cases_df[cases_df['case_label'].str.contains('existing', case=False, na=False)]
    new_cases = cases_df[cases_df['case_label'].str.contains('new_', case=False, na=False)]
   
    col1, col2, col3, col4 = st.columns(4)
   
    with col1:
        st.write("**Existing Wells Cases**")
        selected_existing_cases = st.multiselect(
            "Select Existing Cases",
            existing_cases['case_label'].unique() if not existing_cases.empty else [],
            key="dashboard_existing_cases"
        )
       
        st.write("**New Wells Cases**")
        selected_new_cases = st.multiselect(
            "Select New Cases",
            new_cases['case_label'].unique() if not new_cases.empty else [],
            key="dashboard_new_cases"
        )
   
    available_wells = []
    available_fields = []
   
    selected_cases_df = pd.DataFrame()
    if selected_existing_cases or selected_new_cases:
        all_selected_cases = selected_existing_cases + selected_new_cases
        selected_cases_df = cases_df[cases_df['case_label'].isin(all_selected_cases)]
        available_wells = selected_cases_df['well_name'].unique().tolist()
        available_fields = selected_cases_df['field'].dropna().unique().tolist()
   
    with col2:
        selected_wells = st.multiselect(
            "Select Wells (from selected cases)",
            available_wells,
            key="dashboard_wells"
        )
   
    with col3:
        selected_fields = st.multiselect(
            "Select Fields (from selected cases)",
            available_fields,
            key="dashboard_fields"
        )
   
   
       
        resolution = st.radio(
        "Plot Resolution",
        options=["Monthly", "Daily"],
        index=0,
        key="dashboard_plot_resolution"
    )
        unit_tag = "bbl/month" if resolution == "Monthly" else "bbl/day"
        
        # NEW: Combination mode selection
        st.markdown("---")
        combination_mode = st.radio(
            "New Cases Combination Mode",
            options=["Individual", "Combined"],
            index=0,
            key="dashboard_combination_mode",
            help="Individual: Compare each new case separately with existing\nCombined: Merge all new cases into one profile"
        )
   
    if not selected_cases_df.empty:
        if selected_wells:
            selected_cases_df = selected_cases_df[selected_cases_df['well_name'].isin(selected_wells)]
        if selected_fields:
            selected_cases_df = selected_cases_df[selected_cases_df['field'].isin(selected_fields)]
   
    # Initialize state
    if "comparison_active" not in st.session_state:
        st.session_state.comparison_active = False
    
    def _activate_comparison():
        st.session_state.comparison_active = True
    
    # The button (uses callback)
    if not selected_cases_df.empty:
        st.button(
            "🔄 Generate Comparison",
            key="dashboard_generate",
            on_click=_activate_comparison,
            use_container_width=True
        )
    
    # Auto-generate while active
    if st.session_state.comparison_active and not selected_cases_df.empty:
        with st.spinner("Generating comparison..."):
            generate_scenario_comparison(
                selected_cases_df,
                selected_existing_cases,
                selected_new_cases,
                resolution,
                combination_mode
            )
    
    # Stop/reset button
    if st.session_state.comparison_active:
        if st.button("⏹ Stop Comparison", key="dashboard_stop", use_container_width=True):
            st.session_state.comparison_active = False

def combine_case_profiles(profile1: pd.DataFrame, profile2: pd.DataFrame, combined_name: str) -> pd.DataFrame:
    """Combine two FULL case profiles (already aggregated) by summing their rates"""
   
    # Merge the two profiles by date
    combined = pd.merge(
        profile1[['date', 'rate']],
        profile2[['date', 'rate']],
        on='date', how='outer', suffixes=('_existing', '_new')
    )
   
    # Fill NaN values with 0 and sum the rates
    combined['rate_existing'] = pd.to_numeric(combined['rate_existing'], errors="coerce").fillna(0)
    combined['rate_new'] = pd.to_numeric(combined['rate_new'], errors="coerce").fillna(0)
    combined['rate'] = combined['rate_existing'] + combined['rate_new']
   
    # Create final combined profile
    result = combined[['date', 'rate']].sort_values('date')
    result['cumulative'] = result['rate'].cumsum()
    result['case_label'] = combined_name
    result['dca_time'] = 'monthly'
    result['well_name'] = f"{profile1['well_name'].iloc[0]} + {profile2['well_name'].iloc[0]}"
   
    return result

def convert_to_monthly_totals(profile: pd.DataFrame) -> pd.DataFrame:
    """Convert daily profile to monthly totals by summing all daily values in each month"""
    if profile.empty:
        return profile
   
    # Ensure date column is datetime
    profile = profile.copy()
    profile['date'] = pd.to_datetime(profile['date'])
   
    # Create month-year grouping
    profile['year_month'] = profile['date'].dt.to_period('M')
   
    # Group by month and sum the rates
    monthly_profile = profile.groupby('year_month', as_index=False).agg({
        'rate': 'sum',
        'case_label': 'first',
        'well_name': 'first',
        'dca_time': 'first'
    })
   
    # Convert period back to datetime
    monthly_profile['date'] = monthly_profile['year_month'].dt.start_time
    monthly_profile = monthly_profile.drop(columns=['year_month'])
   
    # Recalculate cumulative
    monthly_profile = monthly_profile.sort_values('date')
    monthly_profile['cumulative'] = monthly_profile['rate'].cumsum()
    monthly_profile['dca_time'] = 'monthly'
   
    return monthly_profile

def create_export_data(all_profiles: List[pd.DataFrame], all_well_profiles_dict: Dict[str, List[pd.DataFrame]]) -> Dict[str, pd.DataFrame]:
    """Create export data for all cases - both case summaries and well pivots"""
    export_data = {}
   
    # Process each case
    for profile in all_profiles:
        case_label = profile['case_label'].iloc[0] if not profile.empty else "Unknown"
       
        # Case Summary CSV
        case_summary = profile[['date', 'rate', 'cumulative']].copy()
        case_summary['date'] = pd.to_datetime(case_summary['date'])
        case_summary = case_summary.sort_values('date')
        case_summary = case_summary.rename(columns={
            'rate': f'{case_label}_rate',
            'cumulative': f'{case_label}_cumulative'
        })
        export_data[f"{case_label}_case_summary"] = case_summary
       
        # Wells Pivot CSV
        if case_label in all_well_profiles_dict:
            well_profiles = all_well_profiles_dict[case_label]
            if well_profiles:
                all_wells_df = pd.concat(well_profiles, ignore_index=True)
                all_wells_df['date'] = pd.to_datetime(all_wells_df['date'])
               
                wells_pivot = all_wells_df.pivot_table(
                    index='date',
                    columns='well_name',
                    values='rate',
                    aggfunc='sum',
                    fill_value=0
                ).reset_index()
               
                wells_pivot.columns.name = None
                export_data[f"{case_label}_wells_pivot"] = wells_pivot
   
    return export_data

def create_download_zip(export_data: Dict[str, pd.DataFrame], resolution: str) -> bytes:
    """Create a ZIP file containing all CSV files"""
    zip_buffer = io.BytesIO()
   
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, df in export_data.items():
            if df.empty:
                continue
               
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
           
            csv_filename = f"{filename}_{resolution.lower()}.csv"
            zip_file.writestr(csv_filename, csv_content)
   
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def generate_scenario_comparison(cases_df: pd.DataFrame, existing_cases: list, new_cases: list,
                                  resolution: str, combination_mode: str):  # ADD combination_mode
    """Generate sophisticated scenario comparison with proper case-level combination logic"""
    st.subheader("📊 Scenario Analysis Results")
   
    existing_df = cases_df[cases_df['case_label'].isin(existing_cases)] if existing_cases else pd.DataFrame()
    new_df = cases_df[cases_df['case_label'].isin(new_cases)] if new_cases else pd.DataFrame()
   
    all_profiles = []
    eur_summary = []
    all_well_profiles_dict = {}
   
    # CASE 1: Only existing cases selected
    if not existing_df.empty and new_df.empty:
        st.info("📊 Showing existing cases separately (with historical + forecast)")
        for case_label in existing_cases:
            case_data = existing_df[existing_df["case_label"] == case_label]
           
            profile, eur, well_profiles = generate_full_case_profile_with_wells(
                case_data, case_label
            )
           
            if profile is not None and not profile.empty:
                if resolution == "Monthly":
                    profile = convert_to_monthly_totals(profile)
                    well_profiles = [convert_to_monthly_totals(wp) for wp in well_profiles if not wp.empty]
                all_profiles.append(profile)
                all_well_profiles_dict[case_label] = well_profiles
            eur_summary.extend(eur)

    # CASE 2: Only new cases selected
    elif existing_df.empty and not new_df.empty:
        st.info("📊 Showing new cases separately (forecast only)")
        for case_label in new_cases:
            case_data = new_df[new_df["case_label"] == case_label]
           
            profile, eur, well_profiles = generate_full_case_profile_with_wells(
                case_data, case_label
            )
           
            if profile is not None and not profile.empty:
                if resolution == "Monthly":
                    profile = convert_to_monthly_totals(profile)
                    well_profiles = [convert_to_monthly_totals(wp) for wp in well_profiles if not wp.empty]
                all_profiles.append(profile)
                all_well_profiles_dict[case_label] = well_profiles
            eur_summary.extend(eur)
   
    # CASE 3: Both existing and new cases selected - CREATE COMBINATIONS
        
    elif not existing_df.empty and not new_df.empty:
        if combination_mode == "Individual":
            st.info("🔄 Individual Mode: Each FULL existing case + Each FULL new case")
        else:
            st.info("🔄 Combined Mode: Each FULL existing case + ALL new cases merged into one")
    
        existing_profiles = {}
        new_profiles = {}
        existing_well_profiles = {}
        new_well_profiles = {}
    
        # Generate full existing case profiles
        for existing_case in existing_cases:
            case_data = existing_df[existing_df["case_label"] == existing_case]
            profile, eur, well_profiles = generate_full_case_profile_with_wells(
                case_data, existing_case
            )
            if profile is not None and not profile.empty:
                if resolution == "Monthly":
                    profile = convert_to_monthly_totals(profile)
                    well_profiles = [convert_to_monthly_totals(wp) for wp in well_profiles if not wp.empty]
                existing_profiles[existing_case] = profile
                existing_well_profiles[existing_case] = well_profiles
                eur_summary.extend(eur)
    
        # Generate full new case profiles
        for new_case in new_cases:
            case_data = new_df[new_df["case_label"] == new_case]
            profile, eur, well_profiles = generate_full_case_profile_with_wells(
                case_data, new_case
            )
            if profile is not None and not profile.empty:
                if resolution == "Monthly":
                    profile = convert_to_monthly_totals(profile)
                    well_profiles = [convert_to_monthly_totals(wp) for wp in well_profiles if not wp.empty]
                new_profiles[new_case] = profile
                new_well_profiles[new_case] = well_profiles
                eur_summary.extend(eur)
    
        # ===== COMBINATION LOGIC BASED ON MODE =====
        if combination_mode == "Individual":
            # Current behavior: Each existing + Each new separately
            for existing_case, ex_profile in existing_profiles.items():
                for new_case, nw_profile in new_profiles.items():
                    combined_name = f"{existing_case} + {new_case}"
                    
                    combined_profile = combine_case_profiles(ex_profile, nw_profile, combined_name)
                    all_profiles.append(combined_profile)
                    
                    combined_well_profiles = []
                    if existing_case in existing_well_profiles:
                        combined_well_profiles.extend(existing_well_profiles[existing_case])
                    if new_case in new_well_profiles:
                        combined_well_profiles.extend(new_well_profiles[new_case])
                    all_well_profiles_dict[combined_name] = combined_well_profiles
                    
                    ex_eur_items = [item for item in eur_summary if item["Case"] == existing_case]
                    nw_eur_items = [item for item in eur_summary if item["Case"] == new_case]
                    
                    # Calculate totals for Historical, Forecast, and EUR
                    ex_historical_total = sum([item["Historical (MMstb)"] for item in ex_eur_items]) if ex_eur_items else 0.0
                    ex_forecast_total = sum([item["Forecast (MMstb)"] for item in ex_eur_items]) if ex_eur_items else 0.0
                    ex_eur_total = sum([item["EUR (MMstb)"] for item in ex_eur_items]) if ex_eur_items else 0.0
                    
                    nw_historical_total = sum([item["Historical (MMstb)"] for item in nw_eur_items]) if nw_eur_items else 0.0
                    nw_forecast_total = sum([item["Forecast (MMstb)"] for item in nw_eur_items]) if nw_eur_items else 0.0
                    nw_eur_total = sum([item["EUR (MMstb)"] for item in nw_eur_items]) if nw_eur_items else 0.0
                    
                    ex_start_dates = [pd.to_datetime(item["Start date"]) for item in ex_eur_items if "Start date" in item]
                    nw_start_dates = [pd.to_datetime(item["Start date"]) for item in nw_eur_items if "Start date" in item]
                    
                    if ex_start_dates and nw_start_dates:
                        min_start_date = min(min(ex_start_dates), min(nw_start_dates))
                    elif ex_start_dates:
                        min_start_date = min(ex_start_dates)
                    elif nw_start_dates:
                        min_start_date = min(nw_start_dates)
                    else:
                        min_start_date = pd.Timestamp.now()
                    
                    eur_summary.append({
                        "Case": combined_name,
                        "Well": f"Combined: {existing_case} + {new_case}",
                        "Historical (MMstb)": round(ex_historical_total + nw_historical_total, 2),
                        "Forecast (MMstb)": round(ex_forecast_total + nw_forecast_total, 2),
                        "EUR (MMstb)": round(ex_eur_total + nw_eur_total, 2),
                        "Start date": min_start_date,
                        "Resolution": resolution
                    })
        
        else:  # combination_mode == "Combined"
            # NEW behavior: Merge all new cases into one, then combine with each existing
            if new_profiles:
                # Combine all new case profiles into one
                combined_new_name = " + ".join(new_cases)
                
                # Start with first new profile
                first_new_case = list(new_profiles.keys())[0]
                merged_new_profile = new_profiles[first_new_case].copy()
                merged_new_profile['case_label'] = combined_new_name
                
                # Merge remaining new profiles
                for new_case in list(new_profiles.keys())[1:]:
                    merged_new_profile = combine_case_profiles(
                        merged_new_profile, 
                        new_profiles[new_case], 
                        combined_new_name
                    )
                
                # Collect all new well profiles
                all_new_well_profiles = []
                for new_case in new_cases:
                    if new_case in new_well_profiles:
                        all_new_well_profiles.extend(new_well_profiles[new_case])
                
                # Calculate combined new EUR
                all_new_eur_items = [item for item in eur_summary if item["Case"] in new_cases]
                combined_new_historical = sum([item["Historical (MMstb)"] for item in all_new_eur_items])
                combined_new_forecast = sum([item["Forecast (MMstb)"] for item in all_new_eur_items])
                combined_new_eur = sum([item["EUR (MMstb)"] for item in all_new_eur_items])
                
                new_start_dates = [pd.to_datetime(item["Start date"]) for item in all_new_eur_items if "Start date" in item]
                min_new_start = min(new_start_dates) if new_start_dates else pd.Timestamp.now()
                
                # Now combine with each existing case
                for existing_case, ex_profile in existing_profiles.items():
                    combined_name = f"{existing_case} + ({combined_new_name})"
                    
                    combined_profile = combine_case_profiles(ex_profile, merged_new_profile, combined_name)
                    all_profiles.append(combined_profile)
                    
                    # Combine well profiles
                    combined_well_profiles = []
                    if existing_case in existing_well_profiles:
                        combined_well_profiles.extend(existing_well_profiles[existing_case])
                    combined_well_profiles.extend(all_new_well_profiles)
                    all_well_profiles_dict[combined_name] = combined_well_profiles
                    
                    # Calculate EUR
                    ex_eur_items = [item for item in eur_summary if item["Case"] == existing_case]
                    ex_historical_total = sum([item["Historical (MMstb)"] for item in ex_eur_items]) if ex_eur_items else 0.0
                    ex_forecast_total = sum([item["Forecast (MMstb)"] for item in ex_eur_items]) if ex_eur_items else 0.0
                    ex_eur_total = sum([item["EUR (MMstb)"] for item in ex_eur_items]) if ex_eur_items else 0.0
                    
                    ex_start_dates = [pd.to_datetime(item["Start date"]) for item in ex_eur_items if "Start date" in item]
                    min_ex_start = min(ex_start_dates) if ex_start_dates else pd.Timestamp.now()
                    
                    eur_summary.append({
                        "Case": combined_name,
                        "Well": f"Combined: {existing_case} + All New Cases",
                        "Historical (MMstb)": round(ex_historical_total + combined_new_historical, 2),
                        "Forecast (MMstb)": round(ex_forecast_total + combined_new_forecast, 2),
                        "EUR (MMstb)": round(ex_eur_total + combined_new_eur, 2),
                        "Start date": min(min_ex_start, min_new_start),
                        "Resolution": resolution
                    })
   
    if all_profiles and eur_summary:
         display_comparison_results(all_profiles, eur_summary, resolution, all_well_profiles_dict,
                              existing_cases, new_cases, existing_df, new_df)
    else:
        st.warning("No profiles generated. Please check your case selections.")

def generate_full_case_profile_with_wells(case_data: pd.DataFrame, case_label: str, 
                                         df_prod_daily: pd.DataFrame = None, df_prod_monthly: pd.DataFrame = None) -> Tuple[pd.DataFrame, List[Dict], List[pd.DataFrame]]:
    """
    Generate a COMPLETE case profile by aggregating ALL wells in the case + return individual well profiles.
    
    Handles:
    - Wells with qi=0 (no forecast) by including only their historical production
    - All selection types (well, multi_well, field, multi_field, company)
    - Mixed dca_time within same case (daily + monthly) by converting to common resolution
    - Proper data loading using load_production_data_by_selection
    """
   
    if case_data.empty:
        return pd.DataFrame(columns=["date", "rate", "cumulative", "case_label", "dca_time", "well_name"]), [], []
   
    all_well_profiles = []
    individual_well_profiles = []
    eur_list = []
    
   
    # ===== NEW: Determine common resolution for the case =====
    # Check if case has mixed resolutions (daily + monthly)
    case_dca_times = case_data['dca_time'].dropna().unique()
    
    # If mixed resolutions, standardize to monthly
    if len(case_dca_times) > 1:
        target_resolution = "monthly"
        st.info(f"⚠️ Case '{case_label}' has mixed resolutions ({', '.join(case_dca_times)}). Converting all to MONTHLY for consistency.")
    else:
        target_resolution = case_dca_times[0] if len(case_dca_times) > 0 else "monthly"
    
    # Get first row to determine overall case settings
    first_row = case_data.iloc[0]
    selection_type = first_row.get("selection_type", "well")
    company = first_row.get('company_name', 'Alamein')
    well_type = first_row.get("well_type", "existing")
    
    # Process each row in case_data (each well/entity in the case)
    for _, row in case_data.iterrows():
        well_id = row["well_name"]
        well_type = row.get("well_type", "existing")
        well_dca_time = row.get("dca_time", "monthly")  # ===== Get this well's dca_time =====
        entity_identifier = row.get("entity_identifier", well_id)
        
        if company == 'Petrosila':
            well_dca_time = 'daily'
        
        eff_ts = pd.to_datetime(row["eff_date"], errors="coerce")
       
        if pd.isna(eff_ts):
            st.warning(f"⚠️ Skipping well {well_id}: Invalid eff_date")
            continue
        
        # Check if this well has forecast parameters (qi > 0)
        has_forecast = (not pd.isna(row["qi"]) and 
                       not pd.isna(row["di"]) and 
                       not pd.isna(row["b"]) and 
                       float(row["qi"]) > 0)
        
        # Get q_abandon and end_of_lease from row or use defaults
        q_abandon_well = row.get('q_abandon')
        if pd.isna(q_abandon_well):
            q_abandon_well = 300
        
        end_of_lease = row.get('end_of_lease')
        if pd.isna(end_of_lease):
            end_of_lease = '2039-12-31'
        end_of_lease_ts = pd.to_datetime(end_of_lease)
       
        # ===== Load historical data for THIS specific well using ITS dca_time =====
        hist_before = pd.DataFrame()
        
        if well_type == "existing":
            try:
                # Get the actual selection_type from the row
                row_selection_type = row.get("selection_type", "well")  # <-- GET IT FROM ROW
                
                df_prod = DatabaseManager.load_production_data_by_selection(
                    selection_type=row_selection_type,  # <-- USE THE ACTUAL SELECTION TYPE
                    entity_identifier=entity_identifier,
                    company=company,
                    dca_time=well_dca_time
                )
                
                if df_prod is not None and not df_prod.empty:
                    df_prod['date'] = pd.to_datetime(df_prod['date'])
                    eff_ts_timestamp = pd.Timestamp(eff_ts)
                    df_prod = df_prod[df_prod["date"] < eff_ts_timestamp]
                    
                    if not df_prod.empty:
                        hist_before = df_prod[["date", "net"]].rename(columns={"net": "rate"})
                        hist_before["case_label"] = case_label
                        hist_before["well_name"] = well_id
                        hist_before["dca_time"] = well_dca_time
                        hist_before["date"] = pd.to_datetime(hist_before["date"])
                        hist_before["rate"] = pd.to_numeric(hist_before["rate"], errors="coerce").fillna(0.0)
                        
                        # ===== Convert daily historical to monthly if needed =====
                        if well_dca_time == "daily" and target_resolution == "monthly":
                            hist_before = convert_to_monthly_totals(hist_before)
                            
            except Exception as e:
                st.warning(f"⚠️ Could not load historical data for well '{well_id}': {e}")

                
                if df_prod is not None and not df_prod.empty:
                    df_prod['date'] = pd.to_datetime(df_prod['date'])
                    eff_ts_timestamp = pd.Timestamp(eff_ts)
                    df_prod = df_prod[df_prod["date"] < eff_ts_timestamp]
                    
                    if not df_prod.empty:
                        hist_before = df_prod[["date", "net"]].rename(columns={"net": "rate"})
                        hist_before["case_label"] = case_label
                        hist_before["well_name"] = well_id
                        hist_before["dca_time"] = well_dca_time
                        hist_before["date"] = pd.to_datetime(hist_before["date"])
                        hist_before["rate"] = pd.to_numeric(hist_before["rate"], errors="coerce").fillna(0.0)
                        
                        # ===== Convert daily historical to monthly if needed =====
                        if well_dca_time == "daily" and target_resolution == "monthly":
                            hist_before = convert_to_monthly_totals(hist_before)
                            
            except Exception as e:
                st.warning(f"⚠️ Could not load historical data for well '{well_id}': {e}")
       
        # ===== Generate forecast using well's own dca_time =====
        forecast_df = pd.DataFrame()
        if has_forecast:
            freq = "D" if well_dca_time == "daily" else "MS"
           
            try:
                forecast_df = ARPSModel.create_production_profile(
                    start_date=eff_ts,
                    end_date=end_of_lease_ts,
                    qi=float(row["qi"]),
                    di=float(row["di"]),
                    b=float(row["b"]),
                    q_abandon=float(q_abandon_well),
                    frequency=freq
                )
                
                if not forecast_df.empty:
                    forecast_df = forecast_df.copy()
                    forecast_df["case_label"] = case_label
                    forecast_df["well_name"] = well_id
                    forecast_df["dca_time"] = well_dca_time
                    forecast_df["date"] = pd.to_datetime(forecast_df["date"], errors="coerce")
                    forecast_df["rate"] = pd.to_numeric(forecast_df["rate"], errors="coerce").fillna(0.0)
                    
                    # ===== Convert daily forecast to monthly if needed =====
                    if well_dca_time == "daily" and target_resolution == "monthly":
                        forecast_df = convert_to_monthly_totals(forecast_df)
                        
            except Exception as e:
                st.warning(f"⚠️ Error generating forecast for well {well_id}: {e}")
                forecast_df = pd.DataFrame()
       
        # Combine historical + forecast for this well
        well_parts = []
        if not hist_before.empty:
            well_parts.append(hist_before)
        if not forecast_df.empty:
            well_parts.append(forecast_df)
       
        
        # Include well if it has data
        if well_parts:
            well_combined = pd.concat(well_parts, ignore_index=True)
            well_combined = well_combined.sort_values("date")
            well_combined["rate"] = pd.to_numeric(well_combined["rate"], errors="coerce").fillna(0.0)
            well_combined["dca_time"] = target_resolution
            all_well_profiles.append(well_combined)
            individual_well_profiles.append(well_combined.copy())
            
            # Calculate EUR components
            hist_cum = hist_before["rate"].sum() if not hist_before.empty else 0.0
            forecast_cum = forecast_df["rate"].sum() if not forecast_df.empty else 0.0
            
            if not forecast_df.empty:
                eur_val = ARPSModel.calculate_eur(forecast_df, hist_cum)
                eur_type = "Historical + Forecast"
            else:
                eur_val = hist_cum
                eur_type = "Historical Only (qi=0)"
            
            try:
                eur_val = float(eur_val)
                hist_cum = float(hist_cum)
                forecast_cum = float(forecast_cum)
            except (TypeError, ValueError):
                eur_val = 0.0
                hist_cum = 0.0
                forecast_cum = 0.0
                
            if pd.isna(eur_val):
                eur_val = 0.0
            if pd.isna(hist_cum):
                hist_cum = 0.0
            if pd.isna(forecast_cum):
                forecast_cum = 0.0
            
            eur_list.append({
                "Case": case_label,
                "Well": well_id,
                "Historical (MMstb)": round(hist_cum / 1_000, 3),      # NEW
                "Forecast (MMstb)": round(forecast_cum / 1_000, 3),    # NEW
                "EUR (MMstb)": round(eur_val / 1_000, 3),
                "Start date": eff_ts,
                "Resolution": target_resolution.capitalize(),
                "Type": eur_type
            })
            
        elif has_forecast:
            if not forecast_df.empty:
                forecast_df["dca_time"] = target_resolution
                all_well_profiles.append(forecast_df)
                individual_well_profiles.append(forecast_df.copy())
                
                forecast_cum = forecast_df["rate"].sum()
                eur_val = ARPSModel.calculate_eur(forecast_df, 0.0)
                
                try:
                    eur_val = float(eur_val)
                    forecast_cum = float(forecast_cum)
                except (TypeError, ValueError):
                    eur_val = 0.0
                    forecast_cum = 0.0
                if pd.isna(eur_val):
                    eur_val = 0.0
                if pd.isna(forecast_cum):
                    forecast_cum = 0.0
                
                eur_list.append({
                    "Case": case_label,
                    "Well": well_id,
                    "Historical (MMstb)": 0.0,                          # NEW
                    "Forecast (MMstb)": round(forecast_cum / 1_000, 3), # NEW
                    "EUR (MMstb)": round(eur_val / 1_000, 3),
                    "Start date": eff_ts,
                    "Resolution": target_resolution.capitalize(),
                    "Type": "Forecast Only"
                })
        else:
            st.warning(f"⚠️ Well {well_id} in case {case_label} has no historical or forecast data")
            eur_list.append({
                "Case": case_label,
                "Well": well_id,
                "Historical (MMstb)": 0.0,  # NEW
                "Forecast (MMstb)": 0.0,    # NEW
                "EUR (MMstb)": 0.0,
                "Start date": eff_ts,
                "Resolution": target_resolution.capitalize(),
                "Type": "No Data"
            })
   
    # Aggregate ALL wells in the case into one profile
    if all_well_profiles:
        all_wells_df = pd.concat(all_well_profiles, ignore_index=True)
       
        case_profile = (all_wells_df.groupby("date", as_index=False)["rate"]
                       .sum()
                       .sort_values("date"))
       
        case_profile["case_label"] = case_label
        case_profile["cumulative"] = case_profile["rate"].cumsum()
        case_profile["dca_time"] = target_resolution  # ===== Use target resolution =====
        case_profile["well_name"] = ";".join(case_data["well_name"].dropna().unique())
       
        return case_profile, eur_list, individual_well_profiles
   
    # No profiles generated - return empty but keep EUR list for tracking
    st.warning(f"⚠️ No profiles generated for case {case_label}. Check data availability.")
    return pd.DataFrame(columns=["date", "rate", "cumulative", "case_label", "dca_time", "well_name"]), eur_list, []

def display_comparison_results(all_profiles: list, eur_summary: list, resolution: str, 
                              all_well_profiles_dict: Dict[str, List[pd.DataFrame]],
                              existing_cases: list, new_cases: list, 
                              existing_df: pd.DataFrame, new_df: pd.DataFrame):
    """Display comparison results with charts and professionally styled tables + Export functionality"""
    unit_tag = "bbl/month" if resolution == "Monthly" else "bbl/day"
   
    eur_df = pd.DataFrame(eur_summary)
   
    # Create filter options
    case_options = ["All Cases"]
    if not eur_df.empty:
        case_options.extend(eur_df["Case"].unique().tolist())
   
    selected_filter = st.selectbox("Filter View", case_options, index=0)
   
    # Add Export Button
    st.markdown("---")
    col_export1, col_export2, col_export3 = st.columns([2, 1, 2])
   
    with col_export1:
        if "button_clicked" not in st.session_state:
            st.session_state.button_clicked = False
        
        def button_callback():
            st.session_state.button_clicked = True
   
        st.button("📥 Export Data to CSV", key="export_data", help="Download all case data as CSV files in a ZIP archive", on_click=button_callback)
   
        if st.session_state.button_clicked:
            export_data = create_export_data(all_profiles, all_well_profiles_dict)
           
            if export_data:
                zip_data = create_download_zip(export_data, resolution)
               
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"scenario_comparison_export_{resolution.lower()}_{timestamp}.zip"
               
                st.download_button(
                    label="📄 Download ZIP File",
                    data=zip_data,
                    file_name=filename,
                    mime="application/zip",
                    help=f"Contains case summaries and wells pivot tables for all {len(all_profiles)} cases/combinations"
                )
               
                st.success(f"✅ Export package ready! Contains {len(export_data)} CSV files from {len(all_profiles)} cases/combinations.")
                time.sleep(1.5)
                st.session_state.button_clicked = True
               
                with st.expander("📋 Export Contents"):
                    for filename in export_data.keys():
                        file_type = "Case Summary" if "case_summary" in filename else "Wells Pivot"
                        st.write(f"• **{filename}.csv** - {file_type}")
            else:
                st.error("❌ No data available for export")
   
        st.markdown("---")
   
    col1, col2 = st.columns([2,1])
   
    with col1:
        st.subheader("📊 EUR Summary")
    
        if selected_filter == "All Cases":
            filtered_eur = eur_df.copy()
        else:
            filtered_eur = eur_df[eur_df["Case"] == selected_filter].copy()
    
        if not filtered_eur.empty:
            # Create display dataframe with proper columns including new Historical and Forecast columns
            display_df = filtered_eur[['Case', 'Well', 'Historical (MMstb)', 'Forecast (MMstb)', 'EUR (MMstb)', 'Start date', 'Resolution']].copy()
            
            # Add Type column if it exists
            if 'Type' in filtered_eur.columns:
                display_df['Type'] = filtered_eur['Type']
            
            # Sort by EUR from highest to lowest
            display_df = display_df.sort_values('EUR (MMstb)', ascending=False)
            
            styled_eur = (
                display_df.style
                .format({
                    "Historical (MMstb)": "{:.2f}",
                    "Forecast (MMstb)": "{:.2f}",
                    "EUR (MMstb)": "{:.2f}"
                })
                .background_gradient(cmap='Blues', subset=['Historical (MMstb)'], low=0.1, high=0.8)
                .background_gradient(cmap='Greens', subset=['Forecast (MMstb)'], low=0.1, high=0.8)
                .background_gradient(cmap='Oranges', subset=['EUR (MMstb)'], low=0.1, high=0.8)
                .set_table_styles([
                    {'selector': 'thead th', 'props': [
                        ('background-color', '#ff8c00'),
                        ('color', 'white'),
                        ('font-weight', 'bold'),
                        ('text-align', 'center'),
                        ('font-size', '14px')
                    ]},
                    {'selector': 'tbody td', 'props': [
                        ('text-align', 'center'),
                        ('padding', '8px'),
                        ('border', '1px solid #ddd')
                    ]},
                    {'selector': 'table', 'props': [
                        ('border-collapse', 'collapse'),
                        ('margin', '0 auto'),
                        ('width', '100%')
                    ]}
                ])
            )
            st.write(styled_eur.to_html(), unsafe_allow_html=True)
            
            # Add export button for EUR Summary
            csv_eur = display_df.to_csv(index=False)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Export EUR Summary as CSV",
                data=csv_eur,
                file_name=f"eur_summary_{selected_filter.replace(' ', '_')}_{timestamp}.csv",
                mime="text/csv",
                key="export_eur_summary"
            )
        else:
            st.info("No EUR data available")

    with col2:
        st.subheader("📈 Total EUR by Scenario")
        if not eur_df.empty:
            total_eur = (
                eur_df.groupby("Case", as_index=False).agg({
                    "Historical (MMstb)": "sum",
                    "Forecast (MMstb)": "sum",
                    "EUR (MMstb)": "sum"
                })
                .sort_values("EUR (MMstb)", ascending=False)
            )
            
            styled_total = (
                total_eur.style
                .format({
                    "Historical (MMstb)": "{:.2f}",
                    "Forecast (MMstb)": "{:.2f}",
                    "EUR (MMstb)": "{:.2f}"
                })
                .background_gradient(cmap='Blues', subset=['Historical (MMstb)'], low=0.2, high=0.9)
                .background_gradient(cmap='Greens', subset=['Forecast (MMstb)'], low=0.2, high=0.9)
                .background_gradient(cmap='Oranges', subset=['EUR (MMstb)'], low=0.2, high=0.9)
                .set_table_styles([
                    {'selector': 'thead th', 'props': [
                        ('background-color', '#ff6600'),
                        ('color', 'white'),
                        ('font-weight', 'bold'),
                        ('text-align', 'center')
                    ]}
                ])
            )
            st.write(styled_total.to_html(), unsafe_allow_html=True)
            
            # Add export button for Total EUR
            csv_total = total_eur.to_csv(index=False)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📥 Export Total EUR as CSV",
                data=csv_total,
                file_name=f"total_eur_by_scenario_{timestamp}.csv",
                mime="text/csv",
                key="export_total_eurr"
            )
        else:
            st.info("No total EUR data available")

    
   
    if not all_profiles:
        st.warning("No profile data available for plotting")
        return
   
    # Combine all profiles for plotting
    combined_df = pd.concat(all_profiles, ignore_index=True)
   
    # Filter profiles based on selection
    if selected_filter != "All Cases":
        combined_df = combined_df[combined_df["case_label"] == selected_filter]
   
    # Create production rate plot
    fig1 = go.Figure()
    colors = px.colors.qualitative.Set1
   
    for i, case in enumerate(combined_df["case_label"].unique()):
        case_data = combined_df[combined_df["case_label"] == case]
        fig1.add_trace(go.Scatter(
            x=case_data["date"],
            y=case_data["rate"],
            mode="lines",
            name=case,
            line=dict(color=colors[i % len(colors)], width=2)
        ))
   
    fig1.update_layout(
        title=f"Production Rate - {resolution} {'' if resolution == 'Daily' else 'Totals'}",
        xaxis_title="Date",
        yaxis_title=f"Rate ({unit_tag})",
        hovermode="x unified",
        plot_bgcolor="white",
        height=500
    )
   
    # Create cumulative production plot
    fig2 = go.Figure()
    for i, case in enumerate(combined_df["case_label"].unique()):
        case_data = combined_df[combined_df["case_label"] == case].copy()
        case_data = case_data.sort_values("date")
        case_data["cum_rate"] = case_data["rate"].cumsum()
       
        fig2.add_trace(go.Scatter(
            x=case_data["date"],
            y=case_data["cum_rate"],
            mode="lines",
            name=case,
            line=dict(color=colors[i % len(colors)], width=2)
        ))
   
    fig2.update_layout(
        title="Cumulative Production",
        xaxis_title="Date",
        yaxis_title="Cumulative Volume (bbl)",
        hovermode="x unified",
        plot_bgcolor="white",
        height=500
    )
   
    left, right = st.columns(2)
    with left:
        st.plotly_chart(fig1, use_container_width=True)
    with right:
        st.plotly_chart(fig2, use_container_width=True)
        # ========== FORECAST-ONLY STACKED AREA CHART =======

    # ========== FORECAST-ONLY STACKED AREA CHART ==========
    st.markdown("---")
    st.subheader("🔮 Forecast Production - Stacked Area Chart")
    st.info("Showing forecast-only production: Existing baseline + New incremental stacked on top")

    # Extract forecast-only data from profiles
    forecast_only_profiles = []

    # Process COMBINED cases to extract their components
    for profile in all_profiles:
        if profile.empty:
            continue
        
        case_label = profile['case_label'].iloc[0]
        
        # Check if this is a combined case
        if ' + ' in case_label:
            # Get well profiles from combined case
            if case_label in all_well_profiles_dict:
                combined_well_profiles = all_well_profiles_dict[case_label]
                
                # Split the case label to get component names
                parts = case_label.split(' + ')
                
                for part in parts:
                    part = part.strip()
                    
                    # Determine if this part is existing or new
                    if part in existing_cases:
                        case_type = "existing"
                        part_data = existing_df[existing_df['case_label'] == part]
                    elif part in new_cases:
                        case_type = "new"
                        part_data = new_df[new_df['case_label'] == part]
                    else:
                        continue
                    
                    if not part_data.empty:
                        # Get well names that belong to this part
                        part_well_names = part_data['well_name'].unique().tolist()
                        min_eff_date = pd.to_datetime(part_data['eff_date']).min()
                        
                        # Filter well profiles that belong to this part
                        part_wells = []
                        for wp in combined_well_profiles:
                            if not wp.empty:
                                well_name = wp['well_name'].iloc[0]
                                # Handle multi-well names (separated by semicolon)
                                if ';' in str(well_name):
                                    well_names_list = str(well_name).split(';')
                                else:
                                    well_names_list = [str(well_name)]
                                
                                # Check if any of this well profile's wells belong to this part
                                if any(wn in part_well_names for wn in well_names_list):
                                    part_wells.append(wp)
                        
                        if part_wells:
                            # Aggregate wells for this part
                            all_wells_for_part = pd.concat(part_wells, ignore_index=True)
                            all_wells_for_part['date'] = pd.to_datetime(all_wells_for_part['date'])
                            
                            # Filter to forecast only (date >= eff_date)
                            forecast_only = all_wells_for_part[all_wells_for_part['date'] >= min_eff_date].copy()
                            
                            if not forecast_only.empty:
                                # Aggregate by date
                                forecast_agg = forecast_only.groupby('date', as_index=False)['rate'].sum()
                                forecast_agg['case_label'] = part
                                forecast_agg['case_type'] = case_type
                                forecast_agg['stack_order'] = 1 if case_type == "existing" else 2
                                forecast_only_profiles.append(forecast_agg)

    # Create stacked area chart
    # Create stacked area chart
    if forecast_only_profiles:
        combined_forecast_df = pd.concat(forecast_only_profiles, ignore_index=True)
        
        if not combined_forecast_df.empty:
            # Determine layout based on resolution
            if resolution == "Monthly":
                # Show two charts side by side
                chart_col1, chart_col2 = st.columns(2)
            else:
                # Show only one chart
                chart_col1 = st.container()
                chart_col2 = None
            
            # ========== CHART 1: Standard Stacked Area (Monthly Totals or Daily) ==========
            with chart_col1:
                fig3 = go.Figure()
                
               
                # Color palettes - Maximum contrast and distinction
                color_map_existing = [
                    "#0E0F10",  # Cobalt Blue
                    '#8B00FF',  # Electric Violet
                    '#00BFFF',  # Deep Sky Blue
                    '#4169E1',  # Royal Blue
                    '#9932CC',  # Dark Orchid
                    '#00CED1'   # Dark Turquoise
                ]

                color_map_new = [
                    '#00A86B',  # Jade Green
                    '#FF8C00',  # Dark Orange
                    '#FFD700',  # Gold
                    '#32CD32',  # Lime Green
                    '#FF4500',  # Orange Red
                    '#ADFF2F'   # Green Yellow
                ]
                
                existing_idx = 0
                new_idx = 0
                
                # Sort by stack_order: existing first (bottom), then new (top)
                unique_cases = combined_forecast_df[["case_label", "case_type", "stack_order"]].drop_duplicates()
                unique_cases = unique_cases.sort_values('stack_order')
                
                for _, row in unique_cases.iterrows():
                    case = row["case_label"]
                    case_type = row["case_type"]
                    
                    case_data = combined_forecast_df[combined_forecast_df["case_label"] == case].sort_values("date")
                    
                    if case_type == "existing":
                        fill_color = color_map_existing[existing_idx % len(color_map_existing)]
                        existing_idx += 1
                    elif case_type == "new":
                        fill_color = color_map_new[new_idx % len(color_map_new)]
                        new_idx += 1
                    else:
                        fill_color = "#999999"
                    
                    fig3.add_trace(go.Scatter(
                        x=case_data["date"],
                        y=case_data["rate"],
                        mode="lines",
                        name=case,
                        line=dict(width=0.5, color=fill_color),
                        fillcolor=fill_color,
                        stackgroup="one",
                        hovertemplate='<b>%{fullData.name}</b><br>' +
                                    'Date: %{x|%Y-%m-%d}<br>' +
                                    f'Rate: %{{y:,.0f}} {unit_tag}<br>' +
                                    '<extra></extra>'
                    ))
                
                chart_title = "📊 Forecast Production (Stacked)" if resolution == "Monthly" else "📊 Forecast-Only Production (Stacked)"
                
                fig3.update_layout(
                    title=f"{chart_title} - {resolution} {'' if resolution == 'Daily' else 'Totals'}",
                    xaxis_title="Date",
                    yaxis_title=f"Rate ({unit_tag})",
                    hovermode="x unified",
                    plot_bgcolor="white",
                    height=650,
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.01,
                        bgcolor="rgba(255, 255, 255, 0.8)",
                        bordercolor="gray",
                        borderwidth=1
                    ),
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='lightgray',
                        gridwidth=0.5
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='lightgray',
                        gridwidth=0.5
                    )
                )
                
                st.plotly_chart(fig3, use_container_width=True)
            
            # ========== CHART 2: Calendar Day Average (Monthly only) ==========
            if resolution == "Monthly" and chart_col2 is not None:
                with chart_col2:
                    # Calculate calendar day average (divide by days in month)
                    combined_forecast_df_daily = combined_forecast_df.copy()
                    combined_forecast_df_daily['date'] = pd.to_datetime(combined_forecast_df_daily['date'])
                    
                    # Get number of days in each month
                    combined_forecast_df_daily['days_in_month'] = combined_forecast_df_daily['date'].dt.days_in_month
                    
                    # Calculate daily average
                    combined_forecast_df_daily['rate_per_day'] = combined_forecast_df_daily['rate'] / combined_forecast_df_daily['days_in_month']
                    
                    fig4 = go.Figure()
                    
                    existing_idx = 0
                    new_idx = 0
                    
                    # Use same sorting
                    unique_cases = combined_forecast_df_daily[["case_label", "case_type", "stack_order"]].drop_duplicates()
                    unique_cases = unique_cases.sort_values('stack_order')
                    
                    for _, row in unique_cases.iterrows():
                        case = row["case_label"]
                        case_type = row["case_type"]
                        
                        case_data = combined_forecast_df_daily[combined_forecast_df_daily["case_label"] == case].sort_values("date")
                        
                        if case_type == "existing":
                            fill_color = color_map_existing[existing_idx % len(color_map_existing)]
                            existing_idx += 1
                        elif case_type == "new":
                            fill_color = color_map_new[new_idx % len(color_map_new)]
                            new_idx += 1
                        else:
                            fill_color = "#999999"
                        
                        fig4.add_trace(go.Scatter(
                            x=case_data["date"],
                            y=case_data["rate_per_day"],
                            mode="lines",
                            name=case,
                            line=dict(width=0.5, color=fill_color),
                            fillcolor=fill_color,
                            stackgroup="one",
                            hovertemplate='<b>%{fullData.name}</b><br>' +
                                        'Date: %{x|%Y-%m-%d}<br>' +
                                        'Rate: %{y:,.1f} bbl/day<br>' +
                                        '<extra></extra>'
                        ))
                    
                    fig4.update_layout(
                        title="📊 Forecast Production (Stacked) - Calendar Day Average",
                        xaxis_title="Date",
                        yaxis_title="Rate (bbl/calendar day)",
                        hovermode="x unified",
                        plot_bgcolor="white",
                        height=650,
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.01,
                            bgcolor="rgba(255, 255, 255, 0.8)",
                            bordercolor="gray",
                            borderwidth=1
                        ),
                        xaxis=dict(
                            showgrid=True,
                            gridcolor='lightgray',
                            gridwidth=0.5
                        ),
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='lightgray',
                            gridwidth=0.5
                        )
                    )
                    
                    st.plotly_chart(fig4, use_container_width=True)
            
            # Legend explanation
            col_legend1, col_legend2 = st.columns(2)
            with col_legend1:
                st.markdown("🔵 **Blue**: Existing wells forecast")
            with col_legend2:
                st.markdown("🟢 **Green**: New wells forecast (stacked)")
            
            if resolution == "Monthly":
                st.info("💡 **Left chart**: Monthly totals (bbl/month) | **Right chart**: Calendar day average (bbl/day) - makes small incremental wells more visible")
            else:
                st.info("💡 **Interpretation**: Green area shows incremental production from new wells stacked on top of existing baseline.")
        else:
            st.info("No data to display")
    else:
        st.warning("⚠️ No forecast data available for stacked area chart")

main()
    