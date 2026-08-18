"""
PalaySense LGU Dashboard — Overview (Dashboard page)
====================================================
Decision-support layout for the Office of the Provincial Agriculturist (OPA).

Top section:
  • Primary KPI row (5 compact cards):
      Total Production, Average Yield, Harvested Area, Supply Status, Forecast Period
  • Market Snapshot (2 compact cards): Regular & Fancy forecast price with % change.

Below: the two main trend charts (Provincial Price Trend + Provincial Yield Trend)
with dashed forecasts. Reuses the existing backend data layer and calculations.

Additional restored visuals from the backup:
  • Provincial Quarterly Production Bar Chart (Q1–Q4) + Production Insight Summary card
  • Top 5 Municipalities horizontal bar + Dry/Wet seasonal pie charts
  • Yield Forecast Summary card (Avg/Peak/Low) beside the yield trend.
  • Insights Narrative / Storytelling Mode
  • Peak price annotations on price charts
  • Section tabs for Historical/Forecast navigation
  • Sidebar Quick View radiobuttons for section navigation
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app_pages.lgu_dashboard import theme
from app_pages.lgu_dashboard import data_layer as dl


def _format_signed(num, suffix="", decimals=0):
    sign = "+" if num >= 0 else ""
    return f"{sign}{num:,.{decimals}f}{suffix}"


def _safe_column(df, col, default=0.0):
    """Safely get a DataFrame column, return Series of default if missing."""
    if df is None or df.empty:
        return pd.Series([default])
    if col not in df.columns:
        return pd.Series([default] * len(df))
    return df[col]


def _safe_index(arr, idx=0, default=0.0):
    """Safely index into a list/array, return default if out of bounds."""
    if arr is None or len(arr) == 0:
        return default
    try:
        return arr[idx]
    except (IndexError, TypeError):
        return default


def _pct_vs_hist(fc, avg):
    """% change of a forecast value vs a historical average (NaN/zero-safe).

    Returns 0.0 when the forecast is missing or the baseline is NaN/zero,
    preventing the '₱0.00/kg (-100.0%)' KPI bug.
    """
    if fc is None or avg is None:
        return 0.0
    try:
        c = float(fc)
        b = float(avg)
    except (TypeError, ValueError):
        return 0.0
    if pd.isna(c) or pd.isna(b) or b == 0:
        return 0.0
    return ((c - b) / b) * 100


def _group_by_period(df, period="ANNUAL", value_cols=None):
    """Group DataFrame by the specified period and return aggregated data with period labels.

    Args:
        df: DataFrame with 'date' column
        period: 'ANNUAL', 'QUARTERLY', or 'MONTHLY'
        value_cols: list of column names to aggregate (mean)

    Returns:
        DataFrame with 'period_label' column and aggregated values
    """
    if value_cols is None:
        value_cols = []
    if df is None or df.empty:
        return pd.DataFrame(columns=["period_label"] + value_cols)

    temp = df.copy()
    temp["date"] = pd.to_datetime(temp["date"])
    temp["year"] = temp["date"].dt.year
    temp["quarter"] = temp["date"].dt.quarter
    temp["month"] = temp["date"].dt.month
    temp["month_name"] = temp["date"].dt.strftime("%b")

    if period == "ANNUAL":
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str)
        return grouped
    elif period == "QUARTERLY":
        grouped = temp.groupby(["year", "quarter"]).mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str) + "-Q" + grouped["quarter"].astype(str)
        return grouped
    elif period == "MONTHLY":
        grouped = temp.groupby(["year", "month"]).mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped.apply(lambda r: f"{r['month_name']} {r['year']}", axis=1)
        return grouped
    else:
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
        grouped["period_label"] = grouped["year"].astype(str)
        return grouped


def _base_layout(fig, yaxis_title="", xaxis_title="Date"):
    """Apply the shared PalaySense plot styling to a figure."""
    fig.update_layout(
        yaxis_title=yaxis_title, xaxis_title=xaxis_title,
        height=300, hovermode="x unified",
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family=theme.FONT, size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
        xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
        margin=dict(t=30, b=40, l=40, r=40),
    )
    return fig


def _price_historical_chart(df, year=None, period="ANNUAL"):
    """Line chart for the selected year range and period with peak annotations."""
    if year is None:
        hist = df.copy()
    else:
        hist = dl.filter_by_year(df, year)
    if hist.empty:
        return go.Figure()

    value_cols = []
    if "fancy_palay_price" in hist.columns:
        value_cols.append("fancy_palay_price")
    if "other_variety_price" in hist.columns:
        value_cols.append("other_variety_price")

    if not value_cols:
        return go.Figure()

    grouped = _group_by_period(hist, period, value_cols)
    if grouped.empty:
        return go.Figure()

    # Determine x-axis title based on period
    xaxis_title = "Year"
    if period == "QUARTERLY":
        xaxis_title = "Quarter"
    elif period == "MONTHLY":
        xaxis_title = "Month"
    elif period == "ANNUAL":
        xaxis_title = "Year"

    fig = go.Figure()

    if "fancy_palay_price" in grouped.columns:
        fig.add_trace(go.Scatter(
            x=grouped["period_label"], y=grouped["fancy_palay_price"],
            mode="lines+markers", name="Fancy Palay",
            line=dict(color=theme.FANCY_COLOR, width=2.5), marker=dict(size=4),
        ))
        # Peak annotation for Fancy
        peak_idx = grouped["fancy_palay_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(
                x=peak_row["period_label"], y=peak_row["fancy_palay_price"],
                text=f"🔺 Peak: ₱{peak_row['fancy_palay_price']:.2f}/kg",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#16A34A",
                ax=0, ay=-50,
                font=dict(size=10, color="#15803D", weight="bold"),
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1, borderpad=4,
            )

    if "other_variety_price" in grouped.columns:
        fig.add_trace(go.Scatter(
            x=grouped["period_label"], y=grouped["other_variety_price"],
            mode="lines+markers", name="Regular Palay",
            line=dict(color=theme.REGULAR_COLOR, width=2.5), marker=dict(size=4),
        ))
        # Peak annotation for Regular
        peak_idx = grouped["other_variety_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(
                x=peak_row["period_label"], y=peak_row["other_variety_price"],
                text=f"🔺 Peak: ₱{peak_row['other_variety_price']:.2f}/kg",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#6D28D9",
                ax=0, ay=50,
                font=dict(size=10, color="#6D28D9", weight="bold"),
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1, borderpad=4,
            )

    return _base_layout(fig, yaxis_title="₱ / kg", xaxis_title=xaxis_title)


def _price_forecast_chart(df, dr):
    """Line chart: ONLY forecasted price values (projected future dates)."""
    fig = go.Figure()
    try:
        fancy = list(dr.forecast_3months_fancy) if dr.forecast_3months_fancy else []
        regular = list(dr.forecast_variety_3months) if dr.forecast_variety_3months else []
        if not fancy and not regular:
            return fig

        latest = dl.get_latest_date(df)
        if latest is None or pd.isna(latest):
            return fig

        n = max(len(fancy), 1)
        start = latest + pd.DateOffset(months=1)
        fc_months = pd.date_range(start=start, periods=n, freq="MS")

        if fancy:
            fig.add_trace(go.Scatter(
                x=fc_months, y=fancy,
                mode="lines+markers", name="Fancy Forecast",
                line=dict(color=theme.FANCY_COLOR, width=2.5, dash="dash"),
                marker=dict(size=6, symbol="diamond"),
                connectgaps=False,
            ))
        if regular:
            fig.add_trace(go.Scatter(
                x=fc_months, y=regular,
                mode="lines+markers", name="Regular Forecast",
                line=dict(color=theme.REGULAR_COLOR, width=2.5, dash="dash"),
                marker=dict(size=6, symbol="diamond"),
                connectgaps=False,
            ))
    except Exception:
        pass

    if not fig.data:
        return go.Figure()
    return _base_layout(fig, yaxis_title="₱ / kg", xaxis_title="Date")


def _yield_historical_chart(df, year=None, period="ANNUAL"):
    """Line chart for historical yield data over the selected year range and period."""
    quarterly = dl.get_quarterly_yield(df)
    if year is None:
        hist = quarterly.copy()
    else:
            hist = quarterly[quarterly["year"] == year].copy()
    if hist.empty:
        return go.Figure()

    # Re-group by period if needed
    if period == "ANNUAL" and not hist.empty:
        hist_grouped = hist.groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
        hist_grouped["period_label"] = hist_grouped["year"].astype(str)
        xaxis_title = "Year"
    elif period == "MONTHLY" and not hist.empty:
        # For monthly, we show quarterly data with monthly-style labels
        hist_grouped = hist.copy()
        hist_grouped["period_label"] = "Q" + hist_grouped["quarter"].astype(str) + " " + hist_grouped["year"].astype(str)
        xaxis_title = "Period"
    else:
        hist_grouped = hist.copy()
        hist_grouped["period_label"] = "Q" + hist_grouped["quarter"].astype(str) + " " + hist_grouped["year"].astype(str)
        xaxis_title = "Quarter"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hist_grouped["period_label"], y=hist_grouped["quarterly_yield_mt_per_ha"],
        mode="lines+markers", name="Historical Yield",
        line=dict(color=theme.HISTORICAL_COLOR, width=3), marker=dict(size=7),
    ))

    # Peak annotation
    peak_idx = hist_grouped["quarterly_yield_mt_per_ha"].idxmax()
    if pd.notna(peak_idx):
        peak_row = hist_grouped.loc[peak_idx]
        fig.add_annotation(
            x=peak_row["period_label"], y=peak_row["quarterly_yield_mt_per_ha"],
            text=f"🔺 Peak: {peak_row['quarterly_yield_mt_per_ha']:.2f} MT/ha",
            showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
            ax=0, ay=-45,
            font=dict(size=10, color="#C2410C", weight="bold"),
            bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
        )

    return _base_layout(fig, yaxis_title="Yield (MT/ha)", xaxis_title=xaxis_title)


def _yield_forecast_chart(dr, df):
    """Line chart: ONLY forecasted yield data (projected future quarters).

    The quarter axis is anchored to the LAST HISTORICAL DATE in the data
    (dynamic), never to pd.Timestamp.today().
    """
    fig = go.Figure()
    try:
        yield_fc = list(dr.forecast_quarterly_yield) if dr.forecast_quarterly_yield else []
        if not yield_fc:
            return fig

        latest = dl.get_latest_date(df)
        anchor = latest if latest is not None and not pd.isna(latest) else pd.Timestamp.today()

        fc_quarters = pd.period_range(
            start=pd.Period(anchor, freq="Q") + 1,
            periods=len(yield_fc), freq="Q"
        )
        fc_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
        fig.add_trace(go.Scatter(
            x=fc_labels, y=yield_fc,
            mode="lines+markers", name="Forecast Yield",
            line=dict(color=theme.FORECAST_COLOR, width=3, dash="dash"),
            marker=dict(size=8, symbol="diamond"),
        ))
        # Peak annotation
        peak_val = float(pd.Series(yield_fc).max())
        peak_idx = yield_fc.index(peak_val) if peak_val in yield_fc else -1
        if 0 <= peak_idx < len(fc_labels):
            fig.add_annotation(
                x=fc_labels[peak_idx], y=peak_val,
                text=f"🔺 Peak: {peak_val:.2f} MT/ha",
                showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
                ax=0, ay=-45,
                font=dict(size=10, color="#C2410C", weight="bold"),
                bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
            )
    except Exception:
        pass

    if not fig.data:
        return go.Figure()
    return _base_layout(fig, yaxis_title="Yield (MT/ha)", xaxis_title="Quarter")


def _supply_status_display(raw_status):
    """Map the backend supply status to the OPA labels (Surplus / Balanced / At Risk)."""
    if raw_status == "Surplus":
        return "Surplus"
    if raw_status == "Balanced":
        return "Balanced"
    return "At Risk"


def _production_quarterly(df, year):
    """Provincial Quarterly Production Bar Chart + Production Insight Summary card."""
    with theme.section_card(title="Provincial Quarterly Production",
                            desc="Production per quarter with high/low insight.",
                            icon_name="bar_chart"):

        prod = df.copy()
        prod["year"] = pd.to_datetime(prod["date"]).dt.year
        prod["quarter"] = pd.to_datetime(prod["date"]).dt.quarter
        sub = prod[prod["year"] == year] if year is not None else prod

        if sub.empty:
            st.info("No production data for the selected year.")
            return

        if "production_total" not in sub.columns:
            st.info("No production_total column available.")
            return
        q_avg = sub.groupby("quarter")["production_total"].mean().reset_index()
        q_avg["quarter"] = "Q" + q_avg["quarter"].astype(str)

        col1, col2 = st.columns([2.2, 1], gap="medium")
        with col1:
            fig = px.bar(
                q_avg, x="quarter", y="production_total", color="quarter",
                labels={"quarter": "Quarter", "production_total": "Production (MT)"},
                color_discrete_map={"Q1": "#FF9800", "Q2": "#C62828",
                                    "Q3": "#66BB6A", "Q4": "#FFB2C8"},
            )
            fig.update_layout(
                yaxis_title="Production (MT)", xaxis_title="Quarter",
                showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
                font=dict(family=theme.FONT, size=12),
                margin=dict(t=30, b=40, l=40, r=40),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="#F3F4F6"),
            )
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True, key=f"overview_prod_q_{year}")

        with col2:
            if not q_avg.empty:
                highest = q_avg.loc[q_avg["production_total"].idxmax()]
                lowest = q_avg.loc[q_avg["production_total"].idxmin()]
                avg_p = q_avg["production_total"].mean()
                trend = ("increasing" if q_avg["production_total"].iloc[-1]
                         > q_avg["production_total"].iloc[0] else "decreasing")
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.5rem;
                            border-radius:16px; border-left:6px solid #2E7D32;
                            box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.95rem; line-height:1.7;">
                    <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.8rem;">
                        📊 Production Insight Summary
                    </div>
                    <div>🏆 Highest Production: <b style="color:#2E7D32;">{highest['quarter']}</b></div>
                    <div>📉 Lowest Production: <b style="color:#C62828;">{lowest['quarter']}</b></div>
                    <div>📊 Average Production: <b>{avg_p:,.0f} MT</b></div>
                    <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.8rem 0;">
                    <div style="font-size:0.95rem; font-weight:600; color:#1B5E20;">
                        📈 Overall trend:
                        <span style="color:#2E7D32; font-weight:700;">{trend.upper()}</span>
                         pattern over the selected period
                    </div>
                </div>
                """, unsafe_allow_html=True)


