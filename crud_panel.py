# crud_operations.py
import streamlit as st
import pandas as pd
import numpy as np
from utils.arps_classes_original import Config,DatabaseManager
from datetime import datetime, date
import sqlite3
from utils.login_panel import AuthManager
from datetime import date

# =================== HELPER FUNCTIONS ===================
def render_crud_operations():
    # Get current user
    if not AuthManager.is_logged_in():
        st.error("❌ You must be logged in to access this page.")
        return
    
    user_id, username = AuthManager.get_current_user()
    
    # Display current user info at the top
    st.info(f"👤 Logged in as: **{username}** (User ID: {user_id})")

    def validate_mandatory_columns(df):
        """Validate that all mandatory columns exist and are not null"""
        
        # Strip whitespace from column names first
        df.columns = df.columns.str.strip()
        
        mandatory_cols = ['well_name', 'field', 'qi', 'di', 'b', 'eff_date', 'case_label', 
                        'dca_time', 'company_name', 'q_abandon', 'end_of_lease']
        
        # Debug: Show actual column names
        st.write("**Debug - Columns found in file:**", list(df.columns))
        
        missing_cols = [col for col in mandatory_cols if col not in df.columns]
        
        if missing_cols:
            return False, f"Missing mandatory columns: {', '.join(missing_cols)}"
        
        # Check for null values in mandatory columns
        for col in mandatory_cols:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                return False, f"Column '{col}' has {null_count} null values. All mandatory columns must be filled."
        
        return True, "Validation successful"

    def map_df_to_forecast_table(df, user_id):
        """Map DataFrame columns to forecast_cases table schema with user_id"""
        
        # Strip whitespace from column names
        df.columns = df.columns.str.strip()
        
        mapped_data = []
        
        for idx, row in df.iterrows():
            record = {}
                # Get well_type (default to 'existing' if not provided)
            if 'well_type' in df.columns and pd.notna(row['well_type']):
                well_type = str(row['well_type']).strip().lower()
            else:
                well_type = 'existing'
            
            # Get original case_label
            original_case_label = str(row['case_label']).strip()
        
        # Prepend well_type with underscore
        # Format: existing_Base Case  OR  new_Optimistic Case
            
            # Add user_id to record
            record['user_id'] = user_id
            
            # Map mandatory columns
            record['well_name'] = str(row['well_name']).strip()
            record['field'] = str(row['field']).strip()
            record['qi'] = float(row['qi'])
            record['di'] = float(row['di'])
            record['b'] = float(row['b'])
            record['eff_date'] = pd.to_datetime(row['eff_date']).strftime('%Y-%m-%d') if pd.notna(row['eff_date']) else None
            record['case_label'] = f"{well_type}_{original_case_label}"
            record['dca_time'] = str(row['dca_time']).strip().lower()
            record['company_name'] = str(row['company_name']).strip()
            record['q_abandon'] = float(row['q_abandon'])
            record['end_of_lease'] = pd.to_datetime(row['end_of_lease']).strftime('%Y-%m-%d') if pd.notna(row['end_of_lease']) else '2039-12-31'
            
            # Handle ti_selected
            if 'ti_selected' in df.columns and pd.notna(row['ti_selected']):
                record['ti_selected'] = pd.to_datetime(row['ti_selected']).strftime('%Y-%m-%d')
            else:
                record['ti_selected'] = record['eff_date']
            
            # Set selection_type and entity_identifier automatically
            record['selection_type'] = 'well'
            record['entity_identifier'] = str(row['well_name']).strip()
            
            # Optional columns with defaults
            if 'qi_regressed' in df.columns and pd.notna(row['qi_regressed']):
                record['qi_regressed'] = float(row['qi_regressed'])
            else:
                record['qi_regressed'] = float(row['qi'])
            
            
            record['well_type'] = str(row['well_type']).strip().lower()
            
            mapped_data.append(record)
        
        return mapped_data
    
    def bulk_insert_cases(mapped_records):
        """Bulk insert forecast cases with user_id"""
        success_count = 0
        error_count = 0
        errors = []
        
        conn = None
        
        try:
            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
            cursor = conn.cursor()
            
            for idx, record in enumerate(mapped_records):
                try:
                    cursor.execute("""
                        INSERT INTO forecast_cases (
                            user_id, well_name, field, qi, di, b, eff_date, case_label,
                            dca_time, company_name, q_abandon, end_of_lease,
                            ti_selected, selection_type, entity_identifier,
                            qi_regressed, well_type
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        record['user_id'],
                        record['well_name'],
                        record['field'],
                        record['qi'],
                        record['di'],
                        record['b'],
                        record['eff_date'],
                        record['case_label'],
                        record['dca_time'],
                        record['company_name'],
                        record['q_abandon'],
                        record['end_of_lease'],
                        record['ti_selected'],
                        record['selection_type'],
                        record['entity_identifier'],
                        record['qi_regressed'],
                        record['well_type']
                    ))
                    
                    success_count += 1
                    
                except sqlite3.IntegrityError as e:
                    error_count += 1
                    errors.append(f"Row {idx + 1} ({record.get('well_name', 'Unknown')}): {str(e)}")
                
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {idx + 1} ({record.get('well_name', 'Unknown')}): {str(e)}")
            
            conn.commit()
            
        except Exception as e:
            error_count = len(mapped_records)
            success_count = 0
            errors.append(f"Database error: {str(e)}")
            if conn:
                conn.rollback()
        
        finally:
            if conn:
                conn.close()
        
        return success_count, error_count, errors

    def render_create_section():
        """Render CREATE section with user_id and template download"""
        st.markdown('<h3 class="section-header">📥 CREATE - Bulk Import Cases</h3>', unsafe_allow_html=True)
        
        st.markdown(f'''
        <div class="info-box">
            <strong>👤 Importing as:</strong> {username} (User ID: {user_id})<br>
            <strong>Upload your cases from Excel:</strong><br>
            <strong>Mandatory columns:</strong> well_name, case_label, field, qi, di, b, eff_date, 
            dca_time (monthly/daily), company_name, q_abandon, end_of_lease<br>
            <strong>Optional columns:</strong> ti_selected, qi_regressed, well_type (existing/new)<br>
            <strong>Auto-set columns:</strong> selection_type='well', entity_identifier=well_name, user_id={user_id}
        </div>
        ''', unsafe_allow_html=True)
        
        # ========== TEMPLATE DOWNLOAD SECTION ==========
        st.markdown("### 📄 Download Template")
        
        # Create template DataFrame
        template_data = {
            'well_name': ['WELL-001', 'WELL-002', 'WELL-003'],
            'case_label': ['Base Case', 'Base Case', 'Optimistic Case'],
            'field': ['Field A', 'Field A', 'Field B'],
            'qi': [1500.0, 2000.0, 1800.0],
            'di': [0.15, 0.12, 0.18],
            'b': [0.5, 0.6, 0.45],
            'eff_date': ['2024-01-01', '2024-01-01', '2024-02-01'],
            'dca_time': ['monthly', 'monthly', 'daily'],
            'company_name': ['Alamein', 'Petrosila', 'Alamein'],
            'q_abandon': [300.0, 300.0, 250.0],
            'end_of_lease': ['2039-12-31', '2039-12-31', '2040-12-31'],
            'ti_selected': ['2023-06-01', '2023-06-01', '2023-12-01'],
            'qi_regressed': [1500.0, 2000.0, 1800.0],
            'well_type': ['existing', 'existing', 'new']
        }
        
        template_df = pd.DataFrame(template_data)
        
        # Convert to CSV
        csv_template = template_df.to_csv(index=False)
        
        col_template1, col_template2, col_template3 = st.columns([1, 2, 1])
        
        with col_template2:
            st.download_button(
                label="📥 Download CSV Template",
                data=csv_template,
                file_name="forecast_cases_template.csv",
                mime="text/csv",
                help="Download this template, fill it with your data, and upload below",
                use_container_width=True,
                type="secondary"
            )
        
        st.markdown("---")
        
        # ========== FILE UPLOAD SECTION ==========
        st.markdown("### 📤 Upload Your Data")
        
        uploaded_file = st.file_uploader(
            "Upload Excel or CSV File (.xlsx, .xls, .csv)",
            type=['xlsx', 'xls', 'csv'],
            key="crud_upload_excel"
        )
        
        if uploaded_file:
            try:
                # Read file based on extension
                file_extension = uploaded_file.name.split('.')[-1].lower()
                
                if file_extension == 'csv':
                    df_uploaded = pd.read_csv(uploaded_file)
                else:
                    df_uploaded = pd.read_excel(uploaded_file)
                
                df_uploaded.columns = df_uploaded.columns.str.strip()
                
                st.success(f"✅ File uploaded successfully! Found {len(df_uploaded)} rows.")
                
                with st.expander("📋 View Column Information"):
                    st.write("**Columns found:**", list(df_uploaded.columns))
                    st.info(f"✅ user_id={user_id} will be added automatically to all records")
                    st.info("✅ selection_type='well' and entity_identifier=well_name set automatically")
                
                st.markdown("### 📝 Review & Edit Data Before Import")
                
                edited_df = st.data_editor(
                    df_uploaded,
                    use_container_width=True,
                    num_rows="dynamic",
                    key="crud_data_editor",
                    height=400
                )
                
                edited_df.columns = edited_df.columns.str.strip()
                
                is_valid, validation_msg = validate_mandatory_columns(edited_df)
                
                if is_valid:
                    st.success(f"✅ {validation_msg}")
                    
                    with st.expander("👀 Preview Mapped Data (First 5 records)"):
                        preview_records = map_df_to_forecast_table(edited_df.head(5), user_id)
                        st.json(preview_records)
                    
                    col_import1, col_import2, col_import3 = st.columns([2, 1, 2])
                    
                    with col_import2:
                        if st.button("🚀 Import to Database", type="primary", use_container_width=True, key="import_btn"):
                            with st.spinner("Importing data..."):
                                mapped_records = map_df_to_forecast_table(edited_df, user_id)
                                success_count, error_count, errors = bulk_insert_cases(mapped_records)
                                
                                if error_count == 0:
                                    st.success(f"🎉 Successfully imported {success_count} cases for user {username}!")
                                    
                                else:
                                    st.warning(f"⚠️ Imported {success_count} cases. {error_count} failed.")
                                    with st.expander("View Errors"):
                                        for error in errors:
                                            st.error(error)
                else:
                    st.error(f"❌ {validation_msg}")
            
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    def render_read_section():
        """Render READ section - only show current user's cases"""
        st.markdown('<h3 class="section-header">📊 READ - View Your Cases</h3>', unsafe_allow_html=True)
        
        st.info(f"👤 Showing cases for: **{username}** (User ID: {user_id})")
        
        # Load only current user's cases
        cases_df = DatabaseManager.load_forecast_cases()
        
        if cases_df.empty:
            st.info(f"No cases found for user {username}.")
            return
        
        st.success(f"Found {len(cases_df)} records for user {username}")
        
        # Filters
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            filter_company = st.multiselect(
                "Filter by Company:",
                options=cases_df['company_name'].unique().tolist(),
                key="read_filter_company"
            )
        
        with col_filter2:
            filter_field = st.multiselect(
                "Filter by Field:",
                options=cases_df['field'].dropna().unique().tolist(),
                key="read_filter_field"
            )
        
        with col_filter3:
            filter_case = st.multiselect(
                "Filter by Case Label:",
                options=cases_df['case_label'].unique().tolist(),
                key="read_filter_case"
            )
        
        # Apply filters
        filtered_df = cases_df.copy()
        
        if filter_company:
            filtered_df = filtered_df[filtered_df['company_name'].isin(filter_company)]
        if filter_field:
            filtered_df = filtered_df[filtered_df['field'].isin(filter_field)]
        if filter_case:
            filtered_df = filtered_df[filtered_df['case_label'].isin(filter_case)]
        
        st.markdown(f"**Showing {len(filtered_df)} of {len(cases_df)} records**")
        
        # Display data
        st.dataframe(
            filtered_df,
            use_container_width=True,
            height=500
        )
        
        # Export
        st.download_button(
            label="📥 Export Your Data to CSV",
            data=filtered_df.to_csv(index=False).encode('utf-8'),
            file_name=f"{username}_forecast_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    
    def render_update_section():
        """Render UPDATE section with data editor - only user's own cases"""
        st.markdown('<h3 class="section-header">✏️ UPDATE - Modify Your Cases</h3>', unsafe_allow_html=True)
        
        st.info(f"👤 Updating cases for: **{username}** (User ID: {user_id})")
        
        st.markdown('''
        <div class="warning-box">
            <strong>⚠️ Safety Notice:</strong> Updates will modify the database directly. 
            Review your changes carefully before saving.
        </div>
        ''', unsafe_allow_html=True)
        
        # Load only current user's cases
        cases_df = DatabaseManager.load_forecast_cases()
        
        if cases_df.empty:
            st.info(f"No cases available to update for user {username}.")
            return
        
        st.success(f"Found {len(cases_df)} records for user {username}")
        
        # ========== FILTERS (Same as READ section) ==========
        st.markdown("### 🔍 Filter Your Data")
        
        col_filter1, col_filter2, col_filter3 = st.columns(3)
        
        with col_filter1:
            filter_company = st.multiselect(
                "Filter by Company:",
                options=cases_df['company_name'].unique().tolist(),
                key="update_filter_company"
            )
        
        with col_filter2:
            filter_field = st.multiselect(
                "Filter by Field:",
                options=cases_df['field'].dropna().unique().tolist(),
                key="update_filter_field"
            )
        
        with col_filter3:
            filter_case = st.multiselect(
                "Filter by Case Label:",
                options=cases_df['case_label'].unique().tolist(),
                key="update_filter_case"
            )
        
        # Apply filters
        filtered_df = cases_df.copy()
        
        if filter_company:
            filtered_df = filtered_df[filtered_df['company_name'].isin(filter_company)]
        if filter_field:
            filtered_df = filtered_df[filtered_df['field'].isin(filter_field)]
        if filter_case:
            filtered_df = filtered_df[filtered_df['case_label'].isin(filter_case)]
        
        st.markdown(f"**Showing {len(filtered_df)} of {len(cases_df)} records**")
        
        if filtered_df.empty:
            st.warning("No records match your filters.")
            return
        
        st.markdown("---")
        
        # ========== DATA EDITOR ==========
        st.markdown("### 📝 Edit Your Data")
        
        st.info("💡 **Tip:** You can edit any cell directly. Changes are highlighted. Click 'Save Changes' when done.")
        
        # Define which columns are editable
        # Make user_id read-only, allow editing of data columns
        # Convert date columns to pandas.Timestamp for st.data_editor
        for col in ['eff_date', 'ti_selected', 'end_of_lease']:
            filtered_df[col] = pd.to_datetime(filtered_df[col], errors='coerce')
        column_config = {
            "user_id": st.column_config.NumberColumn("User ID", disabled=True, help="Your user ID (read-only)"),
            "well_name": st.column_config.TextColumn("Well Name", required=True, help="Name of the well"),
            "case_label": st.column_config.TextColumn("Case Label", required=True, help="Case label (e.g., existing_Base Case)"),
            "field": st.column_config.TextColumn("Field", help="Field name"),
            "qi": st.column_config.NumberColumn("Qi", required=True, format="%.2f", help="Initial rate"),
            "di": st.column_config.NumberColumn("Di", required=True, format="%.4f", help="Decline rate"),
            "b": st.column_config.NumberColumn("b", required=True, format="%.2f", help="Hyperbolic factor"),
            "eff_date": st.column_config.DateColumn("Eff Date", required=True, help="Effective date"),
            "ti_selected": st.column_config.DateColumn("Ti Selected", help="History start date"),
            "dca_time": st.column_config.SelectboxColumn("DCA Time", options=['monthly', 'daily'], required=True),
            "company_name": st.column_config.SelectboxColumn("Company", options=['Alamein', 'Petrosila'], required=True),
            "q_abandon": st.column_config.NumberColumn("Q Abandon", format="%.2f"),
            "end_of_lease": st.column_config.DateColumn("End of Lease"),
            "qi_regressed": st.column_config.NumberColumn("Qi Regressed", format="%.2f"),
            "well_type": st.column_config.SelectboxColumn("Well Type", options=['existing', 'new']),
            "selection_type": st.column_config.TextColumn("Selection Type", disabled=True),
            "entity_identifier": st.column_config.TextColumn("Entity ID", disabled=True)
        }
        update_user_id = int(user_id) if not isinstance(user_id, int) else user_id
        
        # Data editor with all columns
        edited_df = st.data_editor(
            filtered_df,
            use_container_width=True,
            num_rows="fixed",  # Don't allow adding/deleting rows
            column_config=column_config,
            key="update_data_editor",
            height=500,
            hide_index=True
        )
        
        # ========== DETECT CHANGES ==========
        # ========== DETECT CHANGES ==========
        # Compare original and edited dataframes
        changes_detected = not filtered_df.equals(edited_df)

        if changes_detected:
            st.warning("⚠️ You have unsaved changes!")
            
            # Show what changed
            with st.expander("📋 View Changes"):
                # Find rows that changed
                changed_rows = []
                
                for idx in filtered_df.index:
                    if idx in edited_df.index:
                        original_row = filtered_df.loc[idx]
                        edited_row = edited_df.loc[idx]
                        
                        # Check if any value changed
                        if not original_row.equals(edited_row):
                            changes = {}
                            for col in filtered_df.columns:
                                if original_row[col] != edited_row[col]:
                                    changes[col] = {
                                        'old': original_row[col],
                                        'new': edited_row[col]
                                    }
                            
                            if changes:
                                changed_rows.append({
                                    'index': idx,  # STORE THE INDEX
                                    'well_name': original_row['well_name'],
                                    'case_label': original_row['case_label'],
                                    'entity_identifier': original_row['entity_identifier'],
                                    'changes': changes
                                })
                
                if changed_rows:
                    st.write(f"**{len(changed_rows)} record(s) modified:**")
                    for change in changed_rows:
                        st.write(f"**{change['well_name']}** (Case: {change['case_label']})")
                        for field, values in change['changes'].items():
                            st.write(f"  - {field}: `{values['old']}` → `{values['new']}`")
            
            # ========== SAVE BUTTON ==========
            st.markdown("---")
            
            col_save1, col_save2, col_save3 = st.columns([2, 1, 2])
            
            with col_save2:
                if st.button("💾 Save Changes", type="primary", use_container_width=True, key="save_updates_btn"):
                    with st.spinner("Saving changes to database..."):
                        success_count = 0
                        error_count = 0
                        errors = []
                        
                        try:
                            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
                            cursor = conn.cursor()
                            
                            # Update each changed row
                            for change in changed_rows:
                                try:
                                    # USE THE INDEX TO GET THE EDITED ROW
                                    edited_row = edited_df.loc[change['index']]
                                    original_case_label = change['case_label']
                                    original_entity_identifier = change['entity_identifier']
                                    
                                    # Convert dates to strings for SQL
                                    eff_date = edited_row['eff_date'].strftime('%Y-%m-%d') if pd.notna(edited_row['eff_date']) else None
                                    ti_selected = edited_row['ti_selected'].strftime('%Y-%m-%d') if pd.notna(edited_row['ti_selected']) else None
                                    end_of_lease = edited_row['end_of_lease'].strftime('%Y-%m-%d') if pd.notna(edited_row['end_of_lease']) else '2039-12-31'
                                    
                                    # UPDATE query using ORIGINAL identifiers
                                    cursor.execute("""
                                        UPDATE forecast_cases
                                        SET well_name = ?,
                                            case_label = ?,
                                            field = ?,
                                            qi = ?,
                                            di = ?,
                                            b = ?,
                                            eff_date = ?,
                                            ti_selected = ?,
                                            dca_time = ?,
                                            company_name = ?,
                                            q_abandon = ?,
                                            end_of_lease = ?,
                                            qi_regressed = ?,
                                            well_type = ?,
                                            selection_type = ?,
                                            entity_identifier = ?
                                        WHERE case_label = ? AND entity_identifier = ? AND user_id = ?
                                    """, (
                                        str(edited_row['well_name']),
                                        str(edited_row['case_label']),
                                        str(edited_row['field']) if pd.notna(edited_row['field']) else None,
                                        float(edited_row['qi']),
                                        float(edited_row['di']),
                                        float(edited_row['b']),
                                        eff_date,
                                        ti_selected,
                                        str(edited_row['dca_time']),
                                        str(edited_row['company_name']),
                                        float(edited_row['q_abandon']) if pd.notna(edited_row['q_abandon']) else 300.0,
                                        end_of_lease,
                                        float(edited_row['qi_regressed']) if pd.notna(edited_row['qi_regressed']) else float(edited_row['qi']),
                                        str(edited_row['well_type']) if pd.notna(edited_row['well_type']) else 'existing',
                                        str(edited_row['selection_type']),
                                        str(edited_row['entity_identifier']),
                                        original_case_label,  # USE ORIGINAL VALUE FOR WHERE CLAUSE
                                        original_entity_identifier,  # USE ORIGINAL VALUE FOR WHERE CLAUSE
                                        update_user_id
                                    ))
                                    
                                    success_count += 1
                                
                                except Exception as e:
                                    error_count += 1
                                    errors.append(f"Row {change['well_name']} (Case: {change['case_label']}): {str(e)}")
                            
                            conn.commit()
                            conn.close()
                            
                            # Show results
                            if error_count == 0:
                                st.success(f"🎉 Successfully updated {success_count} record(s)!")
                                
                            else:
                                st.warning(f"⚠️ Updated {success_count} record(s). {error_count} failed.")
                                with st.expander("View Errors"):
                                    for error in errors:
                                        st.error(error)
                        
                        except Exception as e:
                            st.error(f"❌ Database error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())

        else:
            st.info("ℹ️ No changes detected. Edit the data above to make updates.")
    def render_delete_section():
        """Render DELETE section - only user's own cases"""
        st.markdown('<h3 class="section-header">🗑️ DELETE - Remove Your Cases</h3>', unsafe_allow_html=True)
        
        st.info(f"👤 Deleting cases for: **{username}** (User ID: {user_id})")
        
        st.markdown('''
        <div class="danger-zone">
            <div class="danger-zone-header">⚠️ DANGER ZONE ⚠️</div>
            <div class="delete-confirm-box">
                <strong>CRITICAL WARNING:</strong> 
                Deletion is permanent and cannot be undone!
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
        # Load only current user's cases
        cases_df = DatabaseManager.load_forecast_cases()
        
        if cases_df.empty:
            st.info(f"No cases available to delete for user {username}.")
            return
        
        deletion_type = st.radio(
            "Select Deletion Type:",
            options=["Delete Entire Case", "Delete Specific Item in Case"],
            key="delete_type_radio"
        )
        
        if deletion_type == "Delete Entire Case":
            case_label = st.selectbox(
                "Select Your Case to Delete:",
                options=cases_df['case_label'].unique().tolist(),
                key="delete_case_select"
            )
            
            if case_label:
                case_data = cases_df[cases_df['case_label'] == case_label]
                st.warning(f"⚠️ This will delete {len(case_data)} record(s)")
                
                confirm_text = st.text_input(f"Type '{case_label}' to confirm:", key="delete_case_confirm")
                
                if st.button("🗑️ DELETE CASE", type="primary", disabled=(confirm_text != case_label), key="delete_case_btn"):
                    try:
                            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM forecast_cases WHERE case_label = ?  AND user_id = ?",
                                (case_label,  user_id)
                            )
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Deleted {case_label}")
                            
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        else:  # Delete Specific Item
            case_label = st.selectbox(
                "Select Case:",
                options=cases_df['case_label'].unique().tolist(),
                key="delete_item_case_select"
            )
            
            if case_label:
                case_data = cases_df[cases_df['case_label'] == case_label]
                
                if len(case_data) == 1:
                    st.info("This case has only one item. Use 'Delete Entire Case' instead.")
                else:
                    well_name = st.selectbox("Select Item:", options=case_data['well_name'].tolist(), key="delete_item_well_select")
                    item_data = case_data[case_data['well_name'] == well_name].iloc[0]
                    
                    confirm_checkbox = st.checkbox(f"I confirm deletion of {well_name}", key="delete_item_confirm")
                    
                    if st.button("🗑️ DELETE ITEM", type="primary", disabled=not confirm_checkbox, key="delete_item_btn"):
                        try:
                            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM forecast_cases WHERE case_label = ? AND well_name = ? AND user_id = ?",
                                (case_label, well_name, user_id)
                            )
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ Deleted {well_name}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")

    # =================== MAIN RENDER ===================
    st.markdown('<h2 class="section-header">🛠️ Database CRUD Operations</h2>', unsafe_allow_html=True)

    st.markdown(f'''
    <div class="info-box">
        <strong>👤 Current User:</strong> {username} (ID: {user_id})<br>
        <strong>Access:</strong> You can only view and modify YOUR OWN forecast cases.
    </div>
    ''', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📥 CREATE", "📊 READ", "✏️ UPDATE", "🗑️ DELETE"])

    with tab1:
        render_create_section()
    with tab2:
        render_read_section()
    with tab3:
        render_update_section()
    with tab4:
        render_delete_section()


# =================== IMPORT FROM CASE TAB ===================
def render_import_from_case():
    st.markdown('<h2 class="section-header">Import from Case Dashboard</h2>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Select an existing case to duplicate, edit parameters, and save as a new case</div>', unsafe_allow_html=True)
    
    if AuthManager.is_logged_in():
        user_id, username = AuthManager.get_current_user()
        with st.sidebar:
            st.markdown(f"### 👤 User: **{username}**")
            st.markdown(f"🆔 ID: `{user_id}`")
            st.markdown("---")
            if st.button("🚪 Logout", use_container_width=True):
                AuthManager.logout()
        
        # Load all forecast cases with user names and case_id
        try:
            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
            query = """
                SELECT fc.*, u.user_name
                FROM forecast_cases fc
                JOIN users u ON fc.user_id = u.user_id
				
                
            """
            cases_df = pd.read_sql(query, conn)
            conn.close()
           
        except Exception as e:
            st.error(f"Error loading cases: {e}")
            cases_df = pd.DataFrame()
        
        if cases_df.empty:
            st.warning("No forecast cases available.")
            return
        
        # Get unique user_id and user_name pairs
        unique_users = cases_df[['user_id', 'user_name']].drop_duplicates()
        
        # Layout with columns for two select boxes
        col1, col2 = st.columns([3, 1])
        
        with col1:
            selected_user_name = st.selectbox(
                "Select User:",
                options=unique_users['user_name'].tolist(),
                key="import_user_select"
            )
        
        with col2:
            # Filter case_labels based on selected user
            selected_user_id = unique_users[unique_users['user_name'] == selected_user_name]['user_id'].iloc[0]
            filtered_cases = cases_df[cases_df['user_id'] == selected_user_id][['user_id', 'case_label']].drop_duplicates()
            
            selected_case_label = st.selectbox(
                "Select Case to Duplicate:",
                options=filtered_cases['case_label'].tolist(),
                key="import_case_select"
            )
        
        if selected_case_label:
            # Get the case_id and user_id for the selected case_label
           
            case_info = filtered_cases[filtered_cases['case_label'] == selected_case_label].iloc[0]
            
            selected_case_id = case_info['user_id']
            
            
            # Load all rows for the selected case_id and user_id
            case_data = cases_df[(cases_df['case_label'] == selected_case_label) & (cases_df['user_id'] == selected_user_id)].copy()
            st.write("edited_data", case_data)
            
            # Input for new case name
            st.markdown("---")
            st.markdown('<h3 class="section-header">New Case Details</h3>', unsafe_allow_html=True)
            col_name1, col_name2 = st.columns([3, 1])
            with col_name1:
                new_case_label = st.text_input(
                    "New Case Label:",
                    value=f"Copy_of_{selected_case_label}_{datetime.now()}",
                    key="new_case_label"
                )
            
            # Prepare editable data for all rows
            editable_columns = [
                'well_name', 'selection_type', 'entity_identifier', 'field', 'eff_date',
                'qi', 'di', 'b', 'qi_regressed', 'ti_selected', 'q_abandon', 'end_of_lease',
                'well_type', 'dca_time', 'company_name'
            ]
            edit_df = case_data[editable_columns].copy()
            
            # Convert date columns to pandas.Timestamp for st.data_editor
            for col in ['eff_date', 'ti_selected', 'end_of_lease']:
                edit_df[col] = pd.to_datetime(edit_df[col], errors='coerce')
            
            # Display data editor for all rows
            st.markdown('<h3 class="section-header">Edit Case Parameters</h3>', unsafe_allow_html=True)
            edited_data = st.data_editor(
                edit_df,
                use_container_width=True,
                column_config={
                    'well_name': st.column_config.TextColumn("Well Name", width="medium"),
                    'selection_type': st.column_config.TextColumn("Selection Type", width="small"),
                    'entity_identifier': st.column_config.TextColumn("Entity Identifier", width="medium"),
                    'field': st.column_config.TextColumn("Field", width="small"),
                    'eff_date': st.column_config.DateColumn("Effective Date", format="YYYY-MM-DD"),
                    'qi': st.column_config.NumberColumn("Qi (bbl/day or bbl/month)", min_value=0.0, step=0.01),
                    'di': st.column_config.NumberColumn("Di (fraction)", min_value=0.0, max_value=1.0, step=0.0001),
                    'b': st.column_config.NumberColumn("b (Arps)", min_value=0.0, max_value=2.0, step=0.001),
                    'qi_regressed': st.column_config.NumberColumn("Qi Regressed", min_value=0.0, step=0.01),
                    'ti_selected': st.column_config.DateColumn("Ti Selected", format="YYYY-MM-DD"),
                    'q_abandon': st.column_config.NumberColumn("Q Abandon", min_value=0.0, step=0.01),
                    'end_of_lease': st.column_config.DateColumn("End of Lease", format="YYYY-MM-DD"),
                    'well_type': st.column_config.TextColumn("Well Type", width="small"),
                    'dca_time': st.column_config.TextColumn("DCA Time", width="small"),
                    'company_name': st.column_config.TextColumn("Company Name", width="small")
                }
            )
            
            # Save all edited rows as new cases
            if st.button("Create New Case", type="primary", use_container_width=True):
                if not new_case_label.strip():
                    st.error("New case label cannot be empty.")
                    return
                
                save_progress = st.progress(0)
                save_status = st.empty()
                saved_count = 0
                failed_count = 0
                error_messages = []
                
                if edited_data.empty:
                    st.error("No data to save.")
                    return
                
                for idx, row in edited_data.iterrows():
                    progress_value = min((idx + 1) / len(edited_data), 1.0)
                    save_status.text(f"Saving {idx + 1}/{len(edited_data)}: {row['well_name']}")
                    save_progress.progress(progress_value)
                    st.write(f"Debug: idx={idx}, len={len(edited_data)}, progress={progress_value}")  # Debug output
                    
                    # Convert dates to strings for SQLite3 TEXT columns
                    eff_date_str = row['eff_date'].strftime('%Y-%m-%d') if pd.notnull(row['eff_date']) else None
                    ti_selected_str = row['ti_selected'].strftime('%Y-%m-%d') if pd.notnull(row['ti_selected']) else None
                    end_of_lease_str = row['end_of_lease'].strftime('%Y-%m-%d') if pd.notnull(row['end_of_lease']) else None
                    
                    try:
                        success = DatabaseManager.save_forecast_case_aggregate(
                            well_name=row['well_name'],
                            case_label=new_case_label.strip(),
                            selection_type=row['selection_type'],
                            entity_identifier=row['entity_identifier'],
                            field=row['field'],
                            eff_date=eff_date_str,
                            qi=float(row['qi']),
                            di=float(row['di']),
                            b=float(row['b']),
                            qi_regressed=float(row['qi_regressed']) if pd.notnull(row['qi_regressed']) else None,
                            ti_selected=ti_selected_str,
                            q_abandon=float(row['q_abandon']),
                            end_of_lease=end_of_lease_str,
                            well_type=row['well_type'],
                            dca_time=row['dca_time'],
                            company_name=row['company_name'],
                            user_id=user_id
                        )
                        if success:
                            saved_count += 1
                        else:
                            failed_count += 1
                            error_messages.append(f"Failed to save {row['well_name']}")
                    except Exception as e:
                        failed_count += 1
                        error_messages.append(f"Error saving {row['well_name']}: {str(e)}")
                
                save_progress.empty()
                save_status.empty()
                
                if failed_count == 0:
                    st.success(f"Successfully saved all {saved_count} cases to database!")
                    st.session_state.pop('import_user_select', None)
                    st.session_state.pop('import_case_select', None)  # Clear selections
                    st.rerun()
                else:
                    st.warning(f"Saved {saved_count}/{len(edited_data)} cases. {failed_count} failed.")
                    with st.expander("View Errors"):
                        for msg in error_messages:
                            st.error(msg)
    else:
        st.error("You must be logged in to access this feature.")
        st.markdown("[Go to Login](#)", unsafe_allow_html=True)