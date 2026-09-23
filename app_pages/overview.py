import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from data.Dashboard_Ready import reload_dashboard_data, load_provincial_forecasts
from app_pages.lgu_dashboard import data_layer as dl

# safe helpers
def _safe_column(df, col, default=0.0):
    if df is None or df.empty:
        return pd.Series([default])
    if col not in df.columns:
        return pd.Series([default] * len(df))
    return df[col]

def _safe_index(arr, idx=0, default=0.0):
    if arr is None or len(arr) == 0:
        return default
    try:
        return arr[idx]
    except (IndexError, TypeError):
        return default

def _safe_mean(values, default=0.0):
    if values is None or len(values) == 0:
        return default
    try:
        s = pd.Series(values, dtype="float64").dropna()
        return float(s.mean()) if not s.empty else default
    except Exception:
        return default

def _safe_max(values, default=0.0):
    if values is None or len(values) == 0:
        return default
    try:
        s = pd.Series(values, dtype="float64").dropna()
        return float(s.max()) if not s.empty else default
    except Exception:
        return default

def _safe_min(values, default=0.0):
    if values is None or len(values) == 0:
        return default
    try:
        s = pd.Series(values, dtype="float64").dropna()
        return float(s.min()) if not s.empty else default
    except Exception:
        return default

def _pct_change(current, baseline):
    if current is None or baseline is None:
        return None
    try:
        c = float(current); b = float(baseline)
    except (TypeError, ValueError):
        return None
    if pd.isna(c) or pd.isna(b):
        return None
    if b == 0:
        return 0.0
    return ((c - b) / b) * 100

def _pick_column(df, candidates):
    if df is None:
        return None
    return next((c for c in candidates if c in df.columns), None)

# ---- farmer helpers for Pangkalahatan hero/top cards (surgical patch - DETALYE untouched) ----
def _build_price_context(fc_fancy, fc_regular, forecast_months):
    def _interp(vals):
        if not vals or len(vals)==0:
            return {"vals":[], "labels":[], "lowest":None, "highest":None, "trend_sentence":"Forecast data is being prepared. Check back soon.", "recover_sentence":"No trend data yet."}
        labels = [m.strftime("%b %Y") if hasattr(m,'strftime') else str(m) for m in forecast_months[:len(vals)]]
        try:
            s = pd.Series(vals, dtype=float)
            mn = float(s.min()); mx = float(s.max())
            mn_idx = int(s.idxmin()); mx_idx = int(s.idxmax())
            mn_lab = labels[mn_idx] if mn_idx < len(labels) else "N/A"
            mx_lab = labels[mx_idx] if mx_idx < len(labels) else "N/A"
        except Exception:
            mn=mx=mn_lab=mx_lab=None
        try:
            first = float(vals[0]); last = float(vals[-1])
            if last > first + 0.3:
                if mn_idx is not None and mx_idx > mn_idx:
                    trend = f"Forecast rising toward {mx_lab}"
                    recover = f"The forecast shows prices recovering after {mn_lab}."
                else:
                    trend = f"Prices are forecast to increase toward {mx_lab}"
                    recover = f"Prices are forecast to be highest in {mx_lab}."
            elif last < first - 0.3:
                trend = f"Forecast easing toward {mx_lab}"
                recover = f"The forecast shows prices easing after {mn_lab}."
            else:
                trend = "Forecast steady over the next months"
                recover = "Prices are forecast to remain steady."
        except Exception:
            trend = "Forecast steady over the next months"
            recover = "Prices are forecast to remain steady."
        return {"vals": vals, "labels": labels, "lowest": (mn_lab, mn), "highest": (mx_lab, mx), "trend_sentence": trend, "recover_sentence": recover}
    return {"fancy": _interp(list(fc_fancy)), "regular": _interp(list(fc_regular))}

def _harvest_interpretation(yield_vals, quarter_labels):
    if not yield_vals:
        return {"avg": None, "range": None, "delta_prev": None, "sentence": "Yield forecast is being prepared."}
    s = pd.Series(yield_vals, dtype=float).dropna()
    if s.empty:
        return {"avg": None, "range": None, "delta_prev": None, "sentence": "Yield forecast is being prepared."}
    avg = float(s.mean())
    lo = float(s.min()); hi = float(s.max())
    delta = float(s.iloc[-1] - s.iloc[0]) if len(s)>1 else 0.0
    if abs(delta) < 0.05:
        sent = f"Expected yield remains around {avg:.2f} MT/ha."
    elif delta > 0:
        sent = f"Yield is forecast to improve toward {quarter_labels[-1] if quarter_labels else 'next quarter'}."
    else:
        sent = f"Yield is forecast to ease slightly after {quarter_labels[0] if quarter_labels else 'next quarter'}."
    return {"avg":avg, "range":(lo,hi), "delta_prev": delta, "sentence": sent, "lo":lo, "hi":hi}

def _farmer_price_chart(forecast_months, vals, color="#1B5E20"):
    fig = go.Figure()
    if not vals or len(vals)==0:
        return fig
    labels = [m.strftime("%b %Y") if hasattr(m,'strftime') else str(m) for m in forecast_months[:len(vals)]]
    fig.add_trace(go.Scatter(x=labels, y=vals, mode="lines+markers+text", name="Forecast", line=dict(color=color, width=2.6), marker=dict(size=7, color=color), text=[f"\u20B1{v:.2f}" if pd.notna(v) else "" for v in vals], textposition="top center", textfont=dict(size=10, color="#1B4332")))
    try:
        s = pd.Series(vals, dtype=float)
        mn_idx = int(s.idxmin()); mx_idx = int(s.idxmax())
        mn_val = float(s.min()); mx_val = float(s.max())
        mn_lab = labels[mn_idx]; mx_lab = labels[mx_idx]
        fig.add_annotation(x=mn_lab, y=mn_val, text=f"Lowest<br>{mn_lab}<br>\u20B1{mn_val:.2f}", showarrow=False, yshift=-28, bgcolor="#F1F8E9", bordercolor="#C5E1A5", borderwidth=1, font=dict(size=9, color="#33691E"), opacity=0.95)
        fig.add_annotation(x=mx_lab, y=mx_val, text=f"Highest<br>{mx_lab}<br>\u20B1{mx_val:.2f}", showarrow=False, yshift=22, bgcolor="#E8F5E9", bordercolor="#A5D6A7", borderwidth=1, font=dict(size=9, color="#1B5E20"), opacity=0.95)
        rng = max(vals)-min(vals)
        pad = max(0.6, rng*0.35)
        fig.update_yaxes(range=[min(vals)-pad, max(vals)+pad])
    except Exception:
        pass
    fig.update_layout(height=300, margin=dict(l=10,r=10,t=26,b=10), plot_bgcolor="white", paper_bgcolor="white", xaxis=dict(gridcolor="#F3F4F6", showgrid=True, tickfont=dict(size=11, color="#6B7280")), yaxis=dict(gridcolor="#F3F4F6", showgrid=True, tickfont=dict(size=11, color="#6B7280"), title=dict(text="\u20B1/kg", font=dict(size=11, color="#6B7280"))), showlegend=False, hovermode="x unified")
    return fig

# benchmark helpers
def _add_benchmark_ref_line(fig, y_value, label, line_color="#78909C", annotation_position="top left"):
    if fig is None or y_value is None:
        return fig
    try:
        y = float(y_value)
    except (TypeError, ValueError):
        return fig
    if pd.isna(y):
        return fig
    try:
        fig.add_hline(y=y, line_dash="dot", line_width=1.2, line_color=line_color, opacity=0.6, annotation_text=label, annotation_position=annotation_position, annotation=dict(font=dict(size=10, color=line_color), bgcolor="rgba(255,255,255,0.85)"))
    except Exception:
        try:
            fig.add_hline(y=y, line_dash="dot", line_width=1.2, line_color=line_color, opacity=0.6, annotation_text=label, annotation_position=annotation_position)
        except Exception:
            pass
    return fig

def _normalize_benchmarks(benchmark_option):
    _none_vals = ("None", "Hide (None)", "Itago (None)", "Wala")
    if benchmark_option is None:
        return set()
    if isinstance(benchmark_option, (list, set, tuple)):
        return {str(o).strip() for o in benchmark_option if str(o).strip() and str(o).strip() not in _none_vals}
    s = str(benchmark_option).strip()
    if not s or s in _none_vals:
        return set()
    return {s}