def _top_municipalities_and_seasonal(dr, start_year, end_year):
    """Top 5 Municipalities Ranking (Historical Production) + Dry/Wet seasonal pies."""
    with theme.section_card(title="Top Municipalities & Seasonal Distribution",
                            desc="Municipal production ranking and dry/wet season split.",
                            icon_name="leaderboard"):
        muni = getattr(dr, "municipal_production_df", None)
        if muni is None or getattr(muni, "empty", True):
            muni = getattr(dr, "municipality_history_df", None)
        top5 = dl.get_top_5_producing_municipalities(muni, (start_year, end_year))

        if top5.empty:
            st.info("No municipality production data for the selected period.")
            return

        plot_top5 = top5.sort_values("palay_production")
        fig_top = px.bar(
            plot_top5,
            x="palay_production", y="municipality", orientation="h",
            color="palay_production",
            color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
            text=plot_top5["palay_production"].round(0).astype(int),
        )
        fig_top.update_layout(
            title=f"Top 5 Municipalities by Total Production ({start_year} – {end_year})",
            xaxis_title="Production (MT)", yaxis_title="Municipality",
            showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
            height=380, margin=dict(t=30, b=40, l=40, r=40),
            yaxis={"categoryorder": "total ascending"},
        )
        fig_top.update_traces(texttemplate='%{text:,}', textposition='outside')
        st.plotly_chart(fig_top, use_container_width=True,
                        key=f"overview_top5_{start_year}_{end_year}")

        dry = dl.get_municipal_seasonal_production(muni, (start_year, end_year), season="dry")
        wet = dl.get_municipal_seasonal_production(muni, (start_year, end_year), season="wet")

        col_a, col_b = st.columns(2)
        with col_a:
            if not dry.empty:
                fig = px.pie(dry, names="municipality", values="production",
                             color_discrete_sequence=px.colors.sequential.Greens[0:5][::-1])
                fig.update_layout(height=340, margin=dict(t=30, b=40, l=40, r=40))
                st.plotly_chart(fig, use_container_width=True,
                                key=f"overview_dry_{start_year}_{end_year}")
            else:
                st.info("No dry season data.")
        with col_b:
            if not wet.empty:
                fig = px.pie(wet, names="municipality", values="production",
                             color_discrete_sequence=px.colors.sequential.Teal[0:5][::-1])
                fig.update_layout(height=340, margin=dict(t=30, b=40, l=40, r=40))
                st.plotly_chart(fig, use_container_width=True,
                                key=f"overview_wet_{start_year}_{end_year}")
            else:
                st.info("No wet season data.")


