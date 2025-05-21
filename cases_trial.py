import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
from datetime import date
import plotly.graph_objs as go
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "trial.db"

# ────────────── Initialize single shared connection with WAL and timeout ──────────────
conn = sqlite3.connect(
    DB_PATH,
   
)


# ────────────── Decline Curve Models ──────────────

def arps_rate(t: np.ndarray, qi: float, di: float, b: float) -> np.ndarray:
    if b == 0:
        return qi * np.exp(-di * t)
    return qi / ((1 + b * di * t) ** (1 / b))


def make_profile(
    start_date: date,
    end_date: date,
    qi: float,
    di: float,
    b: float,
    q_abnd: float
) -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    t_days = (dates - pd.to_datetime(start_date)).days
    rates = np.asarray(arps_rate(t_days, qi, di, b), dtype=float)
    rates[rates < q_abnd] = np.nan

    df = pd.DataFrame({"Date": dates, "rate": rates}).dropna()
    df["cum"] = df["rate"].cumsum()
    return df


def eur_from_profile(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return float(np.trapz(df["rate"].values, dx=1))


# ────────────── Database Utilities ──────────────

def load_wells(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM header_id ORDER BY well_name", conn)


def load_cases(conn: sqlite3.Connection) -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM forecast_cases ORDER BY eff_date DESC, case_id DESC", conn)


def insert_cases(conn: sqlite3.Connection, cases_df: pd.DataFrame) -> int:
    insert_sql = (
        "INSERT INTO forecast_cases "
        "(well_name, case_label, eff_date, qi, di, b) "
        "VALUES (?, ?, ?, ?, ?, ?)"
    )
    count = 0
    # Drop any rows missing required fields
    cases_df = cases_df.dropna(subset=["well_name", "case_label", "eff_date", "qi", "di", "b"])
    for _, row in cases_df.iterrows():
        name  = (row.get("well_name")  or "").strip()
        label = (row.get("case_label") or "").strip()
        if not name or not label:
            continue
        try:
            conn.execute(insert_sql, (
                name,
                label,
                str(row["eff_date"]),
                row["qi"],
                row["di"],
                row["b"],
            ))
            count += 1
        except sqlite3.Error as e:
            st.error(f"❌ Database error: {e}")
    # commit if not in autocommit
    try:
        conn.commit()
    except sqlite3.ProgrammingError:
        pass
    return count


# ────────────── Streamlit Sections ──────────────

def view_cases_section(cases_df: pd.DataFrame) -> None:
    with st.expander("🗂️ All Forecast Cases"):
        st.dataframe(cases_df, use_container_width=True)


def add_cases_section(conn: sqlite3.Connection) -> None:
    st.markdown("## ➕ Add New Forecast Cases")
    n = 4
    template = pd.DataFrame({
        "well_name":  [None] * n,
        "case_label": [None] * n,
        "eff_date":   [None] * n,
        "qi":         [None] * n,
        "di":         [None] * n,
        "b":          [None] * n,
    })
    edited = st.data_editor(
        template,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        column_config={
            "well_name":   st.column_config.TextColumn("Well Name"),
            "case_label":  st.column_config.TextColumn("Case Label"),
            "eff_date":    st.column_config.DateColumn("Effective Date"),
            "qi":          st.column_config.NumberColumn("Initial Rate (qi)", min_value=0.0),
            "di":          st.column_config.NumberColumn("di (1/day)", min_value=0.0, format="%.6f"),
            "b":           st.column_config.NumberColumn("b", min_value=0.0),
        }
    )
    if st.button("💾 Save Cases"):
        inserted = insert_cases(conn, edited)
        if inserted:
            st.success(f"✅ {inserted} case(s) inserted.")
            st.rerun()
        else:
            st.warning("⚠️ Enter at least one valid row.")


def forecast_inputs(cases_df: pd.DataFrame):
    st.markdown("## 📊 Forecast Visualization")
    labels      = st.multiselect("Select Cases", cases_df["case_label"].unique())
    end_date    = st.date_input("Forecast End Date", value=date(2040, 1, 1))
    q_abnd      = st.number_input("Abandonment Rate", min_value=0.0, value=10.0)
    plot_clicked = st.button("📈 Generate Plot")
    return labels, end_date, q_abnd, plot_clicked


def forecast_outputs(
    cases_df: pd.DataFrame,
    labels: list[str],
    end_date: date,
    q_abnd: float
) -> None:
    if not labels:
        st.warning("⚠️ Please select at least one case.")
        return

    # profiles will hold the summed (by Date+case) series
    profiles: list[pd.DataFrame] = []
    # raw_profiles will hold each well's daily profile (for annotations)
    raw_profiles: list[pd.DataFrame] = []

    eur_list = []
    for lbl in labels:
        df_sel = cases_df[cases_df["case_label"] == lbl]
        for _, r in df_sel.iterrows():
            prof = make_profile(r["eff_date"], end_date, r.qi, r.di, r.b, q_abnd)
            prof["case_label"] = lbl
            prof["well_name"]  = r.well_name
            raw_profiles.append(prof)

            eur_list.append({
                "Well":     r.well_name,
                "Case":     lbl,
                "Eff Date": r.eff_date,
                "EUR":      round(eur_from_profile(prof), 2),
            })

        # aggregate for this case
        df_grp = (
            pd.concat(raw_profiles[-len(df_sel):])  # only the last N profiles we just added
              .groupby("Date", as_index=False)["rate"]
              .sum()
        )
        df_grp["case_label"] = lbl
        # pick any one well_name to hang on; raw_profiles covers all wells for annotations
        df_grp["well_name"]  = df_sel["well_name"].iloc[0]
        profiles.append(df_grp)

    # EUR tables
    eur_df    = pd.DataFrame(eur_list)
    total_eur = eur_df.groupby("Case", as_index=False)["EUR"].sum()

    c1, c2 = st.columns(2)
        # … after building eur_df and total_eur …\
        # Convert EUR to millions and rename column
    eur_df_mm = eur_df.copy()
    eur_df_mm["EUR (MM)"] = eur_df_mm["EUR"] / 1_000_000
    eur_df_mm = eur_df_mm.drop(columns=["EUR"])

    total_eur_mm = total_eur.copy()
    total_eur_mm["EUR (MM)"] = total_eur_mm["EUR"] / 1_000_000
    total_eur_mm = total_eur_mm.drop(columns=["EUR"])


        # Common header style
    header_style = [{
        'selector': 'th',
        'props': [
            ('background-color', '#e6f7ff'),
            ('color', '#333333'),
            ('font-size', '14px'),
            ('text-align', 'center')
        ]
    }]

    # EUR Summary table in MM
    eur_styled = (
        eur_df_mm
        .style
        .format({"EUR (MM)": "{:,.2f}"})
        .background_gradient(
            cmap='Oranges', subset=['EUR (MM)'], low=0.2, high=0.8
        )
        .set_table_styles(header_style)
        .set_properties(**{
            'border': '1px solid #ddd',
            'padding': '8px',
            'text-align': 'center'
        })
    )

    # Total EUR by Case in MM
    total_styled = (
        total_eur_mm
        .style
        .format({"EUR (MM)": "{:,.2f}"})
        .background_gradient(
            cmap='Oranges', subset=['EUR (MM)'], low=0.2, high=0.8
        )
        .set_table_styles(header_style)
        .set_properties(**{
            'border': '1px solid #ddd',
            'padding': '8px',
            'text-align': 'center'
        })
    )

    with c1:
        st.markdown("### EUR Summary (MM)")
        st.write(eur_styled.to_html(), unsafe_allow_html=True)

    with c2:
        st.markdown("### Total EUR by Case (MM)")
        st.write(total_styled.to_html(), unsafe_allow_html=True)



    # prepare both DataFrames for plotting
    sum_df = pd.concat(profiles)
    raw_df = pd.concat(raw_profiles)

    # pass both into your two-arg renderer
    _render_plots(sum_df, raw_df)





def _render_plots(
    sum_df: pd.DataFrame,
    raw_df: pd.DataFrame
) -> None:
    import streamlit as st
    import plotly.graph_objs as go

    # — guard rails —
    if "well_name" not in raw_df.columns or "case_label" not in sum_df.columns:
        st.error("Need raw_df with well_name and sum_df with case_label.")
        return

    # — prepare cumulative field for line charts —
    sum_df = sum_df.copy()
    sum_df["cum"] = sum_df.groupby("case_label")["rate"].cumsum()

    # ─── 1) Daily Rate Line Chart ────────────────────────────────────────────
    fig1 = go.Figure()
    for lbl in sum_df["case_label"].unique():
        sub = sum_df[sum_df["case_label"] == lbl]
        fig1.add_trace(go.Scatter(
            x=sub.Date, y=sub.rate,
            mode="lines", name=lbl
        ))
        # annotate each well at its first day
        for well in raw_df.loc[raw_df.case_label==lbl, "well_name"].unique():
            first_dt = raw_df[
                (raw_df.case_label==lbl)&(raw_df.well_name==well)
            ].Date.min()
            y0 = float(sub.loc[sub.Date==first_dt, "rate"].iloc[0])
            fig1.add_annotation(
                x=first_dt, y=y0, text=well,
                showarrow=False,
                font=dict(family="Arial, sans-serif", size=12, color="#333"),
                yshift=8
            )

    fig1.update_layout(
        title="Daily Rate Forecast",
        xaxis_title="Date", yaxis_title="Rate",
        font=dict(family="Arial, sans-serif"),
        plot_bgcolor="#fafafa", paper_bgcolor="#fafafa",
        xaxis=dict(showgrid=True, gridcolor="#ddd"),
        yaxis=dict(showgrid=True, gridcolor="#ddd"),
        margin=dict(l=40, r=20, t=50, b=40)
    )

    # ─── 2) Cumulative Production Line Chart ─────────────────────────────────
    fig2 = go.Figure()
    for lbl in sum_df["case_label"].unique():
        sub = sum_df[sum_df["case_label"] == lbl]
        fig2.add_trace(go.Scatter(
            x=sub.Date, y=sub.cum,
            mode="lines", name=lbl
        ))
        for well in raw_df.loc[raw_df.case_label==lbl, "well_name"].unique():
            first_dt = raw_df[
                (raw_df.case_label==lbl)&(raw_df.well_name==well)
            ].Date.min()
            y0 = float(sub.loc[sub.Date==first_dt, "cum"].iloc[0])
            fig2.add_annotation(
                x=first_dt, y=y0, text=well,
                showarrow=False,
                font=dict(family="Arial, sans-serif", size=12, color="#333"),
                yshift=8
            )

    fig2.update_layout(
        title="Cumulative Production",
        xaxis_title="Date", yaxis_title="Cumulative Volume",
        font=dict(family="Arial, sans-serif"),
        plot_bgcolor="#fafafa", paper_bgcolor="#fafafa",
        xaxis=dict(showgrid=True, gridcolor="#ddd"),
        yaxis=dict(showgrid=True, gridcolor="#ddd"),
        margin=dict(l=40, r=20, t=50, b=40)
    )

    # render the two line charts side by side
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        st.plotly_chart(fig2, use_container_width=True)

    # palette for area charts
    palette = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3']

    # ─── 3) Stacked Area: Daily Rate by Case ────────────────────────────────
    area_rate = (
        sum_df
        .pivot(index="Date", columns="case_label", values="rate")
        .fillna(0)
    )

    fig3 = go.Figure()
    for case in area_rate.columns:
        fig3.add_trace(go.Scatter(
            x=area_rate.index,
            y=area_rate[case],
            mode='none',
            stackgroup='one',
            name=case
        ))
    fig3.update_layout(
        title="Stacked Area: Daily Rate by Case",
        xaxis_title="Date", yaxis_title="Daily Rate",
        font=dict(family="Arial, sans-serif"),
        plot_bgcolor="#fafafa", paper_bgcolor="#fafafa",
        colorway=palette,
        xaxis=dict(showgrid=True, gridcolor="#ddd"),
        yaxis=dict(showgrid=True, gridcolor="#ddd"),
        margin=dict(l=40, r=20, t=50, b=40)
    )

    st.markdown("---")
    with col1:
        st.plotly_chart(fig3, use_container_width=True)

    # ─── 4) Stacked Area: Cumulative Production by Case ──────────────────────
    area_cum = (
        sum_df
        .pivot(index="Date", columns="case_label", values="cum")
        .fillna(0)
    )

    fig4 = go.Figure()
    for case in area_cum.columns:
        fig4.add_trace(go.Scatter(
            x=area_cum.index,
            y=area_cum[case],
            mode='none',
            stackgroup='one',
            name=case
        ))
    fig4.update_layout(
        title="Stacked Area: Cumulative Production by Case",
        xaxis_title="Date", yaxis_title="Cumulative Volume",
        font=dict(family="Arial, sans-serif"),
        plot_bgcolor="#fafafa", paper_bgcolor="#fafafa",
        colorway=palette,
        xaxis=dict(showgrid=True, gridcolor="#ddd"),
        yaxis=dict(showgrid=True, gridcolor="#ddd"),
        margin=dict(l=40, r=20, t=50, b=40)
    )
    with col2:
       st.plotly_chart(fig4, use_container_width=True)






# ────────────── Run App ──────────────

st.title("📈 Decline Curve Forecast Dashboard")

wells_df = load_wells(conn)
cases_df = load_cases(conn)

col_view, _ = st.columns(2)
with col_view:
    view_cases_section(cases_df)

st.markdown("---")

col_add, col_forecast = st.columns([1, 1])
with col_add:
    add_cases_section(conn)
with col_forecast:
    labels, end_date, q_abnd, plot_clicked = forecast_inputs(cases_df)

if plot_clicked:
    forecast_outputs(cases_df, labels, end_date, q_abnd)

conn.close()