def _apply_benchmarks_to_fig(fig, df, chart_type, benchmark_options, provincial_df=None):
    opts = _normalize_benchmarks(benchmark_options)
    if not opts:
        return fig
    src_df = provincial_df if provincial_df is not None and chart_type in ("yield", "price") else df
    if src_df is None:
        src_df = df
    for opt in opts:
        try:
            if chart_type == "yield":
                if opt in ("Presyo sa Merkado", "Market Price", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
                    _col = "quarterly_yield_mt_per_ha"
                    _col = _col if src_df is not None and _col in src_df.columns else _pick_column(src_df, ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha"])
                    hist_avg = None
                    if _col and src_df is not None and _col in src_df.columns:
                        hist_avg = pd.to_numeric(src_df[_col], errors="coerce").dropna().mean()
                        if pd.isna(hist_avg):
                            hist_avg = None
                    if hist_avg is not None and not pd.isna(hist_avg):
                        v = float(hist_avg)
                        label = f"Bataan 10-Yr Avg Yield ({v:.2f} MT/ha)"
                        pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
                        fig = _add_benchmark_ref_line(fig, v, label, line_color="#616161", annotation_position=pos)
                elif opt in ("Target ng Gobyerno", "Government Target", "NFA / DA Policy Baseline"):
                    pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
                    fig = _add_benchmark_ref_line(fig, 4.50, "DA Target Yield (4.50 MT/ha)", line_color="#2E7D32", annotation_position=pos)
                continue
            if chart_type == "price":
                if opt in ("Presyo sa Merkado", "Market Price", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
                    rolling_regular_avg = None; rolling_fancy_avg = None
                    try:
                        if src_df is not None and "other_variety_price" in src_df.columns:
                            rolling_regular_avg = pd.to_numeric(src_df["other_variety_price"], errors="coerce").dropna().tail(12).mean()
                            if pd.isna(rolling_regular_avg):
                                rolling_regular_avg = None
                        if src_df is not None and "fancy_palay_price" in src_df.columns:
                            rolling_fancy_avg = pd.to_numeric(src_df["fancy_palay_price"], errors="coerce").dropna().tail(12).mean()
                            if pd.isna(rolling_fancy_avg):
                                rolling_fancy_avg = None
                    except Exception:
                        pass
                    if rolling_regular_avg is not None and not pd.isna(rolling_regular_avg):
                        v = float(rolling_regular_avg)
                        label = f"Regular 3-Yr Rolling Avg (\u20B1{v:.2f}/kg)"
                        pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
                        fig = _add_benchmark_ref_line(fig, v, label, line_color="#616161", annotation_position=pos)
                    if rolling_fancy_avg is not None and not pd.isna(rolling_fancy_avg):
                        v = float(rolling_fancy_avg)
                        label = f"Fancy 3-Yr Rolling Avg (\u20B1{v:.2f}/kg)"
                        pos = "bottom left" if fig.layout.shapes is None or len(fig.layout.shapes) == 1 else "top left"
                        fig = _add_benchmark_ref_line(fig, v, label, line_color="#78909C", annotation_position=pos)
                elif opt in ("Target ng Gobyerno", "Government Target", "NFA / DA Policy Baseline"):
                    fig = _add_benchmark_ref_line(fig, 19.00, "NFA Floor Price (\u20B119.00/kg)", line_color="#EF4444", annotation_position="bottom left")
                    fig = _add_benchmark_ref_line(fig, 23.75, "Fancy Commercial Target (\u20B123.75/kg)", line_color="#F59E0B", annotation_position="top left")
                continue
        except Exception:
            continue
    return fig

# period helpers
def _period_suffix(period: str) -> str:
    if not period:
        return ""
    p = str(period).strip().upper()
    if p == "ANNUAL":
        return ""
    if p in ("SEMESTER 1", "SEM 1"):
        return " \u2022 Sem 1"
    if p in ("SEMESTER 2", "SEM 2"):
        return " \u2022 Sem 2"
    if p == "QUARTER 1": return " \u2022 Q1"
    if p == "QUARTER 2": return " \u2022 Q2"
    if p == "QUARTER 3": return " \u2022 Q3"
    if p == "QUARTER 4": return " \u2022 Q4"
    return ""

def _filter_df_by_period(df, period):
    if df is None or df.empty or "date" not in df.columns:
        return df
    p = str(period).strip().upper() if period else "ANNUAL"
    try:
        d = pd.to_datetime(df["date"], errors="coerce"); months = d.dt.month; quarters = d.dt.quarter
    except Exception:
        return df
    if p in ("SEMESTER 1", "SEM 1"): return df[months.between(1, 6)]
    if p in ("SEMESTER 2", "SEM 2"): return df[months.between(7, 12)]
    if p == "QUARTER 1": return df[quarters == 1]
    if p == "QUARTER 2": return df[quarters == 2]
    if p == "QUARTER 3": return df[quarters == 3]
    if p == "QUARTER 4": return df[quarters == 4]
    return df

def _align_forecast_arrays(fancy_arr, regular_arr):
    fancy_s = pd.Series(list(fancy_arr) if fancy_arr is not None else [], name="fancy_palay_price")
    regular_s = pd.Series(list(regular_arr) if regular_arr is not None else [], name="other_variety_price")
    aligned = pd.concat([fancy_s, regular_s], axis=1, join="outer").sort_index()
    return aligned["fancy_palay_price"], aligned["other_variety_price"]

def _group_by_period(df, period="ANNUAL", value_cols=None):
    if value_cols is None: value_cols = []
    if df is None or df.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
    temp = df.copy(); temp["date"] = pd.to_datetime(temp["date"]); temp["year"] = temp["date"].dt.year; temp["quarter"] = temp["date"].dt.quarter; temp["month"] = temp["date"].dt.month; temp["semester"] = np.where(temp["month"] <= 6, 1, 2)
    p = str(period).strip().upper() if period else "ANNUAL"
    if p in ("SEMESTER 1", "SEM 1"):
        temp = temp[temp["semester"] == 1]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str) + " Sem 1"; return grouped
    if p in ("SEMESTER 2", "SEM 2"):
        temp = temp[temp["semester"] == 2]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str) + " Sem 2"; return grouped
    if p == "QUARTER 1":
        temp = temp[temp["quarter"] == 1]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str) + "-Q1"; return grouped
    if p == "QUARTER 2":
        temp = temp[temp["quarter"] == 2]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str) + "-Q2"; return grouped
    if p == "QUARTER 3":
        temp = temp[temp["quarter"] == 3]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str) + "-Q3"; return grouped
    if p == "QUARTER 4":
        temp = temp[temp["quarter"] == 4]
        if temp.empty: return pd.DataFrame(columns=["period_label"] + value_cols)
        grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str) + "-Q4"; return grouped
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index(); grouped["period_label"] = grouped["year"].astype(str); return grouped

# charts
def _price_historical_chart(df, period="ANNUAL", benchmark_option="Wala"):
    value_cols = []
    if "fancy_palay_price" in df.columns: value_cols.append("fancy_palay_price")
    if "other_variety_price" in df.columns: value_cols.append("other_variety_price")
    if not value_cols: return go.Figure()
    grouped = _group_by_period(df, period, value_cols)
    if grouped.empty: return go.Figure()
    fig = go.Figure()
    if "fancy_palay_price" in grouped.columns:
        fig.add_trace(go.Scatter(x=grouped["period_label"], y=grouped["fancy_palay_price"], mode="lines+markers", name="Fancy Palay", line=dict(color="#2E7D32", width=2.5), marker=dict(size=6)))
        peak_idx = grouped["fancy_palay_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(x=peak_row["period_label"], y=peak_row["fancy_palay_price"], text=f"\u25B2 Peak: \u20B1{peak_row['fancy_palay_price']:.2f}/kg", showarrow=True, arrowhead=2, arrowcolor="#16A34A", ax=0, ay=-45, font=dict(size=10, color="#15803D"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1, borderpad=4)
    if "other_variety_price" in grouped.columns:
        fig.add_trace(go.Scatter(x=grouped["period_label"], y=grouped["other_variety_price"], mode="lines+markers", name="Regular Palay", line=dict(color="#D4A017", width=2.5), marker=dict(size=6)))
        peak_idx = grouped["other_variety_price"].idxmax()
        if pd.notna(peak_idx):
            peak_row = grouped.loc[peak_idx]
            fig.add_annotation(x=peak_row["period_label"], y=peak_row["other_variety_price"], text=f"\u25B2 Peak: \u20B1{peak_row['other_variety_price']:.2f}/kg", showarrow=True, arrowhead=2, arrowcolor="#6D28D9", ax=0, ay=45, font=dict(size=10, color="#6D28D9"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1, borderpad=4)
    fig = _apply_benchmarks_to_fig(fig, df, "price", benchmark_option)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Year", yaxis_title="\u20B1/kg", legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11)), plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified", xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    return fig

def _price_forecast_chart(provincial_df, fancy_forecast, regular_forecast, benchmark_option="Wala"):
    fig = go.Figure()
    try:
        fancy_fc, regular_fc = _align_forecast_arrays(fancy_forecast, regular_forecast)
        if fancy_fc.dropna().empty and regular_fc.dropna().empty: return fig
        n = len(fancy_fc)
        hist_dates = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
        if hist_dates.empty: raise ValueError("No historical dates")
        last_hist_date = hist_dates.max()
        fc_months = pd.date_range(start=last_hist_date + pd.DateOffset(months=1), periods=n, freq="MS")
        fig.add_trace(go.Scatter(x=fc_months, y=fancy_fc.values, mode="lines+markers", name="Fancy Forecast", line=dict(color="#2E7D32", width=2.5, dash="dash"), marker=dict(size=6, symbol="diamond"), connectgaps=False))
        fig.add_trace(go.Scatter(x=fc_months, y=regular_fc.values, mode="lines+markers", name="Regular Forecast", line=dict(color="#D4A017", width=2.5, dash="dash"), marker=dict(size=6, symbol="diamond"), connectgaps=False))
        fig = _apply_benchmarks_to_fig(fig, provincial_df, "price", benchmark_option)
        fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title="\u20B1/kg", legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11)), plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified", xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    except Exception:
        return go.Figure()
    return fig