def _yield_summary_card(dr):
    """Yield Forecast Summary card (Avg / Peak / Low) — placed beside yield trend."""
    with theme.section_card(title="Yield Forecast Summary",
                            desc="Forward-looking yield metrics for the next 4 quarters.",
                            icon_name="query_stats"):
        try:
            yield_fc = list(dr.forecast_quarterly_yield)
        except Exception:
            yield_fc = []

        if not yield_fc:
            st.info("No data available for yield forecast.")
        else:
            s = pd.Series(yield_fc, dtype="float64").dropna()
            if s.empty:
                st.info("No data available for yield forecast.")
            else:
                avg_y = float(s.mean())
                max_y = float(s.max())
                min_y = float(s.min())
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem;
                            border-radius:16px; border-left:6px solid #2E7D32;
                            box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.95rem; line-height:1.8;">
                    <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.5rem;">
                        📊 Yield Forecast Summary
                    </div>
                    <div>📈 Average: <b>{avg_y:.2f} MT/ha</b></div>
                    <div>🏆 Peak: <b>{max_y:.2f} MT/ha</b></div>
                    <div>📉 Low: <b>{min_y:.2f} MT/ha</b></div>
                    <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
                    <div style="font-size:0.85rem; color:#2E7D32;">Based on next 4 forecast quarters</div>
                </div>
                """, unsafe_allow_html=True)


def _insights_narrative(filtered_df, dr, end_year, selected_muni, selected_eco):
    """Dynamic Insights Narrative / Storytelling Mode."""
    with theme.section_card(title="📝 Insights Narrative",
                            desc="Auto-generated market summary based on your current filter selections.",
                            icon_name="auto_stories"):
        try:
            hist_fancy = _safe_column(filtered_df, "fancy_palay_price")
            hist_regular = _safe_column(filtered_df, "other_variety_price")

            fancy_forecast = _safe_index(dr.forecast_3months_fancy, 0) if dr.forecast_3months_fancy else None
            regular_forecast = _safe_index(dr.forecast_variety_3months, 0) if dr.forecast_variety_3months else None

            # Calculate QoQ yield change
            quarterly = dl.get_quarterly_yield(filtered_df)
            yield_qoq = 0
            if len(quarterly) >= 2:
                q_current = quarterly["quarterly_yield_mt_per_ha"].iloc[-1]
                q_previous = quarterly["quarterly_yield_mt_per_ha"].iloc[-2]
                if pd.notna(q_current) and pd.notna(q_previous) and q_previous != 0:
                    yield_qoq = ((q_current - q_previous) / q_previous) * 100

            # Forecast vs historical
            avg_fancy = hist_fancy.mean() if not hist_fancy.empty else None
            avg_regular = hist_regular.mean() if not hist_regular.empty else None
            fancy_fc_vs_hist = _pct_vs_hist(fancy_forecast, avg_fancy)
            regular_fc_vs_hist = _pct_vs_hist(regular_forecast, avg_regular)

            # Production total
            prod_total = filtered_df["production_total"].sum() if "production_total" in filtered_df.columns else 0

            # Determine trend words
            yield_trend_word = "growth" if yield_qoq > 0 else ("decline" if yield_qoq < 0 else "stability")
            price_trend_word = "upward" if fancy_fc_vs_hist > 0 else ("downward" if fancy_fc_vs_hist < 0 else "stable")

            if fancy_fc_vs_hist > 5:
                advisory = "consider holding Fancy Palay stocks for better pricing in the coming months."
            elif fancy_fc_vs_hist < -5:
                advisory = "consider selling Fancy Palay soon before prices drop further."
            else:
                advisory = "monitor market conditions closely before making bulk transactions."

            narrative_color = "#16A34A" if yield_qoq >= 0 else "#DC2626"
            price_color = "#16A34A" if fancy_fc_vs_hist >= 0 else "#DC2626"
        except Exception:
            yield_qoq = fancy_fc_vs_hist = regular_fc_vs_hist = 0
            yield_trend_word = price_trend_word = "stable"
            advisory = "monitor market conditions closely."
            narrative_color = price_color = "#1B5E20"
            prod_total = 0

        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%);
                    border: 1px solid rgba(22, 163, 74, 0.2); border-radius: 16px;
                    padding: 24px 28px; box-shadow: 0 4px 16px rgba(0,0,0,0.03);">
            <div style="font-size: 1.1rem; font-weight: 700; color: #1B5E20; margin-bottom: 10px;">
                📊 Quarterly Market Summary
            </div>
            <div style="font-size: 0.95rem; line-height: 1.8; color: #374151;">
                In the latest monitoring period, <strong>Bataan's</strong> agricultural sector shows
                <strong>{'promising growth' if yield_qoq > 0 or fancy_fc_vs_hist > 0 else 'signs of adjustment'}</strong>.
                Provincial yield is expected to <strong>{'rise' if yield_qoq >= 0 else 'decline'}
                by <span style="color:{narrative_color};">{abs(yield_qoq):.1f}%</span></strong>
                compared to the previous quarter, while <strong>Fancy Palay</strong> prices show a
                <span style="color:{price_color};">{price_trend_word}</span> trend of
                <strong><span style="color:{price_color};">{abs(fancy_fc_vs_hist):.1f}%</span></strong>
                relative to the historical average.
                <br><br>
                For Regular Palay, the forecast indicates a
                <strong>{'rise' if regular_fc_vs_hist >= 0 else 'decline'} of
                <span style="color:{'#16A34A' if regular_fc_vs_hist >= 0 else '#DC2626'};">{abs(regular_fc_vs_hist):.1f}%</span></strong>
                compared to historical prices.
                Farmers are advised to <strong>{advisory}</strong>
                <br><br>
                <small style="color:#9CA3AF;">
                    💡 This narrative is auto-generated for <strong>{'All Municipalities' if selected_muni == 'All Municipalities' else selected_muni}</strong>
                    across the selected period. Adjust filters to update insights.
                </small>
            </div>
        </div>
        """, unsafe_allow_html=True)


