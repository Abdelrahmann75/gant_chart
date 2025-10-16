
import streamlit as st
import pandas as pd
import numpy as np
from utils.arps_classes_original import DatabaseManager, ARPSModel
from utils.css_style import load_custom_css_admin
from utils.crud_panel import render_crud_operations ,render_import_from_case
from dateutil.relativedelta import relativedelta
from utils.login_panel import AuthManager
from datetime import date

# Custom CSS for styling
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #2c3e50;
        padding: 1rem 0;
        border-bottom: 2px solid #3498db;
    }
    .section-header {
        color: #2c3e50;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #e8f4f8;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #3498db;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #d4edda;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #28a745;
        margin-bottom: 1rem;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #ffc107;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 5px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .stButton>button {
        background-color: #3498db;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #2980b9;
    }
    .main .block-container {
        max-width: 90%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# =================== CASE AUTO INITIALIZATION TAB ===================
def render_case_auto_initialization():
    st.markdown('<h2 class="section-header">Case Auto Initialization Dashboard</h2>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Automatically fit ARPS parameters for multiple wells at once and save them as cases</div>', unsafe_allow_html=True)
    
    # Company and Resolution Selection
    col1, col2 = st.columns(2)
    
    with col1:
        selected_company = st.selectbox(
            "Select Company:",
            options=["Alamein", "Petrosila"],
            key="auto_init_company"
        )
    
    with col2:
        resolution_options = ["Monthly", "Daily"] if selected_company == "Alamein" else ["Daily"]
        resolution = st.radio(
            "Data Resolution:",
            options=resolution_options,
            key="auto_init_resolution"
        )
    
    dca_time = "daily" if resolution == "Daily" else "monthly"
    unit_tag = "bbl/day" if dca_time == "daily" else "bbl/month"
    
    # Load production data
    with st.spinner("Loading production data..."):
        df_prod = DatabaseManager.load_production_data(
            company=selected_company,
            dca_time=dca_time
        )
    
    if df_prod is None or df_prod.empty:
        st.error("No production data available")
        return
    
    # Ensure unique_id column exists
    if 'unique_id' not in df_prod.columns:
        possible_cols = ['well_id', 'well_name', 'wellname', 'well_bore']
        for col in possible_cols:
            if col in df_prod.columns:
                df_prod['unique_id'] = df_prod[col]
                break
    
    st.markdown("---")
    
    # Field Selection with "All Fields" option
    st.markdown('<h3 class="section-header">Field & Well Selection</h3>', unsafe_allow_html=True)
    
    col_field1, col_field2 = st.columns([3, 1])
    
    with col_field1:
        available_fields = sorted(df_prod['field'].dropna().unique().tolist()) if 'field' in df_prod.columns else []
        
        # Add "All Fields" option
        field_options = ["[All Fields]"] + available_fields
        
        selected_fields_raw = st.multiselect(
            f"Select Fields ({len(available_fields)} available):",
            options=field_options,
            key="auto_init_fields",
            help="Select specific fields or choose '[All Fields]' to include all"
        )
        
        # Process field selection
        if "[All Fields]" in selected_fields_raw:
            selected_fields = available_fields
            fields_display = "All Fields"
        else:
            selected_fields = selected_fields_raw
            fields_display = f"{len(selected_fields)} field(s)"
    
    # Well Selection with "All Wells" option
    col_wells1, col_wells2 = st.columns([3, 1])
    
    with col_wells1:
        # Filter wells by selected fields
        if selected_fields:
            available_wells = sorted(df_prod[df_prod['field'].isin(selected_fields)]['unique_id'].unique().tolist())
        else:
            available_wells = sorted(df_prod['unique_id'].unique().tolist())
        
        # Add "All Wells" option
        well_options = ["[All Wells]"] + available_wells
        
        # Auto-select all wells if fields were just selected
        default_wells = ["[All Wells]"] if selected_fields and len(selected_fields) > 0 else []
        
        selected_wells_raw = st.multiselect(
            f"Select Wells ({len(available_wells)} available in selected field(s)):",
            options=well_options,
            default=default_wells,
            key="auto_init_wells",
            help="Select specific wells or choose '[All Wells]' to include all wells in selected fields"
        )
        
        # Process well selection
        if "[All Wells]" in selected_wells_raw:
            selected_wells = available_wells
            wells_display = "All Wells"
        else:
            selected_wells = selected_wells_raw
            wells_display = f"{len(selected_wells)} well(s)"
    
    # Display selection summary
    if selected_wells:
        st.markdown(f'<div class="success-box"><strong>Selected:</strong> {fields_display} | {wells_display} ({len(selected_wells)} total wells)</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="warning-box"><strong>No wells selected</strong> - Please select at least one well</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Process Button
    if st.button("Auto-Fit ARPS Parameters", type="primary", disabled=len(selected_wells) == 0, use_container_width=True):
        if not selected_wells:
            st.warning("Please select at least one well")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        
        for idx, well in enumerate(selected_wells):
            status_text.text(f"Processing {idx + 1}/{len(selected_wells)}: {well}")
            progress_bar.progress((idx + 1) / len(selected_wells))
            
            # Get well data
            well_data = df_prod[df_prod['unique_id'] == well].copy()
            well_data = well_data.sort_values('date')
            
            # Drop rows with NaN in 'net' column
            well_data = well_data.dropna(subset=['net'])
            
            if len(well_data) < 3:
                continue
            
            # Prepare data for fitting
            time_data = np.arange(len(well_data))
            rate_data = well_data['net'].values
            
            # Fit ARPS parameters
            qi_fitted, di_fitted, b_fitted = ARPSModel.fit_arps_parameters(time_data, rate_data)
            
            # Get last rate (forecast qi)
            qi_forecast = float(rate_data[-1])
            q_abandon = 10.00 if dca_time == 'daily' else 300
            end_of_lease = '2039-12-31'
            
            # Get field
            well_field = well_data['field'].iloc[0] if 'field' in well_data.columns else None
            
            results.append({
                'Well Name': well,
                'Field': well_field,
                'Qi Regressed': round(qi_fitted, 2),
                'Qi Forecast': round(qi_forecast, 2),
                'Di': round(di_fitted, 4),
                'b': round(b_fitted, 3),
                'Data Points': len(well_data),
                'First Date': well_data['date'].min(),
                'Last Date': well_data['date'].max(),
                'q_abandon': q_abandon,
                'end_of_lease': end_of_lease
            })
        
        progress_bar.empty()
        status_text.empty()
        
        if results:
            results_df = pd.DataFrame(results)
            
            # Store results in session state with DIFFERENT keys
            st.session_state['fitted_results'] = results_df
            st.session_state['fitted_company'] = selected_company
            st.session_state['fitted_dca_time'] = dca_time
            
            st.success(f"Successfully fitted parameters for {len(results)} wells!")
            
            # Display statistics
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            
            with col_stat1:
                st.markdown(f'<div class="metric-card"><h3>Total Wells</h3><p>{len(results)}</p></div>', unsafe_allow_html=True)
            
            with col_stat2:
                avg_qi = results_df['Qi Forecast'].mean()
                st.markdown(f'<div class="metric-card"><h3>Avg Qi</h3><p>{avg_qi:.1f}</p></div>', unsafe_allow_html=True)
            
            with col_stat3:
                avg_di = results_df['Di'].mean()
                st.markdown(f'<div class="metric-card"><h3>Avg Di</h3><p>{avg_di:.4f}</p></div>', unsafe_allow_html=True)
            
            with col_stat4:
                avg_b = results_df['b'].mean()
                st.markdown(f'<div class="metric-card"><h3>Avg b</h3><p>{avg_b:.3f}</p></div>', unsafe_allow_html=True)
            
            st.markdown("---")
        else:
            st.error("No valid results. Please check your well data.")
    
    # Display results and save section if results exist
    if 'fitted_results' in st.session_state:
        results_df = st.session_state['fitted_results']
        
        # Display results table
        st.markdown('<h3 class="section-header">Auto-Fitted Parameters Summary</h3>', unsafe_allow_html=True)
        
        st.dataframe(
            results_df.style.background_gradient(cmap='Blues', subset=['Qi Forecast', 'Di', 'b']),
            use_container_width=True,
            height=400
        )
        
        # Save option
        st.markdown("---")
        st.markdown('<h3 class="section-header">Save Cases to Database</h3>', unsafe_allow_html=True)
        
        case_label_prefix = st.text_input(
            "Case Label Prefix:",
            value=f"AutoInit_{st.session_state['fitted_company']}_{st.session_state['fitted_dca_time'].capitalize()}",
            help="Each well will be saved as: Existing_prefix_wellname",
            key="case_label_prefix_input"
        )
        
        if st.button("Save All Cases to Database", type="primary", use_container_width=True, key="save_cases_btn"):
            save_progress = st.progress(0)
            save_status = st.empty()
            
            saved_count = 0
            failed_count = 0
            error_messages = []
            
            for idx, row in results_df.iterrows():
                save_status.text(f"Saving {idx + 1}/{len(results_df)}: {row['Well Name']}")
                save_progress.progress((idx + 1) / len(results_df))
                
                case_label = f"Existing_{case_label_prefix}"
                last_date = pd.to_datetime(row['Last Date'], errors='coerce')
                eff_date = (last_date + relativedelta(months=1)).strftime('%Y-%m-%d') if st.session_state['fitted_dca_time'] == 'monthly' else (last_date + relativedelta(days=1)).strftime('%Y-%m-%d')
                
                try:
                    success = DatabaseManager.save_forecast_case_aggregate(
                        well_name=row['Well Name'],
                        case_label=case_label,
                        selection_type="well",
                        entity_identifier=row['Well Name'],
                        eff_date=eff_date,
                        qi=float(row['Qi Forecast']),
                        di=float(row['Di']),
                        b=float(row['b']),
                        qi_regressed=float(row['Qi Regressed']),
                        ti_selected=row['First Date'],
                        q_abandon=float(row['q_abandon']),
                        end_of_lease='2039-12-31',
                        well_type="existing",
                        field=row['Field'],
                        dca_time=st.session_state['fitted_dca_time'],
                        company_name=st.session_state['fitted_company'],
                        user_id=user_id
                    )
                    
                    if success:
                        saved_count += 1
                    else:
                        failed_count += 1
                        error_messages.append(f"Failed to save {row['Well Name']}")
                except Exception as e:
                    failed_count += 1
                    error_messages.append(f"Error saving {row['Well Name']}: {str(e)}")
            
            save_progress.empty()
            save_status.empty()
            
            if failed_count == 0:
                st.success(f"Successfully saved all {saved_count} cases to database!")
                # Clear results after successful save
                if st.button("Clear Results", key="clear_results_btn"):
                    del st.session_state['fitted_results']
                    del st.session_state['fitted_company']
                    del st.session_state['fitted_dca_time']
                    st.rerun()
            else:
                st.warning(f"Saved {saved_count}/{len(results_df)} cases. {failed_count} failed.")
                with st.expander("View Errors"):
                    for msg in error_messages:
                        st.error(msg)



# =================== MAIN RENDER FUNCTION ===================
def render_admin_panel():
    """Main admin panel with pure Streamlit"""
    
    # Load custom CSS
    load_custom_css_admin()
    
    # Header
    st.markdown('<div class="main-header"><h1>🌟POLARIS Control Center</h1></div>', unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs([
        "Case Auto Initialization",
        "CRUD Operations",
        "Import from Case"
    ])
    
    with tab1:
        render_case_auto_initialization()
    
    with tab2:
        render_crud_operations()
    
    with tab3:
        render_import_from_case()

# Run the admin panel
if AuthManager.is_logged_in():
    user_id, username = AuthManager.get_current_user()
    render_admin_panel()
else:
    st.error("You must be logged in to access the admin panel.")
    st.markdown("[Go to Login](#)", unsafe_allow_html=True)