def _yield_historical_chart(df, period="ANNUAL", benchmark_option="Wala"):
    grouped = _group_by_period(df, period, ["quarterly_yield_mt_per_ha"])
    if grouped.empty or "quarterly_yield_mt_per_ha" not in grouped.columns: return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grouped["period_label"], y=grouped["quarterly_yield_mt_per_ha"], mode="lines+markers", name="Historical Yield", line=dict(color="#1B5E20", width=3), marker=dict(size=7)))
    peak_idx = grouped["quarterly_yield_mt_per_ha"].idxmax()
    if pd.notna(peak_idx):
        peak_row = grouped.loc[peak_idx]
        fig.add_annotation(x=peak_row["period_label"], y=peak_row["quarterly_yield_mt_per_ha"], text=f"\u25B2 Peak: {peak_row['quarterly_yield_mt_per_ha']:.2f} MT/ha", showarrow=True, arrowhead=2, arrowcolor="#F57C00", ax=0, ay=-45, font=dict(size=10, color="#C2410C"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4)
    fig = _apply_benchmarks_to_fig(fig, df, "yield", benchmark_option)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Year", yaxis_title="MT/ha", legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5, font=dict(size=11)), plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified", xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
    return fig

def _yield_forecast_chart(provincial_df, yield_forecast, benchmark_option="Wala"):
    # same orange bar design as LGU yield forecast
    fig = go.Figure()
    try:
        fc_yield = list(yield_forecast) if yield_forecast is not None else []
        if not fc_yield: return fig
        hist_dates = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
        if hist_dates.empty: raise ValueError("No historical dates")
        last_hist_date = hist_dates.max()
        fc_quarters = pd.period_range(start=pd.Period(last_hist_date, freq="Q") + 1, periods=len(fc_yield), freq="Q")
        fc_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
        ydf = pd.DataFrame({"Quarter": fc_labels, "Yield": fc_yield})
        fig = px.bar(ydf, x="Quarter", y="Yield", color="Yield", color_continuous_scale=["#8D4004", "#E67E22", "#F39C12", "#F1C40F"], text=ydf["Yield"].round(2))
        fig.update_traces(textposition="outside", marker_line_width=0, marker_cornerradius=8, hovertemplate="%{x}<br>Hula: %{y:.2f} MT/ha<extra></extra>")
        fig_go = go.Figure(fig)
        try:
            peak_val = float(pd.Series(fc_yield).max())
            peak_idx = fc_yield.index(peak_val)
            fig_go.add_annotation(x=fc_labels[peak_idx], y=peak_val, text=f"\u25B2 Peak: {peak_val:.2f} MT/ha", showarrow=True, arrowhead=2, arrowcolor="#F57C00", ax=0, ay=-45, font=dict(size=10, color="#C2410C"), bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4)
        except Exception:
            pass
        fig_go = _apply_benchmarks_to_fig(fig_go, provincial_df, "yield", benchmark_option)
        try:
            _mn, _mx = float(pd.Series(fc_yield).min()), float(pd.Series(fc_yield).max())
            import math
            _lo = math.floor((_mn - 0.08) / 0.05) * 0.05
            _hi = math.ceil((_mx + 0.10) / 0.05) * 0.05
            fig_go.update_yaxes(range=[_lo, _hi], dtick=0.05, tickformat=".2f")
        except Exception:
            pass
        fig_go.update_layout(height=340, margin=dict(l=10, r=10, t=35, b=10), showlegend=False, bargap=0.4, yaxis_title="MT/ha", xaxis_title=None, plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified", xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True))
        return fig_go
    except Exception:
        return go.Figure()

def _render_municipal_crop_cycle_chart(df, rice_type, classification, selected_municipalities, selected_cycle=None):
    if df is None or df.empty:
        st.info("Wala pang hula para sa bawat bayan.")
        return
    df = df.copy(); df.columns = [str(col).lower() for col in df.columns]
    if selected_municipalities:
        selected_munis_lc = [str(m).lower() for m in selected_municipalities]
        df = df[df["municipality"].str.lower().isin(selected_munis_lc)]
    if selected_cycle is None:
        selected_cycle = st.selectbox("Piliin ang panahon ng taniman:", ["Dry Season Crop Cycle", "Wet Season Crop Cycle"], key=f"crop_cycle_{rice_type}_{classification}")
        st.write("---")
    base_key = f"{rice_type.lower()}{classification.lower()}".replace(" ", "")
    suffix = "_dry" if "Dry" in selected_cycle else "_wet"
    target_key = f"{base_key}{suffix}"
    type_col = "rice type & season"
    sub = df[df[type_col].str.lower() == target_key] if type_col in df.columns else pd.DataFrame()
    if sub.empty:
        st.warning(f"Walang datos para sa '{target_key}' — subukan ang ibang kombinasyon.")
        return
    label_map = {}
    for key, n in (("forecast_month_1_label", 1), ("forecast_month_2_label", 2), ("forecast_month_3_label", 3)):
        if key in sub.columns and sub[key].notna().any():
            label_map[f"month {n}"] = str(sub[key].iloc[0])
        else:
            label_map[f"month {n}"] = f"Month {n}"
    forecast_month_labels = [label_map[f"month {n}"] for n in range(1, 4)]
    forecast_year = next((int(str(label).split()[-1]) for label in forecast_month_labels if str(label).split()[-1].isdigit()), 2026)
    if "Dry" in selected_cycle:
        st.markdown(f"<div style='font-weight:700; color:#1B5E20; margin:0.6rem 0 0.2rem 0;'><i class='material-symbols-outlined' style='font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;'>wb_sunny</i>Dry Season Forecast ({forecast_year})</div>", unsafe_allow_html=True)
        st.caption(f"Nagtanim noong huling bahagi ng {forecast_year - 1}, anihan Enero–Marso {forecast_year}.")
    else:
        st.markdown(f"<div style='font-weight:700; color:#1B5E20; margin:0.6rem 0 0.2rem 0;'><i class='material-symbols-outlined' style='font-size:16px; vertical-align:middle; margin-right:6px; color:#2563EB;'>water_drop</i>Wet Season Forecast ({forecast_year})</div>", unsafe_allow_html=True)
        st.caption(f"Paghahanda ng lupa Enero–Mayo {forecast_year}, anihan ng tag-ulan Hunyo–Disyembre {forecast_year}.")
    plot_df = sub.melt(id_vars=["municipality"], value_vars=["month 1", "month 2", "month 3"], var_name="month_key", value_name="price").assign(forecast_month=lambda d: d["month_key"].map(label_map)).groupby(["forecast_month", "municipality"], as_index=False)["price"].mean().dropna(subset=["price"])
    if plot_df.empty:
        st.info("Walang datos sa pinili mo.")
        return
    plot_df["price"] = pd.to_numeric(plot_df["price"], errors="coerce")
    plot_df = plot_df.dropna(subset=["price"])
    if plot_df.empty:
        st.info("Walang presyo sa pinili mo.")
        return
    plot_df["municipality"] = plot_df["municipality"].astype(str).str.title()
    fig = px.bar(plot_df, x="forecast_month", y="price", color="municipality", barmode="group", category_orders={"forecast_month": forecast_month_labels}, color_discrete_sequence=px.colors.qualitative.Set2, labels={"forecast_month": "Forecast Month", "price": "Price (\u20B1/kg)", "municipality": "Bayan"}, title=f"{rice_type} {classification} — {selected_cycle}")
    fig.update_layout(height=340, margin=dict(t=35, b=100, l=45, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Plus Jakarta Sans, sans-serif", size=11), legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5, font=dict(size=10), bgcolor="rgba(255,255,255,0.95)", bordercolor="#E5E7EB", borderwidth=1), yaxis=dict(gridcolor="#F3F4F6", showgrid=True), xaxis=dict(gridcolor="#F3F4F6", showgrid=False), title=dict(font=dict(size=13)), bargap=0.22, bargroupgap=0.10)
    fig.update_traces(marker=dict(cornerradius=6, line=dict(width=0)), hovertemplate="Bayan: %{fullData.name}<br>%{x}<br>\u20B1%{y:.2f}/kg<extra></extra>", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

# insight box
def _farmer_insight_box(text):
    return f'<div style="background:#F0FDF4; border-left:4px solid #1B5E20; padding:0.6rem 0.8rem; border-radius:8px; font-size:0.82rem; color:#14532D; margin-top:0.6rem; line-height:1.5;"><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#1B5E20;">lightbulb</i>{text}</div>'

def overview_page():
    dr = reload_dashboard_data()
    if not dr.has_provincial_data:
        st.markdown("""
            <style>
            .farmer-empty-card { background:#FFFFFF; border:1px solid #E0E0E0; border-radius:12px; padding:40px 32px; min-height:420px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.06); margin:24px auto; max-width:640px; }
            .farmer-empty-badge { display:inline-flex; align-items:center; gap:6px; background:#E8F5E9; color:#2E7D32; border:1px solid #C8E6C9; padding:6px 14px; border-radius:999px; font-size:0.82rem; font-weight:600; margin-top:16px; }
            </style>
            <div class="farmer-empty-card">
                <h1 style="margin:0; color:#1B5E20; font-size:1.9rem; font-weight:800;">Welcome sa PalaySense Bataan!</h1>
                <p style="margin:16px 0 0 0; color:#4B5563; font-size:1rem; line-height:1.7; max-width:520px;">Wala pang laman dito. Naghihintay lang kami ng bagong datos mula sa LGU — bumalik ka mamaya.</p>
                <div class="farmer-empty-badge"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:4px; color:#2E7D32;">info</i>Handa na ang system — naghihintay lang ng datos.</div>
            </div>
        """, unsafe_allow_html=True)
        _, btn_col, _ = st.columns([1, 1.2, 1])
        with btn_col:
            if st.button("Bumalik sa Home", icon=":material/home:", key="farmer_empty_to_home", type="primary", use_container_width=True):
                st.query_params["page"] = "home"; st.rerun()
        st.stop()
    if dr.has_provincial_data and not dr.has_forecasts:
        st.info("Ginagawa pa ang bagong hula sa presyo at ani — makikita mo pa rin ang lumang datos.")
    provincial_df = dr.provincial_df.copy()
    _prod_muni = getattr(dr, "municipal_production_df", None)
    municipality_df = _prod_muni.copy() if _prod_muni is not None and not getattr(_prod_muni, "empty", True) else dr.municipality_df.copy()
    df_municipal_forecasts = dr.df_municipal_forecasts.copy()
    forecast_3months_fancy = list(dr.forecast_3months_fancy)
    forecast_variety_3months = list(dr.forecast_variety_3months)
    forecast_quarterly_yield = list(dr.forecast_quarterly_yield)
    provincial_df = provincial_df.copy()
    if "date" not in provincial_df.columns or provincial_df.empty:
        provincial_df = pd.DataFrame(columns=["date", "year", "quarter"])
    else:
        provincial_df["date"] = pd.to_datetime(provincial_df["date"], errors="coerce")
        provincial_df = provincial_df.dropna(subset=["date"]).copy()
    provincial_sorted = provincial_df.sort_values("date").copy() if not provincial_df.empty else pd.DataFrame(columns=["date", "year", "quarter"])
    df = provincial_sorted.copy()
    if "date" in df.columns and not df.empty:
        df["year"] = df["date"].dt.year; df["quarter"] = df["date"].dt.quarter
    else:
        df["year"] = pd.Series(dtype="int64"); df["quarter"] = pd.Series(dtype="int64")
    muni = municipality_df.copy()
    if muni.empty:
        muni = pd.DataFrame(columns=["date", "year"])
    if "date" not in muni.columns:
        if "year" in muni.columns: muni["date"] = pd.to_datetime(muni["year"].astype(str) + "-06-15")
        else: muni["date"] = pd.Timestamp("2024-01-01")
    else:
        muni["date"] = pd.to_datetime(muni["date"], errors="coerce")
    muni["year"] = muni["date"].dt.year
    _yield_col = _pick_column(df, ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha"])
    if _yield_col is not None:
        quarterly_df = df.groupby(["year", "quarter"])[_yield_col].mean().reset_index()
    else:
        quarterly_df = pd.DataFrame(columns=["year", "quarter", "quarterly_yield_mt_per_ha"])
    if not quarterly_df.empty:
        quarterly_df["date_q"] = pd.PeriodIndex(quarterly_df["year"].astype(str) + "Q" + quarterly_df["quarter"].astype(str), freq="Q").to_timestamp()
        quarterly_df["quarter_label"] = "Q" + quarterly_df["quarter"].astype(str) + " " + quarterly_df["year"].astype(str)
        quarterly_df["Type"] = "Historical"
        quarterly_df = quarterly_df.sort_values("date_q")
    latest_q = quarterly_df.iloc[-1] if not quarterly_df.empty else None
    _fc_quarter_start = pd.Period(latest_q["date_q"], freq="Q") + 1 if latest_q is not None else pd.Period(pd.Timestamp.today(), freq="Q") + 1
    forecast_quarters = pd.period_range(start=_fc_quarter_start, periods=4, freq="Q")
    # top filter bar
    st.markdown("""<style>div[data-testid="stColumn"] { margin-top:0px !important; padding-top:0px !important; padding-bottom:0.2rem !important; } div[data-testid="stSelectbox"] { margin-top:0px !important; padding-top:0px !important; } div[data-testid="stSelectbox"] > div { border:none !important; background:transparent !important; box-shadow:none !important; } div[data-testid="stSelectbox"] div[role="combobox"] { border:1px solid #1B5E20 !important; background:#FFFFFF !important; border-radius:8px !important; box-shadow:none !important; }</style>""", unsafe_allow_html=True)
    st.markdown('<div style="margin-top:0.55rem; margin-bottom:0.2rem;"></div>', unsafe_allow_html=True)
    available_years = sorted(list(df["year"].dropna().unique()), reverse=False)
    if not available_years: available_years = [2024]
    st.session_state.setdefault("overview_start_year", available_years[0])
    st.session_state.setdefault("overview_end_year", available_years[-1])
    st.session_state.setdefault("overview_period", "ANNUAL")
    _valid_periods = ["ANNUAL", "SEMESTER 1", "SEMESTER 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"]
    if st.session_state.get("overview_period") not in _valid_periods: st.session_state["overview_period"] = "ANNUAL"
    st.session_state.setdefault("overview_selected_muni", "Lahat ng Bayan")
    # sidebar first to know current section for conditional filter
    QUICK_VIEW_GROUPS = [("PANGKALAHATAN", [("Pangkalahatan", "dashboard")]), ("DETALYE", [("Tantiya sa Presyo", "payments"), ("Inaasahang Ani", "eco"), ("Pambayang Forecast", "location_on")]), ("SUPORTA", [("Gabay at Payo", "lightbulb")])]
    _SIDEBAR_KEY_BY_LABEL = {label: key for _, items in QUICK_VIEW_GROUPS for (label, key) in items}
    _SIDEBAR_LABEL_BY_KEY = {key: label for label, key in _SIDEBAR_KEY_BY_LABEL.items()}
    _OLD_TO_NEW = {"Buong Dashboard": "Pangkalahatan", "Price Forecast": "Tantiya sa Presyo", "Yield Forecast": "Inaasahang Ani", "Municipal Forecast": "Pambayang Forecast", "Mga Payo": "Gabay at Payo", "Mga Payo (Advisories)": "Gabay at Payo"}
    st.session_state.setdefault("overview_section", "Pangkalahatan")
    if st.session_state.get("overview_section") in _OLD_TO_NEW:
        st.session_state["overview_section"] = _OLD_TO_NEW[st.session_state.get("overview_section")]
    _valid = {"Pangkalahatan","Tantiya sa Presyo","Inaasahang Ani","Pambayang Forecast","Gabay at Payo"}
    if st.session_state.get("overview_section") not in _valid:
        st.session_state["overview_section"] = "Pangkalahatan"
    _current_section_for_filter = st.session_state.get("overview_section", "Pangkalahatan")
    _is_municipal_section = _current_section_for_filter == "Pambayang Forecast"
    # top filter bar - municipality hidden on Buong Dashboard, visible on details
    if _is_municipal_section:
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4, gap="small")
    else:
        filter_col1, filter_col2, filter_col3 = st.columns([1, 1, 1], gap="small")
        filter_col4 = None
    with filter_col1:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">TAON (MULA)</div>', unsafe_allow_html=True)
        selected_start_year = st.selectbox("Simula Taon", options=available_years, key="overview_start_year", label_visibility="collapsed")
    with filter_col2:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">HANGGANG</div>', unsafe_allow_html=True)
        selected_end_year = st.selectbox("Hanggang Taon", options=available_years, key="overview_end_year", label_visibility="collapsed")
    with filter_col3:
        st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">PANAHON</div>', unsafe_allow_html=True)
        selected_period = st.selectbox("Panahon", options=["ANNUAL", "SEMESTER 1", "SEMESTER 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"], key="overview_period", label_visibility="collapsed")
    _muni_label_col = _pick_column(muni, ["municipality", "Municipality", "Mun", "Area"])
    all_munis_options = sorted(muni[_muni_label_col].dropna().unique()) if _muni_label_col is not None else []
    muni_options = ["Lahat ng Bayan"] + all_munis_options
    if st.session_state["overview_selected_muni"] not in muni_options: st.session_state["overview_selected_muni"] = "Lahat ng Bayan"
    if _is_municipal_section and filter_col4 is not None:
        with filter_col4:
            st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">BAYAN</div>', unsafe_allow_html=True)
            selected_muni = st.selectbox("Bayan", options=muni_options, key="overview_selected_muni", label_visibility="collapsed")
    else:
        selected_muni = st.session_state.get("overview_selected_muni", "Lahat ng Bayan")
        # keep state in sync but hide dropdown on Buong Dashboard
    selected_years = list(range(selected_start_year, selected_end_year + 1))
    selected_munis = [selected_muni] if selected_muni != "Lahat ng Bayan" else all_munis_options
    # visible tooltip for farmers - not techy, always shown
    if _current_section_for_filter == "Buong Dashboard":
        st.markdown("""
        <div style="background:#FFF8E1; border:1px solid #FFE082; border-left:6px solid #F9A825; border-radius:10px; padding:10px 14px; margin:8px 0 10px 0; display:flex; gap:10px; align-items:flex-start;">
            <i class="material-symbols-outlined" style="font-size:20px; color:#F57F17; margin-top:1px;">info</i>
            <div style="font-size:0.82rem; line-height:1.5; color:#5D4037;">
                <b style="color:#E65100;">Paano gamitin?</b> Ang nasa taas (<b>Pangkalahatan</b>) ay presyo at ani ng <b>pang-buong Bataan</b>. Para makita ang <b>bawat Munisipyo </b>, pindutin sa kaliwa ang <b>Pambayang Forecast</b> at piliin ang bayan. 
            </div>
        </div>
        """, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("""<style>.ov-qv-group { font-size:0.68rem !important; letter-spacing:0.8px !important; color:#A8C3B0 !important; margin:1.0rem 0 0.45rem 0 !important; font-weight:700 !important; text-align:left !important; } section[data-testid="stSidebar"] .stButton > button { padding:10px 12px 10px 14px !important; min-height:46px !important; line-height:1.3 !important; font-size:0.86rem !important; gap:10px !important; margin:5px 0 !important; border-radius:10px !important; justify-content:flex-start !important; text-align:left !important; align-items:center !important; } section[data-testid="stSidebar"] .stButton > button > div { justify-content:flex-start !important; text-align:left !important; } section[data-testid="stSidebar"] .stButton > button p { text-align:left !important; width:100% !important; } section[data-testid="stSidebar"] > div:first-child { padding-top:0.9rem !important; gap:8px !important; } section[data-testid="stSidebar"] hr.ps-side-divider { margin:0.35rem 0 !important; } @media (max-width: 768px) { section[data-testid="stSidebar"] { display:none !important; } } div[data-testid="stElementContainer"]:has(.ov-phone-marker) { display:none !important; } div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] { display:none !important; position:fixed !important; top:10px !important; right:12px !important; z-index:1001 !important; } div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] .stButton > button { background:linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%) !important; color:#FFFFFF !important; border:1px solid rgba(255,255,255,0.25) !important; border-radius:12px !important; padding:8px 14px !important; height:42px !important; min-height:42px !important; font-weight:700 !important; font-size:0.85rem !important; box-shadow:0 4px 14px rgba(27,94,32,0.35) !important; } div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] .stButton > button p { color:#FFFFFF !important; font-weight:700 !important; } @media (max-width: 768px) { div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] { display:flex !important; } } @media (min-width: 769px) { div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] { display:none !important; } }</style>""", unsafe_allow_html=True)
        for grp_label, items in QUICK_VIEW_GROUPS:
            st.markdown(f'<p class="ov-qv-group">{grp_label}</p>', unsafe_allow_html=True)
            for label, icon in items:
                is_active = (st.session_state.get("overview_section") == label)
                if st.button(label, icon=f":material/{icon}:" if icon else None, use_container_width=True, type="primary" if is_active else "secondary", key=f"ov_qv_{icon}"):
                    st.session_state["overview_section"] = label; st.rerun()
        section_choice = st.session_state.get("overview_section", "Pangkalahatan")
    st.session_state.setdefault("ov_mobile_nav_open", False)
    st.markdown('<div class="ov-phone-marker" style="display:none;"></div>', unsafe_allow_html=True)
    _is_open = st.session_state.get("ov_mobile_nav_open", False)
    _lbl = "Isara" if _is_open else "Menu"; _ico = "close" if _is_open else "menu"
    if st.button(_lbl, icon=f":material/{_ico}:", key="ov_phone_toggle", type="primary"):
        st.session_state["ov_mobile_nav_open"] = not _is_open; st.rerun()
    if st.session_state.get("ov_mobile_nav_open", False):
        st.markdown("""<style>@media (max-width: 768px) { section[data-testid="stSidebar"] { display:flex !important; position:fixed !important; left:0 !important; top:0 !important; bottom:0 !important; width:78% !important; max-width:300px !important; min-width:260px !important; z-index:1000 !important; box-shadow:4px 0 24px rgba(0,0,0,0.35) !important; overflow-y:auto !important; } }</style>""", unsafe_allow_html=True)
    show_all = section_choice == "Pangkalahatan"
    if selected_years:
        provincial_year = df[df["year"].isin(selected_years)].copy().sort_values("date")
        muni_filtered = muni[muni["year"].isin(selected_years)]
    else:
        provincial_year = df[df["year"] == available_years[0]].copy().sort_values("date")
        muni_filtered = muni[muni["year"] == available_years[0]]
    if selected_munis and _muni_label_col is not None:
        muni_filtered = muni_filtered[muni_filtered[_muni_label_col].isin(selected_munis)]
    else:
        muni_filtered = muni_filtered.iloc[0:0]
    if selected_years and not quarterly_df.empty:
        quarterly_df = quarterly_df[quarterly_df["year"].isin(selected_years)].copy()
    fc_fancy_s, fc_regular_s = _align_forecast_arrays(forecast_3months_fancy, forecast_variety_3months)
    _hist_last = pd.to_datetime(provincial_df["date"], errors="coerce").max()
    _today_month = pd.Timestamp.today().to_period("M").to_timestamp()
    if not provincial_year.empty:
        latest_selected = provincial_year.iloc[-1]
        avg_fancy_price = _safe_column(provincial_year, "fancy_palay_price").mean()
        avg_regular_price = _safe_column(provincial_year, "other_variety_price").mean()
        _data_start = (pd.to_datetime(latest_selected["date"]) + pd.DateOffset(months=1)).to_period("M").to_timestamp()
        if pd.isna(_data_start):
            _data_start = (_hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp() if not pd.isna(_hist_last) else _today_month
    else:
        avg_fancy_price = _safe_column(df, "fancy_palay_price").mean() if not df.empty else np.nan
        avg_regular_price = _safe_column(df, "other_variety_price").mean() if not df.empty else np.nan
        if not pd.isna(_hist_last):
            _data_start = (_hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp()
        else:
            _data_start = _today_month
    _forecast_start = _data_start
    _fc_len = len(fc_fancy_s) if len(fc_fancy_s) > 0 else 6
    forecast_months = pd.date_range(start=_forecast_start, periods=_fc_len, freq="MS")
    if len(forecast_months) > 1:
        forecast_range_label = f"{forecast_months[0].strftime('%B %Y')} \u2013 {forecast_months[-1].strftime('%B %Y')}"
    elif len(forecast_months) > 0:
        forecast_range_label = forecast_months[0].strftime("%B %Y")
    else:
        forecast_range_label = "N/A"
    _today_m = _today_month
    if len(forecast_months) > 0 and _today_m in forecast_months:
        next_month_name = _today_m.strftime("%B %Y")
    elif len(forecast_months) > 0:
        next_month_name = forecast_months[-1].strftime("%B %Y")
    else:
        next_month_name = "N/A"
    last_avail_month = forecast_months[-1].strftime("%B %Y") if len(forecast_months) > 0 else "N/A"
    is_awaiting_lgu = False
    if len(forecast_months) > 0 and _today_m > forecast_months[-1]:
        is_awaiting_lgu = True
    if len(forecast_months) == len(fc_fancy_s) and not fc_fancy_s.empty:
        fancy_indexed = pd.Series(fc_fancy_s.values, index=forecast_months)
    elif len(forecast_3months_fancy):
        fancy_indexed = pd.Series(list(forecast_3months_fancy), index=forecast_months[:len(forecast_3months_fancy)])
    else:
        fancy_indexed = pd.Series(dtype=float)
    if len(forecast_months) == len(fc_regular_s) and not fc_regular_s.empty:
        regular_indexed = pd.Series(fc_regular_s.values, index=forecast_months)
    elif len(forecast_variety_3months):
        regular_indexed = pd.Series(list(forecast_variety_3months), index=forecast_months[:len(forecast_variety_3months)])
    else:
        regular_indexed = pd.Series(dtype=float)
    def _forecast_value_for_month(indexed, fallback_list):
        if not indexed.empty and _today_m in indexed.index:
            v = indexed.loc[_today_m]
            if not pd.isna(v): return float(v)
        s = indexed.dropna()
        if not s.empty: return float(s.iloc[-1])
        return _safe_index(fallback_list, 0)
    _fancy_current = _forecast_value_for_month(fancy_indexed, forecast_3months_fancy)
    _regular_current = _forecast_value_for_month(regular_indexed, forecast_variety_3months)
    next_fancy_pred = _fancy_current; next_regular_pred = _regular_current
    percent_change_fancy = _pct_change(_fancy_current, avg_fancy_price) or 0.0
    percent_change_regular = _pct_change(_regular_current, avg_regular_price) or 0.0
    avg_yield_forecast = _safe_mean(forecast_quarterly_yield)
    try:
        fc_fancy_vals = [float(x) for x in forecast_3months_fancy if pd.notna(x)]
        fc_regular_vals = [float(x) for x in forecast_variety_3months if pd.notna(x)]
        if fc_fancy_vals and len(forecast_months) >= len(fc_fancy_vals):
            _fmax_idx = int(np.argmax(fc_fancy_vals)); _fmin_idx = int(np.argmin(fc_fancy_vals))
            _fmax_month = forecast_months[_fmax_idx].strftime("%b %Y") if _fmax_idx < len(forecast_months) else "N/A"
            _fmin_month = forecast_months[_fmin_idx].strftime("%b %Y") if _fmin_idx < len(forecast_months) else "N/A"
            _fmax_val = fc_fancy_vals[_fmax_idx]; _fmin_val = fc_fancy_vals[_fmin_idx]
        else:
            _fmax_month = _fmin_month = "N/A"; _fmax_val = _fmin_val = 0
        fc_yield_vals = [float(x) for x in forecast_quarterly_yield if pd.notna(x)]
        if fc_yield_vals:
            _ymax = max(fc_yield_vals); _ymin = min(fc_yield_vals)
        else:
            _ymax = _ymin = 0
    except Exception:
        _fmax_month = _fmin_month = "N/A"; _fmax_val = _fmin_val = _ymax = _ymin = 0
    # ---- surgical Pangkalahatan hero context (DETALYE untouched) ----
    try:
        _p_fancy = list(forecast_3months_fancy)[:6]
        _p_regular = list(forecast_variety_3months)[:6]
        while len(_p_fancy) < len(forecast_months):
            _p_fancy.append(np.nan)
        while len(_p_regular) < len(forecast_months):
            _p_regular.append(np.nan)
        _price_ctx = _build_price_context(_p_fancy, _p_regular, forecast_months)
        try:
            _pf_y = load_provincial_forecasts()
            _y_labs = _pf_y[_pf_y["forecast_type"]=="yield"]["period_label"].tolist() if not _pf_y.empty else ["Q4 2026", "Q1 2027"]
        except Exception:
            _y_labs = ["Q4 2026", "Q1 2027"]
        _harvest_ctx = _harvest_interpretation(forecast_quarterly_yield, _y_labs)
        _next_yield = float(pd.Series(forecast_quarterly_yield).dropna().iloc[0]) if forecast_quarterly_yield and len(pd.Series(forecast_quarterly_yield).dropna())>0 else None
    except Exception:
        _price_ctx = {"fancy": {"vals": [], "labels": [], "lowest": None, "highest": None, "trend_sentence": "Forecast data is being prepared.", "recover_sentence": "No data"}, "regular": {"vals": [], "labels": [], "lowest": None, "highest": None, "trend_sentence": "", "recover_sentence": ""}}
        _harvest_ctx = {"avg": None, "lo": None, "hi": None, "sentence": ""}
        _next_yield = None
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap'); .main-container { font-family:'Poppins', sans-serif; padding:0 1% 20px 1%; background:#F8FAF9; } .block-container { padding-left:1rem !important; padding-right:1rem !important; padding-top:2rem !important; padding-bottom:0rem !important; } .hero-banner { background:linear-gradient(135deg, #1B5E20 0%, #2E7D32 40%, #388E3C 100%); padding:35px 40px; border-radius:20px; color:white; margin-bottom:28px; box-shadow:0 12px 35px rgba(27,94,32,0.2); position:relative; overflow:hidden; margin-top:-2.08rem; } .hero-title { font-size:clamp(1.8rem, 2.8vw, 2.5rem); font-weight:900; margin-bottom:8px; letter-spacing:-0.5px; } .hero-subtitle { font-size:1rem; opacity:0.92; line-height:1.6; font-weight:400; } .hero-badge { display:inline-block; background:rgba(255,255,255,0.15); padding:4px 16px; border-radius:20px; font-size:0.75rem; font-weight:600; margin-top:8px; backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.1); } .forecast-bar-text { color:#1B5E20 !important; font-weight:700 !important; font-size:0.85rem !important; letter-spacing:0.3px; white-space:nowrap; display:flex; align-items:center; gap:8px; } .kpi-row { display:grid; grid-template-columns:repeat(auto-fit, minmax(220px, 1fr)); gap:16px; margin-bottom:16px; } .metric-card { background:#FFFFFF; padding:20px 22px; border-radius:16px; border:1px solid rgba(46,125,50,0.08); position:relative; overflow:hidden; } .metric-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg, #2E7D32, #66BB6A); } .metric-title { font-size:0.8rem; font-weight:600; color:#6B7280; text-transform:uppercase; letter-spacing:0.5px; } .metric-data { font-size:1.8rem; font-weight:800; color:#1B5E20; margin:4px 0 2px 0; letter-spacing:-0.5px; } .metric-footer { font-size:0.7rem; color:#9CA3AF; font-weight:500; } .metric-change-positive { color:#16A34A; font-weight:700; } .metric-change-negative { color:#DC2626; font-weight:700; } .component-card { background:#FFFFFF; border-radius:16px; border:1px solid rgba(0,0,0,0.05); padding:22px 24px 24px 24px; margin-bottom:20px; box-shadow:0 2px 8px rgba(0,0,0,0.03); } .component-header { font-size:1.05rem; font-weight:700; color:#111827; } .component-desc { font-size:0.8rem; color:#6B7280; margin-bottom:16px; font-weight:400; } .advisory-container { display:flex; flex-direction:column; gap:12px; width:100%; margin-top:4px; } .advisory-card { display:flex; align-items:flex-start; padding:16px 20px; border-radius:12px; background:#FFFFFF; border:1px solid #E5E7EB; } .card-status { border-left:4px solid #1B5E20; background:linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%); } .card-marketing { border-left:4px solid #16A34A; background:linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%); } .card-notice { border-left:4px solid #EA580C; background:linear-gradient(135deg, #FFF7ED 0%, #FFFFFF 100%); } .card-optimization { border-left:4px solid #7C3AED; background:linear-gradient(135deg, #F5F3FF 0%, #FFFFFF 100%); } .card-icon { font-size:1.2rem; margin-right:14px; margin-top:2px; } .card-body { flex:1; font-size:0.88rem; line-height:1.6; color:#374151; } .card-label { font-weight:700; margin-right:4px; } .label-status { color:#1B5E20; } .label-marketing { color:#15803D; } .label-notice { color:#C2410C; } .label-optimization { color:#6D28D9; } .highlight-text { font-weight:700; color:#1B5E20; background:rgba(27,94,32,0.06); padding:1px 6px; border-radius:4px; } .kailan-card { background:linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%); border:1px solid #C8E6C9; border-left:6px solid #1B5E20; border-radius:16px; padding:18px 20px; margin-bottom:16px; }</style>""", unsafe_allow_html=True)
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    if show_all:
        # surgical farmer hero - Pangkalahatan only, DETALYE unchanged
        try:
            _hero_label = forecast_months[0].strftime("%b %Y") if len(forecast_months) > 0 else "Forecast"
        except Exception:
            _hero_label = "Forecast"
        st.markdown(f"""<div style="background: linear-gradient(90deg, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.82) 45%, rgba(255,255,255,0.10) 100%), url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=2070"); background-size:cover; background-position:center; border-radius:16px; padding:22px 28px; border:1px solid #E8EFDE; margin-bottom:16px; display:flex; align-items:center; gap:12px;"><div style="width:38px; height:38px; background:#E8F5E9; border-radius:10px; display:flex; align-items:center; justify-content:center; border:1px solid #C8E6C9;"><i class="material-symbols-outlined" style="font-size:20px; color:#2E7D32;">eco</i></div><div><div style="font-family:'DM Serif Display', serif; font-size:20px; color:#1B4332; font-weight:400; margin:0;">Good day, Farmer!</div><div style="font-size:12px; color:#3A4D3D; margin-top:2px;">Here's your palay outlook for Bataan &bull; {_hero_label} forecast &bull; {len(selected_munis) if selected_munis else 0} bayan</div></div></div>""", unsafe_allow_html=True)
    muni_badge = selected_muni if selected_muni != "Lahat ng Bayan" else "Lahat ng Bayan sa Bataan"
    st.markdown(f"""<div style="display:inline-flex; align-items:center; gap:6px; background:#E8F5E9; border:1px solid #C8E6C9; color:#1B5E20; padding:6px 14px; border-radius:999px; font-size:0.78rem; font-weight:700; margin-bottom:14px;"><i class="material-symbols-outlined" style="font-size:16px; color:#1B5E20;">location_on</i>Tinitingnan: {muni_badge} &bull; {selected_start_year}–{selected_end_year}</div>""", unsafe_allow_html=True)
    top5_municipalities = dl.get_top_5_producing_municipalities(muni_filtered, selected_years)
    total_production = dl.get_total_production(provincial_year, selected_years)
    if total_production is None: total_production = dl.get_total_production(muni_filtered, selected_years)
    prod_val = total_production if total_production is not None else 0
    if show_all:
        # surgical top cards - farmer style, DETALYE untouched
        _ctx = _price_ctx.get("regular", _price_ctx.get("fancy")) if '_price_ctx' in locals() and _price_ctx else None
        _vals = _ctx["vals"] if _ctx else []
        _labs = _ctx["labels"] if _ctx else []
        try:
            _prim_val = float(_vals[0]) if _vals and len(_vals)>0 and not __import__("pandas").isna(_vals[0]) else 0
            _prim_lab = _labs[0] if _labs else next_month_name
            _trend = _ctx["trend_sentence"] if _ctx else ""
            _next_vals = _vals[1:4] if len(_vals)>=4 else (_vals[1:] if len(_vals)>1 else [])
            _next_labs = _labs[1:4] if len(_labs)>=4 else (_labs[1:] if len(_labs)>1 else [])
        except Exception:
            _prim_val=0; _prim_lab=next_month_name; _trend=""; _next_vals=[]; _next_labs=[]
        c1, c2 = st.columns([1.15, 0.85], gap="medium")
        with c1:
            # build inner html for price card (single markdown to avoid empty white bars)
            if _next_vals:
                _cols_html = "".join([f'<div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">{lab}</div><div style="font-size:13px; font-weight:800; color:#0F2A1A;">\u20B1{val:.2f}/kg</div></div>' for lab,val in zip(_next_labs,_next_vals)])
                _cols_block = f'<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:10px; background:#FAFAF7; border:1px solid #F0EDE0; border-radius:10px; padding:10px;">{_cols_html}</div>'
            else:
                _cols_block = ""
            st.markdown(f'<div style="background:white; border:1px solid #E8EFDE; border-radius:16px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,0.03);"><div style="font-size:13px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:8px;"><span style="width:32px; height:32px; background:#E8F5E9; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; border:1px solid #C8E6C9;"><i class="material-symbols-outlined" style="font-size:18px; color:#2E7D32;">payments</i></span> Palay Price Forecast</div><div style="font-family:DM Serif Display, serif; font-size:28px; color:#0F2A1A; margin:6px 0 2px 0;">\u20B1{_prim_val:.2f}/kg</div><div style="font-size:12px; color:#6B7C6E;">regular palay \u2022 {_prim_lab} forecast</div><div style="font-size:12px; color:#1B7A3D; font-weight:600; margin-top:6px; display:flex; align-items:center; gap:4px;"><i class="material-symbols-outlined" style="font-size:14px;">trending_up</i> {_trend}</div>{_cols_block}</div>', unsafe_allow_html=True)
        with c2:
            # merged harvest card - single markdown to avoid empty bars
            if _next_yield is not None:
                if _harvest_ctx.get("lo") is not None:
                    _harvest_inner = f'<div style="font-family:DM Serif Display, serif; font-size:26px; color:#0F2A1A; margin:4px 0 2px 0;">{_next_yield:.2f} MT/ha</div><div style="font-size:12px; color:#6B7C6E;">Forecast for {_y_labs[0] if _y_labs else "next harvest"}</div><div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:10px; background:white; border:1px solid #F2E8C8; border-radius:10px; padding:10px;"><div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">Forecast range</div><div style="font-size:12px; font-weight:800; color:#0F2A1A;">{_harvest_ctx["lo"]:.2f} \u2013 {_harvest_ctx["hi"]:.2f} MT/ha</div></div><div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">Trend</div><div style="font-size:12px; font-weight:600; color:#1B7A3D;">{_harvest_ctx["sentence"]}</div></div></div>'
                else:
                    _harvest_inner = f'<div style="font-family:DM Serif Display, serif; font-size:26px; color:#0F2A1A; margin:4px 0 2px 0;">{_next_yield:.2f} MT/ha</div><div style="font-size:12px; color:#6B7C6E;">Forecast for {_y_labs[0] if _y_labs else "next harvest"}</div>'
            else:
                _harvest_inner = '<div style="font-size:13px; color:#6B7C6E;">No data</div>'
            st.markdown(f'<div style="background:#FFFEF8; border:1px solid #F2E8C8; border-radius:16px; padding:16px; box-shadow:0 2px 10px rgba(0,0,0,0.03);"><div style="font-size:13px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:8px;"><span style="width:32px; height:32px; background:#FFF8E1; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; border:1px solid #FFE082;"><i class="material-symbols-outlined" style="font-size:18px; color:#F9A825;">eco</i></span> Expected Harvest (Ani)</div>{_harvest_inner}</div>', unsafe_allow_html=True)
        try:
            _fig_preview = _farmer_price_chart(forecast_months, _vals, color="#1B5E20")
            st.plotly_chart(_fig_preview, use_container_width=True, config={"displayModeBar": False})
            if _ctx and _ctx.get("lowest") and _ctx.get("highest"):
                _lo_lab,_lo_val = _ctx["lowest"]; _hi_lab,_hi_val = _ctx["highest"]
                if _lo_val is not None and _hi_val is not None:
                    st.markdown(f'<div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:8px;"><div style="background:white; border:1px solid #E8EFDE; border-left:3px solid #C62828; border-radius:10px; padding:10px;"><div style="font-size:11px; font-weight:700; color:#6B7C6E;">Lowest forecast</div><div style="font-size:12px; font-weight:600;">{_lo_lab}</div><div style="font-size:14px; font-weight:800;">₱{_lo_val:.2f}/kg</div></div><div style="background:white; border:1px solid #E8EFDE; border-left:3px solid #2E7D32; border-radius:10px; padding:10px;"><div style="font-size:11px; font-weight:700; color:#6B7C6E;">Highest forecast</div><div style="font-size:12px; font-weight:600;">{_hi_lab}</div><div style="font-size:14px; font-weight:800;">₱{_hi_val:.2f}/kg</div></div></div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="background:#E8F5E9; border:1px solid #C8E6C9; border-radius:8px; padding:8px 12px; margin-top:8px; font-size:12px; color:#1B5E20; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="font-size:16px;">lightbulb</i> {_ctx["recover_sentence"]}</div>', unsafe_allow_html=True)
        except Exception:
            pass
        st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:6px; color:#1B5E20;">show_chart</i>Trend ng Presyo at Ani (Forecast)</div><div class="component-desc">Forecast trend ng presyo at ani. Piliin kung Presyo o Inaasahang Ani ang nais ipakita.</div>', unsafe_allow_html=True)
        try:
            trend_choice = st.segmented_control("Trend", options=["Presyo", "Ani"], default="Presyo", key="essentials_trend_toggle")
            if trend_choice is None: trend_choice = "Presyo"
        except Exception:
            trend_choice = st.radio("Trend", options=["Presyo", "Ani"], horizontal=True, key="essentials_trend_toggle_radio")
        benchmark_option = "Wala"
        if trend_choice == "Presyo":
            _fig = _price_forecast_chart(provincial_df, forecast_3months_fancy, forecast_variety_3months, benchmark_option=benchmark_option)
            st.plotly_chart(_fig, use_container_width=True, key="essentials_price_trend")
            try:
                _f = float(forecast_3months_fancy[0]) if forecast_3months_fancy and len(forecast_3months_fancy) > 0 else None
                _r = float(forecast_variety_3months[0]) if forecast_variety_3months and len(forecast_variety_3months) > 0 else None
                if _f is not None and _r is not None:
                    if _f > _r + 1: _msg = f"Fancy \u20B1{_f:.2f}/kg, Regular \u20B1{_r:.2f}/kg — mas mataas ang Fancy, mas malaki ang kita sa Fancy."
                    else: _msg = f"Fancy \u20B1{_f:.2f}/kg, Regular \u20B1{_r:.2f}/kg — halos magkapareho ang presyo."
                else: _msg = "Pag pataas ang guhit, tataas ang presyo. Pag pababa, bababa."
                st.markdown(_farmer_insight_box(_msg), unsafe_allow_html=True)
            except Exception:
                st.markdown(_farmer_insight_box("Pag pataas ang guhit, tataas ang presyo."), unsafe_allow_html=True)
        else:
            _fig = _yield_forecast_chart(provincial_df, forecast_quarterly_yield, benchmark_option=benchmark_option)
            st.plotly_chart(_fig, use_container_width=True, key="essentials_yield_trend")
            try:
                _hist_avg = float(provincial_df["quarterly_yield_mt_per_ha"].dropna().mean()) if "quarterly_yield_mt_per_ha" in provincial_df.columns else None
                _next_y = float(forecast_quarterly_yield[0]) if forecast_quarterly_yield and len(forecast_quarterly_yield) > 0 else None
                if _hist_avg is not None and _next_y is not None:
                    _diff = _next_y - _hist_avg
                    if _diff > 0.12: _msg = f"Tataas ng {_diff:.2f} MT/ha vs dati ({_hist_avg:.2f} → {_next_y:.2f}). Magandang magtanim."
                    elif _diff < -0.12: _msg = f"Bababa ng {abs(_diff):.2f} MT/ha ({_hist_avg:.2f} → {_next_y:.2f}). Mag-ingat sa gastos sa abono."
                    else: _msg = f"Halos pareho lang ang ani ({_next_y:.2f} MT/ha) vs dati ({_hist_avg:.2f}). Walang masyadong pagbabago."
                else: _msg = "Pag pataas ang guhit, mas marami ang aanihin."
                st.markdown(_farmer_insight_box(_msg), unsafe_allow_html=True)
            except Exception:
                st.markdown(_farmer_insight_box("Pag pataas ang guhit, mas marami ang aanihin."), unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:6px; color:#1B5E20;">lightbulb</i>Pangunahing Payo</div><div class="component-desc">Buod ng rekomendasyon batay sa forecast ng presyo at ani.</div>', unsafe_allow_html=True)
        if not muni_filtered.empty:
            if percent_change_fancy > 5:
                _trade_title = "Itago muna ang Fancy"; _trade_body = f"Tataas pa ang Fancy sa <span class='highlight-text'>\u20B1{next_fancy_pred:.2f}/kg</span> — mas kikita kung sa {_fmax_month} ibebenta."
            elif percent_change_fancy < -5:
                _trade_title = "Benta na ang Fancy"; _trade_body = f"Bababa ang Fancy sa <span class='highlight-text'>\u20B1{next_fancy_pred:.2f}/kg</span>. Mas maganda ibenta ngayon bago bumaba pa."
            else:
                _trade_title = "Magmasid muna"; _trade_body = f"Hindi gumagalaw ang presyo (Fancy <span class='highlight-text'>\u20B1{next_fancy_pred:.2f}/kg</span>, Regular <span class='highlight-text'>\u20B1{next_regular_pred:.2f}/kg</span>). Magmasid muna bago magbenta nang maramihan."
            if _ymax > 0 and _ymin > 0:
                if _ymax - _ymin > 0.3:
                    _yield_title = "Maghanda — paiba-iba ang aanihin"; _yield_body = f"Pinakamataas <span class='highlight-text'>{_ymax:.2f} MT/ha</span>, pinakamababa <span class='highlight-text'>{_ymin:.2f} MT/ha</span> — magtabi ng abono at reserba para sa mga buwang mahina ang ani."
                elif avg_yield_forecast >= 4.5:
                    _yield_title = "Maganda ang ani — ituloy ang plano"; _yield_body = f"Avg <span class='highlight-text'>{avg_yield_forecast:.2f} MT/ha</span> lagpas sa target ng DA na 4.50. Sapat ang supply."
                else:
                    _yield_title = "Medyo mababa ang ani"; _yield_body = f"Avg <span class='highlight-text'>{avg_yield_forecast:.2f} MT/ha</span> — magtipid sa gastos, ayusin ang patubig."
            else:
                _yield_title = "Walang hula"; _yield_body = "Wala pang sapat na datos para sa payo sa ani."
            st.markdown(f"""<div class="advisory-container"><div class="advisory-card card-marketing"><div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20;">payments</i></div><div class="card-body"><span class="card-label label-marketing">{_trade_title}:</span> {_trade_body}</div></div><div class="advisory-card card-optimization"><div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20;">eco</i></div><div class="card-body"><span class="card-label label-optimization">{_yield_title}:</span> {_yield_body}</div></div></div>""", unsafe_allow_html=True)
        else:
            st.warning("Walang sapat na datos para makapagbigay ng payo sa pinili mo.")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("""<div style="text-align:center; padding:10px 0 5px 0; font-size:0.75rem; color:#9CA3AF; border-top:1px solid #E5E7EB; margin-top:10px;"><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#9CA3AF;">agriculture</i>Bataan Rice Monitoring System &bull; v2.0</div>""", unsafe_allow_html=True)
        return
    st.markdown('<div class="main-container">', unsafe_allow_html=True)
    if section_choice == "Tantiya sa Presyo":
        st.markdown("""<div style="background:linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%); padding:22px 28px; border-radius:16px; color:white; margin-bottom:18px;"><div style="font-size:1.5rem; font-weight:800;"><i class="material-symbols-outlined" style="font-size:22px; vertical-align:middle; margin-right:8px; color:white;">payments</i>Tantiya sa Presyo</div><div style="font-size:0.9rem; opacity:0.92; margin-top:6px;">Forecast ng presyo sa lalawigan — Fancy vs Regular, kasama ang historical trend at 6-month forecast.</div></div>""", unsafe_allow_html=True)
        try:
            benchmark_option = st.segmented_control("Batayan:", options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"], default="Wala", key="price_detail_benchmark")
            if benchmark_option is None: benchmark_option = "Wala"
        except Exception:
            benchmark_option = st.radio("Batayan:", options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"], horizontal=True, key="price_detail_benchmark_radio")
        _pc1, _pc2 = st.columns(2, gap="medium")
        with _pc1:
            st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">show_chart</i>Historical Price Trend</div><div class="component-desc">Historical na presyo ng Fancy at Regular na palay.</div>', unsafe_allow_html=True)
            _fig = _price_historical_chart(provincial_year, selected_period, benchmark_option)
            st.plotly_chart(_fig, use_container_width=True, key="detail_price_hist")
            st.markdown(_farmer_insight_box("Ito ang dating presyo. Pag pataas ang guhit, tumataas ang presyo. Ihambing sa presyo ng NFA para malaman kung lugi o panalo."), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with _pc2:
            st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">query_stats</i>6-Month Price Forecast (Fancy vs Regular)</div><div class="component-desc">Forecast ng presyo para sa susunod na 6 na buwan.</div>', unsafe_allow_html=True)
            _fig2 = _price_forecast_chart(provincial_df, forecast_3months_fancy, forecast_variety_3months, benchmark_option)
            st.plotly_chart(_fig2, use_container_width=True, key="detail_price_fc")
            st.markdown(_farmer_insight_box(f"Fancy \u20B1{next_fancy_pred:.2f}/kg, Regular \u20B1{next_regular_pred:.2f}/kg sa {next_month_name}. NFA floor: \u20B119.00 (Regular) / \u20B123.75 (Fancy)."), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i>Dagdag na Impormasyon</div>', unsafe_allow_html=True)
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"<div style='background:#F0FDF4; border:1px solid #C8E6C9; border-radius:10px; padding:12px;'><div style='font-weight:700; color:#1B5E20; font-size:0.85rem;'><i class='material-symbols-outlined' style='font-size:14px; vertical-align:middle; margin-right:4px;'>trending_up</i>Agwat ng Fancy at Regular</div><div style='font-size:0.85rem; color:#374151; margin-top:4px;'>Gap: \u20B1{abs(next_fancy_pred - next_regular_pred):.2f}/kg — {'Mas mataas ang Fancy' if next_fancy_pred > next_regular_pred else 'Mas mataas ang Regular o halos pareho'}</div></div>", unsafe_allow_html=True)
        with col_b:
            st.markdown(f"<div style='background:#FFF7ED; border:1px solid #FDBA74; border-radius:10px; padding:12px;'><div style='font-weight:700; color:#9A3412; font-size:0.85rem;'><i class='material-symbols-outlined' style='font-size:14px; vertical-align:middle; margin-right:4px;'>flag</i>Kumpara sa Presyo ng NFA</div><div style='font-size:0.85rem; color:#374151; margin-top:4px;'>Regular \u20B1{next_regular_pred:.2f} vs \u20B119.00 — {'lagpas sa presyo ng NFA, puwedeng ibenta' if next_regular_pred >= 19 else 'mababa sa presyo ng NFA, malulugi pag binenta'}</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    elif section_choice == "Inaasahang Ani":
        st.markdown("""<div style="background:linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%); padding:22px 28px; border-radius:16px; color:white; margin-bottom:18px;"><div style="font-size:1.5rem; font-weight:800;"><i class="material-symbols-outlined" style="font-size:22px; vertical-align:middle; margin-right:8px; color:white;">eco</i>Inaasahang Ani</div><div style="font-size:0.9rem; opacity:0.92; margin-top:6px;">Forecast ng ani — historical na datos at trend kada quarter at taon.</div></div>""", unsafe_allow_html=True)
        try:
            benchmark_option = st.segmented_control("Batayan:", options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"], default="Wala", key="yield_detail_benchmark")
            if benchmark_option is None: benchmark_option = "Wala"
        except Exception:
            benchmark_option = st.radio("Batayan:", options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"], horizontal=True, key="yield_detail_benchmark_radio")
        _yc1, _yc2 = st.columns(2, gap="medium")
        with _yc1:
            st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">show_chart</i>Historical Yield Trend</div><div class="component-desc">Historical na ani kada ektarya (MT/ha).</div>', unsafe_allow_html=True)
            _fig = _yield_historical_chart(provincial_year, selected_period, benchmark_option)
            st.plotly_chart(_fig, use_container_width=True, key="detail_yield_hist")
            st.markdown(_farmer_insight_box("Ito ang dating ani. Pag pataas ang guhit, mas marami ang naaani kada ektarya. Target ng DA: 4.50 MT/ha."), unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with _yc2:
            st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">query_stats</i>Yield Forecast (Next 4 Quarters)</div><div class="component-desc">Forecast ng ani para sa susunod na 4 na quarter.</div>', unsafe_allow_html=True)
            _fig2 = _yield_forecast_chart(provincial_df, forecast_quarterly_yield, benchmark_option)
            st.plotly_chart(_fig2, use_container_width=True, key="detail_yield_fc")
        st.markdown("</div>", unsafe_allow_html=True)
        # yield insight summary - same visual as LGU production summary
        try:
            _fyd = [float(x) for x in forecast_quarterly_yield if pd.notna(x)]
        except Exception:
            _fyd = []
        if _fyd:
            try:
                _hd = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
                _last = _hd.max()
                _fqs = pd.period_range(start=pd.Period(_last, freq="Q") + 1, periods=len(_fyd), freq="Q")
                _flabs = [f"Q{q.quarter} {q.year}" for q in _fqs]
            except Exception:
                _flabs = [f"Q{i+1}" for i in range(len(_fyd))]
            _imax = int(np.argmax(_fyd)); _imin = int(np.argmin(_fyd))
            _ytrend = "TUMATAAS" if _fyd[-1] > _fyd[0] else ("BUMABABA" if _fyd[-1] < _fyd[0] else "STABLE")
            _vsda = "lagpas sa target" if avg_yield_forecast >= 4.5 else "kulang sa target"
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem 1.4rem; border-radius:16px; border-left:6px solid #2E7D32; box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.92rem; line-height:1.9;">
                <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.6rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i>Buod ng Hula sa Ani
                </div>
                <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">emoji_events</i>Pinakamataas: <b style="color:#2E7D32;">{_flabs[_imax]} — {_fyd[_imax]:.2f} MT/ha</b></div>
                <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_down</i>Pinakamababa: <b style="color:#C62828;">{_flabs[_imin]} — {_fyd[_imin]:.2f} MT/ha</b></div>
                <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i>Karaniwan: <b>{avg_yield_forecast:.2f} MT/ha</b> <span style="font-size:0.78rem; color:#6B7280;">(sa target ng DA na 4.50: {_vsda})</span></div>
                <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
                <div style="font-size:0.92rem; font-weight:600; color:#1B5E20;">
                    <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_up</i>Kabuuang trend:
                    <span style="color:#2E7D32; font-weight:700;">{_ytrend}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("Walang sapat na datos para sa buod ng ani.")
    elif section_choice == "Pambayang Forecast":
        st.markdown("""<div style="background:linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%); padding:22px 28px; border-radius:16px; color:white; margin-bottom:18px;"><div style="font-size:1.5rem; font-weight:800;"><i class="material-symbols-outlined" style="font-size:22px; vertical-align:middle; margin-right:8px; color:white;">location_on</i>Pambayang Forecast</div><div style="font-size:0.9rem; opacity:0.92; margin-top:6px;">Forecast kada bayan — pili ng binhi at klase, comparison ng presyo at historical production.</div></div>""", unsafe_allow_html=True)
        try:
            df_municipal_forecast = df_municipal_forecasts.copy()
            if df_municipal_forecast.empty:
                st.info("Wala pang hula para sa bawat bayan.")
            else:
                muni_label_col = _pick_column(df_municipal_forecast, ["Municipality"])
                muni_list = list(df_municipal_forecast[muni_label_col].dropna().unique()) if muni_label_col is not None else []
                # visible help for farmers
                st.markdown("""
                <div style="background:#E8F5E9; border:1px solid #A5D6A7; border-left:6px solid #1B5E20; border-radius:10px; padding:10px 14px; margin:6px 0 10px 0; display:flex; gap:10px; align-items:flex-start;">
                    <i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20; margin-top:1px;">location_on</i>
                    <div style="font-size:0.82rem; line-height:1.5; color:#1B5E20;">
                        Dito makikita ang presyo ng palay sa <b>bawat munisipyo batay sa binhi</b>.
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # grouped green card - wrap radios in bordered container
                st.markdown("""
                <style>
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.muni-group-anchor) { border:1.5px solid #C8E6C9 !important; border-radius:12px !important; background:#FFFFFF !important; padding:2px !important; }
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.muni-group-anchor) div[data-testid="stRadio"] label p { color:#1B5E20 !important; font-weight:500 !important; }
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.muni-group-anchor) div[data-testid="stRadio"] input[type="radio"] { accent-color:#1B5E20 !important; }
                </style>
                """, unsafe_allow_html=True)
                st.markdown('<div class="muni-group-anchor" style="display:none;"></div>', unsafe_allow_html=True)
                with st.container(border=True):
                    _muni_for_chart = [selected_muni] if selected_muni != "Lahat ng Bayan" else []
                    c1, c2, c3 = st.columns(3, gap="small")
                    with c1:
                        ov_rice_type = st.radio("Binhi", options=["Inbred", "Hybrid"], horizontal=True, key="ov_muni_rt_detail")
                    with c2:
                        ov_grade_raw = st.radio("Klase", options=["Regular", "Premium"], horizontal=True, key="ov_muni_cls_detail")
                        ov_classification = "Ordinary" if ov_grade_raw == "Regular" else "Premium"
                    with c3:
                        ov_cycle = st.radio("Panahon", options=["Dry Season", "Wet Season"], horizontal=True, key="ov_muni_cycle_detail")
                # dynamic Dry vs Wet side-by-side cards - always show, works for All or single
                try:
                    _prefix = f"{ov_rice_type.lower()}{ov_classification.lower()}"
                    _dry_key = f"{_prefix}_dry"
                    _wet_key = f"{_prefix}_wet"
                    _type_col = "rice type & season"
                    _df_lc = df_municipal_forecast.copy()
                    _df_lc.columns = [str(c).lower() for c in _df_lc.columns]
                    if selected_muni != "Lahat ng Bayan":
                        _dry_sub = _df_lc[(_df_lc["municipality"].str.lower() == selected_muni.lower()) & (_df_lc[_type_col].str.lower() == _dry_key)]
                        _wet_sub = _df_lc[(_df_lc["municipality"].str.lower() == selected_muni.lower()) & (_df_lc[_type_col].str.lower() == _wet_key)]
                        _label_muni = selected_muni
                    else:
                        _dry_sub = _df_lc[_df_lc[_type_col].str.lower() == _dry_key]
                        _wet_sub = _df_lc[_df_lc[_type_col].str.lower() == _wet_key]
                        _label_muni = "Buong Bataan (lahat ng bayan)"
                    if not _dry_sub.empty and not _wet_sub.empty:
                        _dry_vals = pd.to_numeric(_dry_sub["month 1"], errors="coerce").dropna()
                        _wet_vals = pd.to_numeric(_wet_sub["month 1"], errors="coerce").dropna()
                        _dry_price = float(_dry_vals.mean()) if not _dry_vals.empty else None
                        _wet_price = float(_wet_vals.mean()) if not _wet_vals.empty else None
                        if _dry_price is not None and _wet_price is not None:
                            _diff = _dry_price - _wet_price
                            _diff_col = "#1B5E20" if _diff > 0 else "#BF360C" if _diff < 0 else "#6B7280"
                            _diff_txt = f"+\u20B1{abs(_diff):.2f} kapag pinatuyo (Dry kumpara sa Wet)" if _diff > 0 else f"-\u20B1{abs(_diff):.2f} mas mataas ang Wet" if _diff < 0 else "Pareho ang presyo"
                            _dry_lab = _dry_sub["forecast_month_1_label"].iloc[0] if "forecast_month_1_label" in _dry_sub.columns and not _dry_sub["forecast_month_1_label"].dropna().empty else "Month 1"
                            st.markdown(f"""
                            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin:10px 0 12px 0;">
                                <div style="background:#E8F5E9; border:1.5px solid #1B5E20; border-radius:10px; padding:12px; text-align:center;">
                                    <div style="font-size:0.72rem; font-weight:600; color:#6B7280; text-transform:uppercase;">Dry</div>
                                    <div style="font-size:1.25rem; font-weight:800; color:#1B5E20;"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:4px; color:#1B5E20;">wb_sunny</i>\u20B1{_dry_price:.2f}/kg</div>
                                    <div style="font-size:0.70rem; color:#6B7280;">{_dry_lab} • {ov_rice_type} {ov_classification}</div>
                                </div>
                                <div style="background:#E3F2FD; border:1.5px solid #90CAF9; border-radius:10px; padding:12px; text-align:center;">
                                    <div style="font-size:0.72rem; font-weight:600; color:#6B7280; text-transform:uppercase;">Wet</div>
                                    <div style="font-size:1.25rem; font-weight:800; color:#1565C0;"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:4px; color:#1565C0;">water_drop</i>\u20B1{_wet_price:.2f}/kg</div>
                                    <div style="font-size:0.70rem; color:#6B7280;">Wet • {ov_rice_type} {ov_classification}</div>
                                </div>
                            </div>
                            <div style="background:#FFF8E1; border:1px solid #FFE082; border-radius:8px; padding:8px 12px; text-align:center; font-size:0.80rem; color:{_diff_col}; font-weight:700; margin-bottom:10px;">
                                <i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:4px; color:{_diff_col};">compare_arrows</i>{_diff_txt} • {_label_muni}
                            </div>
                            """, unsafe_allow_html=True)
                except Exception:
                    pass
                _sel_cycle = "Dry Season Crop Cycle" if "Dry" in ov_cycle else "Wet Season Crop Cycle"
                _render_municipal_crop_cycle_chart(df_municipal_forecast, rice_type=ov_rice_type, classification=ov_classification, selected_municipalities=_muni_for_chart, selected_cycle=_sel_cycle)
                st.markdown(_farmer_insight_box("Hula ito ng presyo sa bawat bayan sa susunod na 3 buwan. Piliin ang binhi at bayan para makita kung saan pinakamataas — doon ka mas kikita."), unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Unable to render municipal forecast: {str(e)}")
        if not top5_municipalities.empty:
            st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">emoji_events</i>Top 5 Bayan — Historical Production</div><div class="component-desc">Top 5 bayan na may pinakamataas na produksyon (historical).</div>', unsafe_allow_html=True)
            try:
                fig_muni = px.bar(top5_municipalities.sort_values("palay_production"), x="palay_production", y="municipality", orientation="h", color="palay_production", color_continuous_scale=["#A5D6A7", "#1B5E20"], text="palay_production")
                fig_muni.update_traces(texttemplate="%{text:,.0f} MT", textposition="outside", marker=dict(line=dict(width=2, color='white'), cornerradius=4), hovertemplate="<b>%{y}</b><br>Produksyon: %{x:,.0f} MT<extra></extra>")
                fig_muni.update_layout(height=360, margin=dict(l=10, r=80, t=10, b=10), xaxis_title="Produksyon (MT)", yaxis_title="Bayan", showlegend=False, plot_bgcolor="white", paper_bgcolor="white", coloraxis_showscale=False, yaxis={"categoryorder": "total ascending"})
                fig_muni.update_xaxes(gridcolor="#F3F4F6", showgrid=True)
                st.plotly_chart(fig_muni, use_container_width=True, key="muni_detail_top5")
                _top = top5_municipalities.sort_values("palay_production", ascending=False).iloc[0]
                st.markdown(_farmer_insight_box(f"Nangunguna si {str(_top['municipality'])} na may {float(_top['palay_production']):,.0f} MT."), unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"Chart error: {str(e)}")
            st.markdown("</div>", unsafe_allow_html=True)
        # pies hidden for farmer - kept for LGU only
    elif section_choice == "Gabay at Payo":
        st.markdown("""<div style="background:linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%); padding:22px 28px; border-radius:16px; color:white; margin-bottom:18px;"><div style="font-size:1.5rem; font-weight:800;"><i class="material-symbols-outlined" style="font-size:22px; vertical-align:middle; margin-right:8px; color:white;">lightbulb</i>Gabay at Payo</div><div style="font-size:0.9rem; opacity:0.92; margin-top:6px;">Mga payong galing sa hula</div></div>""", unsafe_allow_html=True)
        st.markdown('<div class="component-card"><div class="component-header"><i class="material-symbols-outlined" style="font-size:18px; vertical-align:middle; margin-right:6px; color:#1B5E20;">lightbulb</i>Payo Batay sa Forecast</div><div class="component-desc">Rekomendasyon batay sa forecast ng presyo at ani.</div>', unsafe_allow_html=True)
        if not muni_filtered.empty:
            if percent_change_fancy > 5: _p_title, _p_body, _p_icon, _p_accent = "Itago muna ang Fancy", f"Fancy tataas sa <span class='highlight-text'>\u20B1{next_fancy_pred:.2f}/kg</span> sa {next_month_name}. Mas kikita kung sa {_fmax_month} ibebenta. Regular nasa \u20B1{next_regular_pred:.2f}/kg.", "trending_up", "card-marketing"
            elif percent_change_fancy < -5: _p_title, _p_body, _p_icon, _p_accent = "Ibenta na ang Fancy", f"Bababa ang Fancy sa <span class='highlight-text'>\u20B1{next_fancy_pred:.2f}/kg</span>. Mas maganda ibenta ngayon bago bumaba pa sa {_fmin_month}.", "trending_down", "card-notice"
            else: _p_title, _p_body, _p_icon, _p_accent = "Magmasid muna", f"Hindi gumagalaw ang presyo (Fancy \u20B1{next_fancy_pred:.2f}, Regular \u20B1{next_regular_pred:.2f}). Magmasid muna bago magbenta nang maramihan.", "monitoring", "card-status"
            if avg_yield_forecast >= 4.5 and (_ymax - _ymin) < 0.4: _y_title, _y_body, _y_icon, _y_accent = "Maganda ang ani — ituloy ang plano", f"Avg <span class='highlight-text'>{avg_yield_forecast:.2f} MT/ha</span> lagpas sa target ng DA na 4.50. Sapat ang supply, ituloy ang pagtatanim.", "eco", "card-marketing"
            elif avg_yield_forecast < 4.0: _y_title, _y_body, _y_icon, _y_accent = "Magtipid at ayusin ang patubig", f"Avg <span class='highlight-text'>{avg_yield_forecast:.2f} MT/ha</span> kulang sa target. Magtipid sa abono, ayusin ang patubig.", "water_drop", "card-notice"
            else: _y_title, _y_body, _y_icon, _y_accent = "Magtabi ng reserba", f"Pinakamataas <span class='highlight-text'>{_ymax:.2f} MT/ha</span>, pinakamababa <span class='highlight-text'>{_ymin:.2f} MT/ha</span> — magtabi ng reserba para sa mga buwang mahina ang ani.", "inventory_2", "card-optimization"
            st.markdown(f"""<div class="advisory-container"><div class="advisory-card {_p_accent}"><div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20;">{_p_icon}</i></div><div class="card-body"><span class="card-label label-marketing">{_p_title}:</span> {_p_body}</div></div><div class="advisory-card {_y_accent}"><div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20;">{_y_icon}</i></div><div class="card-body"><span class="card-label label-optimization">{_y_title}:</span> {_y_body}</div></div><div class="advisory-card card-status"><div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20;">location_on</i></div><div class="card-body"><span class="card-label label-status">Para sa {muni_badge}:</span> Kabuuang ani <span class="highlight-text">{prod_val:,.0f} MT</span> sa {selected_start_year}–{selected_end_year}. Kung mataas ang presyo sa {_fmax_month}, mas mainam magbenta noon.</div></div></div>""", unsafe_allow_html=True)
        else:
            st.warning("Walang sapat na datos para makapagbigay ng payo sa pinili mo.")
        st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("Gabay sa Pagbasa ng Forecast", expanded=False):
            st.markdown("- **Presyo ng Palay:** Pag pataas ang linya, tumataas ang presyo.\n- **Inaasahang Ani:** MT/ha — toneladang aanihin kada ektarya.\n- **Batayan:** Putol-putol na linya — NFA floor price (₱19.00) at 3-year average.\n- **Pambayang Forecast:** Piliin ang bayan para sa comparison ng presyo.")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("""<div style="text-align:center; padding:10px 0 5px 0; font-size:0.75rem; color:#9CA3AF; border-top:1px solid #E5E7EB; margin-top:10px;"><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#9CA3AF;">agriculture</i>Bataan Rice Monitoring System &bull; v2.0</div>""", unsafe_allow_html=True)