def _render_top_filter_bar(df):
    """Render a top horizontal filter toolbar for the overview page."""
    years = sorted(pd.Series(df["year"].dropna().astype(int).unique()).tolist())
    if not years:
        return None, None, "ANNUAL", "All Municipalities"

    st.session_state.setdefault("lgu_start_year", years[0])
    st.session_state.setdefault("lgu_end_year", years[-1])
    st.session_state.setdefault("lgu_period", "ANNUAL")
    st.session_state.setdefault("lgu_selected_muni", "All Municipalities")

    st.markdown(
        """
        <div style="margin:0.3rem 0 1rem 0; padding:0.8rem 1rem; border:1px solid #D8E6DA; border-radius:14px; background:#F8FBF7;">
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4 = st.columns([1.0, 1.0, 1.0, 1.2], gap="small")
    with col1:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">YEAR RANGE</div>', unsafe_allow_html=True)
        start_year = st.selectbox(
            "Start Year",
            options=years,
            index=years.index(st.session_state["lgu_start_year"]),
            key="lgu_start_year",
            label_visibility="collapsed",
        )
    with col2:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">TO</div>', unsafe_allow_html=True)
        end_year = st.selectbox(
            "End Year",
            options=years,
            index=years.index(st.session_state["lgu_end_year"]),
            key="lgu_end_year",
            label_visibility="collapsed",
        )
    with col3:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">PERIOD</div>', unsafe_allow_html=True)
        period = st.selectbox(
            "Period",
            options=["ANNUAL", "QUARTERLY", "MONTHLY"],
            index=["ANNUAL", "QUARTERLY", "MONTHLY"].index(st.session_state["lgu_period"]),
            key="lgu_period",
            label_visibility="collapsed",
        )
    with col4:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.3rem;">MUNICIPALITY</div>', unsafe_allow_html=True)
        muni_options = ["All Municipalities"]
        muni_options.extend(sorted(pd.Series(df.get("municipality", pd.Series(dtype="object")).dropna().unique()).tolist()))
        selected_muni = st.selectbox(
            "Municipality",
            options=muni_options,
            index=0 if st.session_state["lgu_selected_muni"] not in muni_options else muni_options.index(st.session_state["lgu_selected_muni"]),
            key="lgu_selected_muni",
            label_visibility="collapsed",
        )
    return start_year, end_year, period, selected_muni





def render(df, dr):
    """Main decision-support dashboard content for the OPA."""
    # Initialize display DataFrames to prevent UnboundLocalError
    df_dry_display = pd.DataFrame()
    df_wet_display = pd.DataFrame()

    theme.topbar(
        "Overview",
        "Provincial Palay Overview and Forecast Summary",
        as_of=dl.get_latest_month_label(df),
    )
    theme.close_header_card()

    # Always show all sections
    show_all = True

    # Top Filter Toolbar
    start_year, end_year, period, selected_muni = _render_top_filter_bar(df)
    if start_year is None:
        st.info("No year data available.")
        return

    filtered_df = df[(df["year"] >= start_year) & (df["year"] <= end_year)].copy()
    metrics = dl.get_year_metrics(filtered_df, end_year, dr)

    # Total production summed across the selected year range (MT).
    total_production = dl.get_total_production(filtered_df, (start_year, end_year))
    if total_production is not None:
        total_display = f"{total_production:,.0f} MT"
        total_sub = f"Sum across {start_year} – {end_year}"
    else:
        total_display = "No Data Available"
        total_sub = "Historical/current production"

    fc_start, fc_end, fc_months = dl.get_forecast_period(dr)
    supply_status, supply_ratio = dl.get_supply_status(dr, end_year)
    supply_display = _supply_status_display(supply_status)

    # Forecast values for the Market Snapshot
    fancy_forecast = _safe_index(dr.forecast_3months_fancy, 0) if hasattr(dr, "forecast_3months_fancy") else None
    regular_forecast = _safe_index(dr.forecast_variety_3months, 0) if hasattr(dr, "forecast_variety_3months") else None

    # Historical averages for the selected year range (basis for % change vs previous period)
    hist = filtered_df
    if not hist.empty:
        hist_fancy = _safe_column(hist, "fancy_palay_price").mean()
        hist_regular = _safe_column(hist, "other_variety_price").mean()
        fancy_change = ((fancy_forecast - hist_fancy) / hist_fancy * 100) if fancy_forecast is not None and hist_fancy else None
        regular_change = ((regular_forecast - hist_regular) / hist_regular * 100) if regular_forecast is not None and hist_regular else None
    else:
        fancy_change = regular_change = None

    # ---- Primary KPI Row (5 compact cards) ----
    if show_all:
        theme.kpi_row([
            theme.kpi_card(
                "🌾 Total Production",
                total_display,
                total_sub,
                icon_name="inventory_2", icon_bg="rgba(22,163,74,0.1)", icon_color="#16A34A", accent="#16A34A",
                compact=True,
            ),
            theme.kpi_card(
                "🌱 Average Yield",
                f"{metrics['yield'] * 1000:,.0f} kg/ha",
                f"{_format_signed(metrics['yield_delta'] * 1000, ' kg/ha', 0)} vs prev year",
                icon_name="eco", icon_bg="rgba(245,158,11,0.1)", icon_color="#F59E0B", accent="#F59E0B",
                compact=True,
            ),
            theme.kpi_card(
                "🚜 Harvested Area",
                f"{metrics['harvested']:,.0f} ha",
                f"{_format_signed(metrics['harv_delta'], ' ha')} vs prev year",
                icon_name="landscape", icon_bg="rgba(37,99,235,0.1)", icon_color="#2563EB", accent="#2563EB",
                compact=True,
            ),
            theme.kpi_card(
                "⚠ Supply Status",
                supply_display,
                (f"Ratio: {supply_ratio:.0f}%" if isinstance(supply_ratio, (int, float)) and supply_ratio != "N/A" else "Supply / demand"),
                icon_name="monitoring",
                icon_bg="rgba(220,38,38,0.1)" if supply_display == "At Risk" else "rgba(22,163,74,0.1)",
                icon_color="#DC2626" if supply_display == "At Risk" else "#16A34A",
                accent="#DC2626" if supply_display == "At Risk" else "#16A34A",
                compact=True,
            ),
            theme.kpi_card(
                "📅 Forecast Period",
                f"{fc_start} – {fc_end}",
                f"{fc_months}-Month Rolling Forecast",
                icon_name="calendar_month", icon_bg="rgba(124,58,237,0.1)", icon_color="#7C3AED", accent="#7C3AED",
                compact=True,
            ),
        ])

        # ---- Market Snapshot ----
        st.markdown(
            f'<div class="ps-market-heading">{theme.icon("storefront", "16px", "#1E5C3A")} Market Snapshot — Forecast Prices</div>',
            unsafe_allow_html=True,
        )
        m1, m2 = st.columns(2, gap="medium")
        with m1:
            if regular_forecast is not None:
                st.markdown(
                    theme.market_price_card(
                        "Regular Palay Forecast Price",
                        regular_forecast,
                        regular_change,
                        vs_label="vs selected year avg",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ps-market-card"><span class="ps-market-title">Regular Palay Forecast Price</span>'
                    '<div class="ps-market-price" style="font-size:1rem;">No Data Available</div></div>',
                    unsafe_allow_html=True,
                )
        with m2:
            if fancy_forecast is not None:
                st.markdown(
                    theme.market_price_card(
                        "Fancy Palay Forecast Price",
                        fancy_forecast,
                        fancy_change,
                        vs_label="vs selected year avg",
                    ),
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="ps-market-card"><span class="ps-market-title">Fancy Palay Forecast Price</span>'
                    '<div class="ps-market-price" style="font-size:1rem;">No Data Available</div></div>',
                    unsafe_allow_html=True,
                )

        theme.divider()

    # ---- Charts (with PERIOD filter applied + tabs) ----
    if show_all:
        c1, c2 = st.columns(2, gap="medium")

        with c1:
            with st.container(border=True):
                st.markdown("### 📈 Provincial Price Trend")
                st.caption("View historical Fancy & Regular prices or the price forecast.")
                price_subtab1, price_subtab2 = st.tabs(["📈 Historical Price Trend", "🔮 Price Forecast"])
                with price_subtab1:
                    st.plotly_chart(_price_historical_chart(filtered_df, None, period),
                                    use_container_width=True, key=f"price_hist_{start_year}_{end_year}_{period}")
                with price_subtab2:
                    st.plotly_chart(_price_forecast_chart(df, dr),
                                    use_container_width=True, key=f"price_fc_{start_year}_{end_year}")

        with c2:
            with st.container(border=True):
                st.markdown("### 🌱 Provincial Yield Trend")
                st.caption("View historical quarterly yield or the yield forecast.")
                yield_subtab1, yield_subtab2 = st.tabs(["📈 Historical Yield Trend", "🔮 Yield Forecast"])
                with yield_subtab1:
                    st.plotly_chart(_yield_historical_chart(filtered_df, None, period),
                                    use_container_width=True, key=f"yield_hist_{start_year}_{end_year}_{period}")
                with yield_subtab2:
                    st.plotly_chart(_yield_forecast_chart(dr, df),
                                    use_container_width=True, key=f"yield_fc_{start_year}_{end_year}")

        theme.divider()

    # ---- Provincial Quarterly Production + Insight Summary ----
    if show_all:
        _production_quarterly(filtered_df, end_year)

        # ---- Top Municipalities + Seasonal Distribution ----
        _top_municipalities_and_seasonal(dr, start_year, end_year)

    # ---- Yield Forecast Summary card ----
    if show_all:
        _yield_summary_card(dr)

    # ---- Model Benchmark vs Baselines (defense-grade evaluation) ----
    if show_all:
        _model_benchmark(dr)

    # ---- Insights Narrative ----
    if show_all:
        _insights_narrative(filtered_df, dr, end_year, selected_muni, "All Types")

    # ---- Footer ----
    st.markdown("""
    <div style="text-align: center; padding: 10px 0 5px 0; font-size: 0.75rem; color: #9CA3AF;
                border-top: 1px solid #E5E7EB; margin-top: 10px;">
        🌾 PalaySense LGU Dashboard • Provincial Palay Overview and Forecast Summary • v2.0
    </div>
    """, unsafe_allow_html=True)


def _model_benchmark(dr):
    """Model Benchmark vs Baselines (defense-grade evaluation section).

    Shows the selected forecast model's held-out RMSE against the Naive and
    Seasonal Naive baselines, plus the walk-forward (rolling-origin) mean ± std
    as a robustness check. Data comes from the evaluation blocks the pipeline
    writes into metrics.json.
    """
    ev = dr.model_evaluation
    if ev is None or ev.empty:
        return

    st.markdown("### 🧪 Model Benchmark vs Baselines")
    st.caption(
        "Bars = held-out test RMSE for the selected model vs Naive / Seasonal Naive baselines. "
        "Diamonds = walk-forward (rolling-origin) mean RMSE ± 1 std over multiple origins."
    )

    x = ev["Forecast"].tolist()
    wf_rmse = [v if v is not None else 0.0 for v in ev["Walk-Forward RMSE"].tolist()]
    wf_err = [v if v is not None else 0.0 for v in ev["Walk-Forward ±"].tolist()]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=x, y=[v if v is not None else 0.0 for v in ev["RMSE (test)"].tolist()],
        name="Selected Model (test)", marker_color="#2D6A4F", width=0.22,
    ))
    fig.add_trace(go.Bar(
        x=x, y=[v if v is not None else 0.0 for v in ev["Naive RMSE (test)"].tolist()],
        name="Naive", marker_color="#D4A373", width=0.22,
    ))
    fig.add_trace(go.Bar(
        x=x, y=[v if v is not None else 0.0 for v in ev["Seas. Naive RMSE (test)"].tolist()],
        name="Seasonal Naive", marker_color="#8B9BAE", width=0.22,
    ))
    fig.add_trace(go.Scatter(
        x=x, y=wf_rmse, mode="markers+lines", name="Walk-Forward (mean ± std)",
        marker=dict(symbol="diamond", size=12, color="#1E3A8A"),
        line=dict(color="#1E3A8A", width=1.5, dash="dot"),
        error_y=dict(type="data", array=wf_err, thickness=1.5, color="#1E3A8A"),
    ))
    fig.update_layout(
        barmode="group",
        height=380,
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title="RMSE",
        xaxis_title="",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True, key="model_benchmark")

    # Compact detail table (defense-ready numbers)
    detail = ev.copy()
    for col in detail.columns:
        if "Beats" in col:
            detail[col] = detail[col].map(
                lambda v: "Yes" if v is True else ("No" if v is False else "n/a")
            )
    st.markdown(
        '<div class="ps-market-heading">Benchmark Summary</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(detail, use_container_width=True, hide_index=True)
