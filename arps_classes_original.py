import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date, datetime
import plotly.graph_objs as go
import plotly.express as px
from scipy.optimize import curve_fit
import os
import calendar
from datetime import datetime
from dateutil.relativedelta import relativedelta
from utils.login_panel import AuthManager
from pathlib import Path


class Config:
    """Application configuration"""
    MAIN_DB_PATH = Path(__file__).parent.parent / "data" / "alamein_db.sqlite3"
    FORECAST_DB_PATH = Path(__file__).parent.parent / "my_pages" / "trial.db"
    PETROSILA_DB_PATH = Path(__file__).parent.parent / "data" / "petrosila.db"
    DEFAULT_ABANDONMENT_RATE_MONTHLY = 300.00
    DEFAULT_ABANDONMENT_RATE_DAILY = 10.0
    DEFAULT_FORECAST_END_DATE = date(2040, 1, 1)


# =================== DATABASE UTILITIES ===================
class DatabaseManager:
    """Centralized database management"""
    
    @staticmethod
    def get_connection(db_path: str):
        """Create database connection with proper settings"""
        return sqlite3.connect(db_path, timeout=30.0)
    
    @staticmethod
    @st.cache_resource
    def load_production_data(company: str = "Alamein", dca_time: str = "monthly") -> pd.DataFrame:
        """Load ALL production data for a company - no filtering"""
        if company == "Alamein":
            conn = DatabaseManager.get_connection(Config.MAIN_DB_PATH)
            if dca_time == "daily":
                query = "SELECT unique_id, date, net, field, reservoir AS zone, well_bore FROM st_data_plot"
            else:
                query = "SELECT unique_id, date, net_oil AS net, field, reservoir AS zone, well_bore FROM monthly_data"
        else:  # Petrosila
            conn = DatabaseManager.get_connection(Config.PETROSILA_DB_PATH)
            query = "SELECT date, unique_id, net, field, zone, well_bore FROM st_data"
        
        try:
            df = pd.read_sql_query(query, conn)
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df.dropna(subset=['date']).sort_values('date')
            return df
        except Exception as e:
            st.error(f"Error loading production data: {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    @staticmethod
    def load_production_data_by_selection(selection_type: str, entity_identifier: str, 
                                         company: str = "Alamein", dca_time: str = "monthly") -> pd.DataFrame:
        """Load production data based on selection type and entity identifier"""
        
        # Build base query
        if company == "Alamein":
            conn = DatabaseManager.get_connection(Config.MAIN_DB_PATH)
            if dca_time == "daily":
                base_query = "SELECT unique_id, date, net, field, reservoir AS zone, well_bore FROM st_data_plot"
            else:
                base_query = "SELECT unique_id, date, net_oil AS net, field, reservoir AS zone, well_bore FROM monthly_data"
        else:  # Petrosila
            conn = DatabaseManager.get_connection(Config.PETROSILA_DB_PATH)
            base_query = "SELECT date, unique_id, net, field, zone, well_bore FROM st_data"
        
        # Add WHERE clause based on selection_type
        where_clause = ""
        
        if selection_type == "well":
            # Single well
            where_clause = f" WHERE unique_id = '{entity_identifier}'"
        
        elif selection_type == "multi_well":
            # Multiple wells - split by pipe separator
            wells = entity_identifier.split("|")
            wells_quoted = "', '".join(wells)
            where_clause = f" WHERE unique_id IN ('{wells_quoted}')"
        
        elif selection_type == "field":
            # Single field
            where_clause = f" WHERE field = '{entity_identifier}'"
        
        elif selection_type == "multi_field":
            # Multiple fields - split by pipe separator
            fields = entity_identifier.split("|")
            fields_quoted = "', '".join(fields)
            where_clause = f" WHERE field IN ('{fields_quoted}')"
        
        elif selection_type == "company":
            # Load all company data - no WHERE clause
            where_clause = ""
        
        else:
            st.warning(f"Unknown selection_type: {selection_type}. Loading all data.")
            where_clause = ""
        
        query = base_query + where_clause
        
        try:
            df = pd.read_sql_query(query, conn)
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df.dropna(subset=['date']).sort_values('date')
            return df
        except Exception as e:
            st.error(f"Error loading production data: {e}")
            st.error(f"Query: {query}")
            return pd.DataFrame()
        finally:
            conn.close()
    
    @staticmethod
    def load_forecast_cases() -> pd.DataFrame:
        """Load existing forecast cases for the logged-in user"""
        if not AuthManager.is_logged_in():
            st.error("You must be logged in to load forecast cases.")
            return pd.DataFrame()
        
        user_id, _ = AuthManager.get_current_user()
        try:
            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
            try:
                query = """
                    SELECT * FROM forecast_cases 
                    WHERE user_id = ? 
                    ORDER BY eff_date DESC, case_id DESC
                """
                return pd.read_sql(query, conn, params=(user_id,))
            finally:
                conn.close()
        except sqlite3.Error as e:
            st.error(f"Database error: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def load_unique_fields() -> pd.DataFrame:
        """Load unique fields from both databases"""
        try:
            conn1 = DatabaseManager.get_connection(Config.MAIN_DB_PATH)
            conn2 = DatabaseManager.get_connection(Config.PETROSILA_DB_PATH)
            try:
                df1 = pd.read_sql("SELECT DISTINCT field FROM header_id", conn1)
                df2 = pd.read_sql("SELECT DISTINCT field FROM header_id", conn2)
                final_df = pd.concat([df1, df2], ignore_index=True).drop_duplicates().reset_index(drop=True)
                return final_df
            finally:
                conn1.close()
                conn2.close()
        except Exception as e:
            st.error(f"Error loading unique fields: {e}")
            return pd.DataFrame()
    
    @staticmethod
    def save_forecast_case_aggregate(
        well_name: str,
        case_label: str,
        selection_type: str,
        entity_identifier: str,
        eff_date: date,
        qi: float,
        di: float,
        b: float,
        qi_regressed: float,
        ti_selected: date,
        q_abandon: float,
        end_of_lease: str,
        well_type: str = "existing",
        field: str = None,
        dca_time: str = "monthly",
        company_name: str = "Alamein",
        user_id: int = None  # Added optional user_id parameter
    ) -> bool:
        """Save a forecast case with selection metadata including q_abandon, end_of_lease, and user_id"""
        # Get user_id from session state if not provided
        if user_id is None and AuthManager.is_logged_in():
            user_id, _ = AuthManager.get_current_user()
        
        try:
            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
            try:
                conn.execute("""
                    INSERT INTO forecast_cases 
                    (well_name, case_label, selection_type, entity_identifier, field, eff_date, 
                    qi, di, b, qi_regressed, ti_selected, q_abandon, end_of_lease, well_type, 
                    dca_time, company_name, user_id, created_at) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (well_name, case_label, selection_type, entity_identifier, field, str(eff_date),
                    qi, di, b, qi_regressed, str(ti_selected), q_abandon, end_of_lease, well_type, 
                    dca_time, company_name, user_id))
                conn.commit()
                return True
            finally:
                conn.close()
        except sqlite3.Error as e:
            st.error(f"Database error: {e}")
            return False

    
    @staticmethod
    def update_forecast_case_aggregate(
        case_label: str,
        selection_type: str,
        entity_identifier: str,
        eff_date: date,
        qi: float,
        di: float,
        b: float,
        dca_time: str,
        q_abandon: float,
        end_of_lease: str,
        qi_regressed: float = None,
        ti_selected: date = None,
        company_name: str = "Alamein",
        user_id: int = None
    ) -> bool:
        """Update an existing forecast case including q_abandon, end_of_lease, and user_id"""
        if user_id is None and AuthManager.is_logged_in():
            user_id, _ = AuthManager.get_current_user()
        
        try:
            conn = DatabaseManager.get_connection(Config.FORECAST_DB_PATH)
            try:
                update_fields = [
                    "eff_date = ?",
                    "qi = ?",
                    "di = ?",
                    "b = ?",
                    "q_abandon = ?",
                    "end_of_lease = ?",
                    "dca_time = ?",
                    "company_name = ?",
                    "updated_at = datetime('now')"
                ]
                
                params = [str(eff_date), qi, di, b, q_abandon, end_of_lease, dca_time, company_name]
                
                if qi_regressed is not None:
                    update_fields.append("qi_regressed = ?")
                    params.append(qi_regressed)
                
                if ti_selected is not None:
                    update_fields.append("ti_selected = ?")
                    params.append(str(ti_selected))
                
                # WHERE clause includes user_id for security
                params.extend([case_label, selection_type, entity_identifier, user_id])
                
                query = f"""
                    UPDATE forecast_cases 
                    SET {', '.join(update_fields)}
                    WHERE case_label = ? AND selection_type = ? AND entity_identifier = ? AND user_id = ?
                """
                
                conn.execute(query, params)
                conn.commit()
                return True
                    
            finally:
                conn.close()
                
        except sqlite3.Error as e:
            st.error(f"Database error: {e}")
            return False

# =================== ARPS DECLINE MODELS ===================
class ARPSModel:
    """ARPS decline curve calculations"""
    
    @staticmethod
    def calculate_rate(t: np.ndarray, qi: float, di: float, b: float) -> np.ndarray:
        """Calculate rate using ARPS equation"""
        if b == 0:
            return qi * np.exp(-di * t)
        return qi / ((1 + b * di * t) ** (1 / b))
    
    @staticmethod
    def create_production_profile(start_date: date, end_date: date, 
                                qi: float, di: float, b: float, 
                                q_abandon: float, frequency: str = "MS") -> pd.DataFrame:
        """Create production profile using ARPS parameters"""
        dates = pd.date_range(start=start_date, end=end_date, freq=frequency)
        t = np.arange(1, len(dates) + 1)
        rates = ARPSModel.calculate_rate(t, qi, di, b)
        rates = np.asarray(rates, dtype=float)
        rates[rates < q_abandon] = np.nan
        df = pd.DataFrame({"date": dates, "rate": rates}).dropna()
        if not df.empty:
            df["cumulative"] = df["rate"].cumsum()
        return df
    
    @staticmethod
    def calculate_eur(production_df: pd.DataFrame, historical_cum: float = 0.0) -> float:
        """Calculate EUR from production profile"""
        if production_df.empty:
            return historical_cum
        forecast_eur = production_df["rate"].sum()
        return historical_cum + forecast_eur
    
    @staticmethod
    def fit_arps_parameters(time_data: np.ndarray, rate_data: np.ndarray) -> tuple:
        """Fit ARPS parameters to historical data"""
        def hyperbolic_decline(t, qi, di, b):
            if b == 0:
                return qi * np.exp(-di * t)
            return qi / ((1 + di * b * t) ** (1 / b))
        
        try:
            initial_guess = [np.mean(rate_data[-3:]), 0.1, 0.5]
            bounds = ([0, 0, 0], [750000, 1, 1])
            params, _ = curve_fit(hyperbolic_decline, time_data, rate_data, 
                                p0=initial_guess, bounds=bounds)
            return params
        except RuntimeError:
            return [0, 0, 0]

    @staticmethod
    def generate_history_match_profile(selected_data: pd.DataFrame, qi_fitted: float, 
                                    di_fitted: float, b_fitted: float) -> pd.DataFrame:
        """Generate ARPS profile using fitted parameters for history matching visualization"""
        if selected_data.empty:
            return pd.DataFrame()
        
        selected_data_sorted = selected_data.sort_values('date').reset_index(drop=True)
        time_data = np.arange(len(selected_data_sorted))
        
        if b_fitted == 0:
            rates = qi_fitted * np.exp(-di_fitted * time_data)
        else:
            rates = qi_fitted / ((1 + b_fitted * di_fitted * time_data) ** (1 / b_fitted))
        
        history_match_df = pd.DataFrame({
            'date': pd.to_datetime(selected_data_sorted['date']),
            'rate': rates
        })
        
        return history_match_df


# =================== DATA PROCESSING ===================
class DataProcessor:
    """Data filtering and processing utilities"""
    
    @staticmethod
    def apply_production_filters(df: pd.DataFrame, date_range: tuple, 
                            fields: list, unique_ids: list, zones: list) -> pd.DataFrame:
        """Apply filters to production data"""
        filtered_df = df[
            (df['date'] >= date_range[0]) & 
            (df['date'] <= date_range[1])
        ]
        
        if fields:
            filtered_df = filtered_df[filtered_df['field'].isin(fields)]
        if unique_ids:
            filtered_df = filtered_df[filtered_df['unique_id'].isin(unique_ids)]
        if zones:
            filtered_df = filtered_df[filtered_df['zone'].isin(zones)]
        
        return filtered_df.groupby('date')['net'].sum().reset_index()

    @staticmethod
    def normalize_to_monthly(df):
        """Convert daily profile to monthly totals by summing daily rates."""
        if df.empty or "Date" not in df.columns or "rate" not in df.columns:
            return df
        
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        
        monthly_df = df.groupby(pd.Grouper(key="Date", freq="MS")).agg({"rate": "sum", "cumulative": "last"}).reset_index()
        
        for col in df.columns:
            if col not in ["Date", "rate", "cumulative"]:
                monthly_df[col] = df[col].iloc[0]
        
        monthly_df["dca_time"] = "monthly"
        return monthly_df


# =================== VISUALIZATION ===================
class PlotManager:
    """Professional plotting utilities"""
    
    @staticmethod
    def create_production_scatter(df: pd.DataFrame, title: str, enable_selection: bool = True, unit: str = "bbl/month") -> go.Figure:
        """Create interactive production scatter plot"""
        fig = px.scatter(
            df, x="date", y="net",
            title=title,
            labels={"date": "Date", "net": f"Net Oil ({unit})"},
            color_discrete_sequence=["#00CC96"]
        )
        
        if enable_selection:
            fig.update_layout(dragmode='lasso')
        
        fig.update_layout(
            title=dict(font=dict(size=16, color="#1f2937"), x=0.5),
            xaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
            yaxis=dict(showgrid=True, gridcolor="#e5e7eb"),
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=400
        )
        
        return fig
    
    @staticmethod
    def create_combined_plot(historical_df: pd.DataFrame, forecast_profile: pd.DataFrame, 
                           title: str, unit: str = "bbl/month", history_match_df: pd.DataFrame = None) -> go.Figure:
        """Create plot showing historical + forecast data with optional history matching regression"""
        fig = go.Figure()
        
        # Add historical production data
        fig.add_trace(go.Scatter(
            x=historical_df['date'],
            y=historical_df['net'],
            mode='markers',
            marker=dict(color='#00CC96', size=4),
            name='Historical Production',
        ))
        
        # Add forecast profile
        if not forecast_profile.empty:
            fig.add_trace(go.Scatter(
                x=forecast_profile['date'],
                y=forecast_profile['rate'],
                mode='lines',
                line=dict(color='blue', width=3),
                name='ARPS Forecast',
            ))
        
        # Add history matching regression data
        if history_match_df is not None and not history_match_df.empty:
            fig.add_trace(go.Scatter(
                x=history_match_df['date'],
                y=history_match_df['rate'],
                mode='markers',
                marker=dict(color='red', size=4),
                name='History Match Regression',
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title=f"Net Oil ({unit})",
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=400,
            showlegend=True
        )
        
        return fig

    @staticmethod
    def create_enhanced_combined_plot(historical_df: pd.DataFrame, forecast_profile: pd.DataFrame, 
                                    selected_data: pd.DataFrame, qi_for_history: float, di_for_history: float, 
                                    b_for_history: float, title: str, unit: str = "bbl/month") -> go.Figure:
        """Create enhanced plot showing historical + history match + forecast data"""
        fig = go.Figure()
        
        # Historical production data
        fig.add_trace(go.Scatter(
            x=historical_df['date'],
            y=historical_df['net'],
            mode='markers',
            marker=dict(color='#00CC96', size=6),
            name='Historical Production',
        ))
        
        # Selected points for regression
        if not selected_data.empty:
            fig.add_trace(go.Scatter(
                x=pd.to_datetime(selected_data['date']),
                y=selected_data['net'],
                mode='markers',
                marker=dict(color='blue', size=8, symbol='diamond'),
                name='Selected Points for Regression',
            ))
            
            # ARPS History Match curve
            time_data = np.arange(len(selected_data))
            
            if b_for_history == 0:
                history_match_rates = qi_for_history * np.exp(-di_for_history * time_data)
            else:
                history_match_rates = qi_for_history / ((1 + b_for_history * di_for_history * time_data) ** (1 / b_for_history))
            
            history_match_dates = pd.to_datetime(selected_data['date'].values)
            
            fig.add_trace(go.Scatter(
                x=history_match_dates,
                y=history_match_rates,
                mode='lines',
                line=dict(color='red', width=3, dash='dash'),
                name=f'ARPS History Match (qi={qi_for_history:.1f})',
            ))
        
        # Future forecast
        if not forecast_profile.empty:
            fig.add_trace(go.Scatter(
                x=forecast_profile['date'],
                y=forecast_profile['rate'],
                mode='lines',
                line=dict(color='blue', width=3),
                name='ARPS Forecast',
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title=f"Net Oil ({unit})",
            hovermode="x unified",
            plot_bgcolor="white",
            paper_bgcolor="white",
            height=500,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        return fig
    
    @staticmethod
    def create_forecast_plots(cases_df: pd.DataFrame, selected_cases: list, 
                            end_date: date, q_abandon: float):
        """Create comprehensive forecast visualization"""
        if not selected_cases:
            st.warning("Please select at least one case for plotting.")
            return
        
        all_profiles = []
        eur_summary = []
        
        for case_label in selected_cases:
            case_data = cases_df[cases_df["case_label"] == case_label]
            case_profiles = []
            
            for _, row in case_data.iterrows():
                dca_time = row.get("dca_time", "monthly")
                q_abandon_use = Config.DEFAULT_ABANDONMENT_RATE_DAILY if dca_time == "daily" else Config.DEFAULT_ABANDONMENT_RATE_MONTHLY
                freq = "D" if dca_time == "daily" else "MS"
                
                profile = ARPSModel.create_production_profile(
                    row["eff_date"], end_date, row["qi"], row["di"], row["b"], q_abandon_use, frequency=freq
                )
                if not profile.empty:
                    profile["case_label"] = case_label
                    profile["well_name"] = row["well_name"]
                    case_profiles.append(profile)
                    
                    eur = ARPSModel.calculate_eur(profile)
                    eur_summary.append({
                        "Case": case_label,
                        "Well": row["well_name"],
                        "EUR (MMstb)": round(eur / 1_000, 3),
                        "Start Date": row["eff_date"]
                    })
            
            if case_profiles:
                combined = pd.concat(case_profiles)
                aggregated = combined.groupby("date", as_index=False)["rate"].sum()
                aggregated["case_label"] = case_label
                aggregated["cumulative"] = aggregated["rate"].cumsum()
                all_profiles.append(aggregated)
        
        if not all_profiles:
            st.warning("No valid profiles generated.")
            return
        
        # Display EUR summary
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("EUR Summary")
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
            st.subheader("Total EUR by Case")
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
            yaxis_title="Rate (bbl/month)",
            hovermode="x unified",
            plot_bgcolor="white"
        )
        
        fig2 = go.Figure()
        
        for i, case in enumerate(selected_cases):
            case_data = combined_df[combined_df["case_label"] == case]
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
            plot_bgcolor="white"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            st.plotly_chart(fig2, use_container_width=True)