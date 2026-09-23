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

# ---- farmer helpers (English) ----

def _build_price_context(fc_fancy, fc_regular, forecast_months):
    def _interp(vals):
        if not vals or len(vals)==0:
            return {"vals":[], "labels":[], "lowest":None, "highest":None, "trend_sentence":"Price forecast is being prepared. Please check again soon.", "recover_sentence":"No price trend available yet."}
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
                    trend = f"Prices likely to rise toward {mx_lab}"
                    recover = f"Prices are expected to recover after {mn_lab}."
                else:
                    trend = f"Prices expected to increase toward {mx_lab}"
                    recover = f"Highest price expected in {mx_lab}."
            elif last < first - 0.3:
                trend = f"Prices expected to ease toward {mx_lab}"
                recover = f"Prices may ease after {mn_lab}."
            else:
                trend = "Prices expected to remain steady"
                recover = "Prices are expected to stay steady in the coming months."
        except Exception:
            trend = "Prices expected to remain steady"
            recover = "Prices are expected to stay steady."
        return {"vals": vals, "labels": labels, "lowest": (mn_lab, mn), "highest": (mx_lab, mx), "trend_sentence": trend, "recover_sentence": recover}
    return {"fancy": _interp(list(fc_fancy)), "regular": _interp(list(fc_regular))}

def _harvest_interpretation(yield_vals, quarter_labels):
    if not yield_vals:
        return {"avg": None, "range": None, "delta_prev": None, "sentence": "Harvest forecast is being prepared. Please check again soon."}
    s = pd.Series(yield_vals, dtype=float).dropna()
    if s.empty:
        return {"avg": None, "range": None, "delta_prev": None, "sentence": "Harvest forecast is being prepared. Please check again soon."}
    avg = float(s.mean())
    lo = float(s.min()); hi = float(s.max())
    delta = float(s.iloc[-1] - s.iloc[0]) if len(s)>1 else 0.0
    if abs(delta) < 0.05:
        sent = f"Harvest (ani) expected to stay around {avg:.2f} tons per hectare."
    elif delta > 0:
        sent = f"Harvest (ani) may improve by {quarter_labels[-1] if quarter_labels else 'next quarter'}."
    else:
        sent = f"Harvest (ani) may ease slightly after {quarter_labels[0] if quarter_labels else 'next quarter'}."
    return {"avg":avg, "range":(lo,hi), "delta_prev": delta, "sentence": sent, "lo":lo, "hi":hi}

def _municipal_yield_estimate(selected_muni, provincial_yield_vals, provincial_labels, municipal_prod_df):
    """Historical municipal yield (not a forecast) — for reference only."""
    prov_forecast = float(pd.Series(provincial_yield_vals).dropna().iloc[0]) if provincial_yield_vals and len(pd.Series(provincial_yield_vals).dropna())>0 else None
    try:
        if municipal_prod_df is None or municipal_prod_df.empty or selected_muni in (None, "All Municipalities", ""):
            return None, None, None
        mdf = municipal_prod_df.copy()
        mdf.columns = [str(c).strip() for c in mdf.columns]
        mc = next((c for c in mdf.columns if c.lower()=="municipality"), None)
        if mc is None:
            return None, None, None
        mdf[mc] = mdf[mc].astype(str)
        sub = mdf[mdf[mc].str.lower()==str(selected_muni).lower()]
        if sub.empty:
            return None, None, None
        ap_col = next((c for c in mdf.columns if c.lower() in ("ave_production","aveproduction","avg_yield")), None)
        if ap_col is None:
            return None, None, None
        sub_vals = pd.to_numeric(sub[ap_col], errors="coerce").dropna()
        sub_vals = sub_vals[(sub_vals >= 1.5) & (sub_vals <= 8.0)]
        if sub_vals.empty:
            return None, None, None
        _all_vals = pd.to_numeric(mdf[ap_col], errors="coerce").dropna()
        _all_vals = _all_vals[(_all_vals >= 1.5) & (_all_vals <= 8.0)]
        prov_hist_avg = _all_vals.mean() if not _all_vals.empty else None
        if prov_hist_avg is None or pd.isna(prov_hist_avg):
            return None, None, None
        try:
            ycol = next((c for c in mdf.columns if c.lower()=="year"), None)
            if ycol is not None:
                sub_sorted = sub.sort_values(ycol)
                sub_re_vals = pd.to_numeric(sub_sorted[ap_col], errors="coerce").dropna()
                sub_re_vals = sub_re_vals[(sub_re_vals >= 1.5) & (sub_re_vals <= 8.0)]
                muni_hist_avg = float(sub_re_vals.tail(5).mean()) if not sub_re_vals.empty else float(sub_vals.tail(3).mean())
            else:
                muni_hist_avg = float(sub_vals.tail(5).mean())
        except Exception:
            muni_hist_avg = float(sub_vals.tail(3).mean())
        if pd.isna(prov_hist_avg) or pd.isna(muni_hist_avg) or prov_hist_avg==0:
            return None, None, None
        diff = float(muni_hist_avg - prov_hist_avg)
        if diff > 0.05:
            comp = f"Above Bataan average ({prov_hist_avg:.2f} tons/ha) by {diff:.2f}"
            status = "above"
        elif diff < -0.05:
            comp = f"Below Bataan average ({prov_hist_avg:.2f} tons/ha) by {abs(diff):.2f}"
            status = "below"
        else:
            comp = f"Around Bataan average ({prov_hist_avg:.2f} tons/ha)"
            status = "around"
        return float(muni_hist_avg), float(prov_hist_avg), (comp, status, diff, prov_forecast)
    except Exception:
        return None, None, None

def _farmer_price_chart(forecast_months, vals, color="#1B5E20"):
    fig = go.Figure()
    if not vals or len(vals)==0:
        return fig
    labels = [m.strftime("%b %Y") if hasattr(m,'strftime') else str(m) for m in forecast_months[:len(vals)]]
    fig.add_trace(go.Scatter(x=labels, y=vals, mode="lines+markers+text", name="Forecast", line=dict(color=color, width=2.6), marker=dict(size=7, color=color), text=[f"₱{v:.2f}" if pd.notna(v) else "" for v in vals], textposition="top center", textfont=dict(size=10, color="#1B4332")))
    try:
        s = pd.Series(vals, dtype=float)
        mn_idx = int(s.idxmin()); mx_idx = int(s.idxmax())
        mn_val = float(s.min()); mx_val = float(s.max())
        mn_lab = labels[mn_idx]; mx_lab = labels[mx_idx]
        fig.add_annotation(x=mn_lab, y=mn_val, text=f"Lowest<br>{mn_lab}<br>₱{mn_val:.2f}", showarrow=False, yshift=-28, bgcolor="#F1F8E9", bordercolor="#C5E1A5", borderwidth=1, font=dict(size=9, color="#33691E"), opacity=0.95)
        fig.add_annotation(x=mx_lab, y=mx_val, text=f"Highest<br>{mx_lab}<br>₱{mx_val:.2f}", showarrow=False, yshift=22, bgcolor="#E8F5E9", bordercolor="#A5D6A7", borderwidth=1, font=dict(size=9, color="#1B5E20"), opacity=0.95)
        rng = max(vals)-min(vals)
        pad = max(0.6, rng*0.35)
        fig.update_yaxes(range=[min(vals)-pad, max(vals)+pad])
    except Exception:
        pass
    fig.update_layout(height=300, margin=dict(l=10,r=10,t=26,b=10), plot_bgcolor="white", paper_bgcolor="white", xaxis=dict(gridcolor="#F3F4F6", showgrid=True, tickfont=dict(size=11, color="#6B7280")), yaxis=dict(gridcolor="#F3F4F6", showgrid=True, tickfont=dict(size=11, color="#6B7280"), title=dict(text="₱/kg", font=dict(size=11, color="#6B7280"))), showlegend=False, hovermode="x unified")
    return fig

def _render_municipal_crop_cycle_chart(df, rice_type, classification, selected_municipalities, selected_cycle=None):
    if df is None or df.empty:
        st.info("No price forecast is available yet for each town. Please check again later.")
        return
    df = df.copy(); df.columns = [str(col).lower() for col in df.columns]
    if selected_municipalities:
        selected_munis_lc = [str(m).lower() for m in selected_municipalities]
        df = df[df["municipality"].str.lower().isin(selected_munis_lc)]
    if selected_cycle is None:
        selected_cycle = st.selectbox("Choose palay moisture:", ["Dry Palay", "Wet Palay"], key=f"crop_cycle_{rice_type}_{classification}")
        st.write("---")
    base_key = f"{rice_type.lower()}{classification.lower()}".replace(" ", "")
    suffix = "_dry" if "Dry" in selected_cycle else "_wet"
    target_key = f"{base_key}{suffix}"
    type_col = "rice type & season"
    sub = df[df[type_col].str.lower() == target_key] if type_col in df.columns else pd.DataFrame()
    if sub.empty:
        st.warning(f"No data for this combination — please try another option.")
        return
    label_map = {}
    for key, n in (("forecast_month_1_label", 1), ("forecast_month_2_label", 2), ("forecast_month_3_label", 3)):
        if key in sub.columns and sub[key].notna().any():
            label_map[f"month {n}"] = str(sub[key].iloc[0])
        else:
            label_map[f"month {n}"] = f"Month {n}"
    forecast_month_labels = [label_map[f"month {n}"] for n in range(1, 4)]
    # --- Dynamic title: akma sa pinili (Binhi + Palay Type + Moisture + forecast months) ---
    try:
        _parsed = [pd.to_datetime(lbl, errors="coerce") for lbl in forecast_month_labels]
        if all(pd.notna(p) for p in _parsed):
            if _parsed[0].year == _parsed[-1].year:
                period_str = f"{_parsed[0].strftime('%b')} – {_parsed[-1].strftime('%b %Y')}"
            else:
                period_str = f"{_parsed[0].strftime('%b %Y')} – {_parsed[-1].strftime('%b %Y')}"
        else:
            period_str = f"{forecast_month_labels[0]} – {forecast_month_labels[-1]}"
    except Exception:
        period_str = f"{forecast_month_labels[0]} – {forecast_month_labels[-1]}"
    grade_display = "Premium" if str(classification).strip().lower() == "premium" else "Regular"
    is_dry = "Dry" in str(selected_cycle)
    moisture_full = "Dry Palay (Tuyo)" if is_dry else "Wet Palay (Basa/Sariwa)"
    moisture_icon = "wb_sunny" if is_dry else "water_drop"
    moisture_color = "#B45309" if is_dry else "#2563EB"
    n_towns = len(selected_municipalities) if selected_municipalities else 12
    st.markdown(
        f"<div style='font-weight:800; color:#1B4332; margin:0.6rem 0 2px 0; display:flex; align-items:center; gap:6px; flex-wrap:wrap; font-size:13px;'>"
        f"<i class='material-symbols-outlined' style='font-size:16px; color:{moisture_color};'> {moisture_icon}</i> "
        f"{rice_type} {grade_display} — {moisture_full}"
        f"<span style='font-weight:600; color:#6B7280; font-size:12px;'>| {period_str}</span>"
        f"</div>"
        f"<div style='font-size:11px; color:#6B7280; margin-bottom:6px;'>{n_towns} towns • Forecast ng presyo (₱/kg) — grouped per month</div>",
        unsafe_allow_html=True,
    )
    plot_df = sub.melt(id_vars=["municipality"], value_vars=["month 1", "month 2", "month 3"], var_name="month_key", value_name="price").assign(forecast_month=lambda d: d["month_key"].map(label_map)).groupby(["forecast_month", "municipality"], as_index=False)["price"].mean().dropna(subset=["price"])
    if plot_df.empty:
        st.info("No data for your selection. Please try another combination.")
        return
    plot_df["price"] = pd.to_numeric(plot_df["price"], errors="coerce")
    plot_df = plot_df.dropna(subset=["price"])
    if plot_df.empty:
        st.info("No price data for your selection.")
        return
    plot_df["municipality"] = plot_df["municipality"].astype(str).str.title()
    # Title is now rendered as markdown above (dynamic), so keep Plotly title empty to avoid double title
    fig = px.bar(plot_df, x="forecast_month", y="price", color="municipality", barmode="group", category_orders={"forecast_month": forecast_month_labels}, color_discrete_sequence=px.colors.qualitative.Set3, labels={"forecast_month": "Forecast Month", "price": "Price (₱/kg)", "municipality": "Town"}, title="")
    fig.update_layout(height=380, margin=dict(t=10, b=120, l=45, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(family="Plus Jakarta Sans, sans-serif", size=11), legend=dict(orientation="h", yanchor="top", y=-0.28, xanchor="center", x=0.5, font=dict(size=9.5), bgcolor="rgba(255,255,255,0.95)", bordercolor="#E5E7EB", borderwidth=1), yaxis=dict(gridcolor="#F3F4F6", showgrid=True), xaxis=dict(gridcolor="#F3F4F6", showgrid=False), bargap=0.22, bargroupgap=0.10)
    fig.update_traces(marker=dict(cornerradius=6, line=dict(width=0)), hovertemplate="Town: %{fullData.name}<br>%{x}<br>₱%{y:.2f}/kg<extra></extra>", cliponaxis=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})

def overview_page():
    dr = reload_dashboard_data()
    if not dr.has_provincial_data:
        _is_maint = False
        try:
            if st.session_state.get("maintenance_mode") or st.session_state.get("demo_empty_state"):
                _is_maint = True
            if st.query_params.get("maintenance") == "1" or st.query_params.get("demo_empty") == "1":
                _is_maint = True
            from pathlib import Path as _P
            import json as _js
            _flag = _P(__file__).resolve().parents[1] / "data" / ".maintenance.json"
            if not _is_maint and _flag.exists():
                try:
                    d = _js.loads(_flag.read_text(encoding="utf-8"))
                    if d.get("enabled"):
                        _is_maint = True
                except Exception:
                    _is_maint = True
        except Exception:
            pass
        if _is_maint:
            st.markdown("""
                <style>
                .farmer-maint-card { background:#FFFBEB; border:1px solid #FDE68A; border-radius:12px; padding:40px 32px; min-height:420px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.06); margin:24px auto; max-width:640px; }
                .farmer-maint-badge { display:inline-flex; align-items:center; gap:6px; background:#FEF3C7; color:#92400E; border:1px solid #FDE68A; padding:6px 14px; border-radius:999px; font-size:0.82rem; font-weight:600; margin-top:16px; }
                </style>
                <div class="farmer-maint-card">
                    <div style="width:64px; height:64px; background:#FEF3C7; border:1px solid #FDE68A; border-radius:50%; display:flex; align-items:center; justify-content:center; margin-bottom:16px;">
                        <i class="material-symbols-outlined" style="font-size:32px; color:#D97706;">construction</i>
                    </div>
                    <h1 style="margin:0; color:#92400E; font-size:1.9rem; font-weight:800; line-height:1.25;">System Under Maintenance</h1>
                    <p style="margin:18px 0 0 0; color:#78350F; font-size:0.98rem; line-height:1.7; max-width:560px;">The <strong>PalaySense Farmer Dashboard</strong> is under <strong>scheduled maintenance</strong> to provide you with better service.</p>
                    <p style="margin:10px 0 0 0; color:#78350F; font-size:0.95rem; line-height:1.6; max-width:560px;">Please try again later. We appreciate your patience and understanding.</p>
                    <div class="farmer-maint-badge"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:4px; color:#D97706;">info</i>Official Advisory — Office of the Provincial Agriculturist, Bataan</div>
                </div>
            """, unsafe_allow_html=True)
            _, btn_col, _ = st.columns([1, 1.2, 1])
            with btn_col:
                if st.button("Back to Home", icon=":material/home:", key="farmer_maint_to_home", type="primary", use_container_width=True):
                    st.query_params["page"] = "home"; st.rerun()
            st.stop()
        else:
            st.markdown("""
                <style>
                .farmer-empty-card { background:#FFFFFF; border:1px solid #E0E0E0; border-radius:12px; padding:40px 32px; min-height:420px; display:flex; flex-direction:column; justify-content:center; align-items:center; text-align:center; box-shadow:0 4px 12px rgba(0,0,0,0.06); margin:24px auto; max-width:640px; }
                .farmer-empty-badge { display:inline-flex; align-items:center; gap:6px; background:#E8F5E9; color:#2E7D32; border:1px solid #C8E6C9; padding:6px 14px; border-radius:999px; font-size:0.82rem; font-weight:600; margin-top:16px; }
                </style>
                <div class="farmer-empty-card">
                    <h1 style="margin:0; color:#1B5E20; font-size:1.9rem; font-weight:800;">Welcome to PalaySense, Bataan!</h1>
                    <p style="margin:16px 0 0 0; color:#4B5563; font-size:1rem; line-height:1.7; max-width:520px;">No records are available yet. We are waiting for updated information from your LGU. Please check again later.</p>
                    <div class="farmer-empty-badge"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:4px; color:#2E7D32;">info</i>System ready — waiting for new data.</div>
                </div>
            """, unsafe_allow_html=True)
            _, btn_col, _ = st.columns([1, 1.2, 1])
            with btn_col:
                if st.button("Back to Home", icon=":material/home:", key="farmer_empty_to_home", type="primary", use_container_width=True):
                    st.query_params["page"] = "home"; st.rerun()
            st.stop()
    if dr.has_provincial_data and not dr.has_forecasts:
        st.info("New price and harvest (<i>ani</i>) forecasts are being prepared — you can still view past records.")

    provincial_df = dr.provincial_df.copy()
    _prod_muni = getattr(dr, "municipal_production_df", None)
    municipality_df = _prod_muni.copy() if _prod_muni is not None and not getattr(_prod_muni, "empty", True) else dr.municipality_df.copy()
    df_municipal_forecasts = dr.df_municipal_forecasts.copy()
    forecast_3months_fancy = list(dr.forecast_3months_fancy)
    forecast_variety_3months = list(dr.forecast_variety_3months)
    forecast_quarterly_yield = list(dr.forecast_quarterly_yield)

    hist_last = pd.to_datetime(provincial_df["date"], errors="coerce").max() if "date" in provincial_df.columns and not provincial_df.empty else pd.Timestamp("2026-07-01")
    if pd.isna(hist_last):
        hist_last = pd.Timestamp("2026-07-01")
    fc_len = max(len(forecast_3months_fancy), len(forecast_variety_3months), 6)
    try:
        pf = load_provincial_forecasts()
        fancy_labels = pf[pf["forecast_type"]=="fancy"]["period_label"].tolist() if not pf.empty else []
        month_map = {"january":1,"february":2,"march":3,"april":4,"may":5,"june":6,"july":7,"august":8,"september":9,"october":10,"november":11,"december":12}
        forecast_months = []
        for lbl in fancy_labels[:fc_len]:
            try:
                parts = str(lbl).strip().lower().split()
                m = month_map.get(parts[0], 1)
                y = int(parts[1])
                forecast_months.append(pd.Timestamp(year=y, month=m, day=1))
            except Exception:
                continue
        if len(forecast_months) < fc_len:
            start = (hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp()
            forecast_months = list(pd.date_range(start=start, periods=fc_len, freq="MS"))
    except Exception:
        start = (hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp()
        forecast_months = list(pd.date_range(start=start, periods=fc_len, freq="MS"))
    if not forecast_months:
        forecast_months = list(pd.date_range(start="2026-08-01", periods=6, freq="MS"))
    try:
        pf_y = load_provincial_forecasts()
        y_labels = pf_y[pf_y["forecast_type"]=="yield"]["period_label"].tolist() if not pf_y.empty else []
        if not y_labels:
            y_labels = [f"Q4 2026", f"Q1 2027", f"Q2 2027", f"Q3 2027"]
    except Exception:
        y_labels = [f"Q4 2026", f"Q1 2027", f"Q2 2027", f"Q3 2027"]

    fc_fancy = list(forecast_3months_fancy)[:6]
    fc_regular = list(forecast_variety_3months)[:6]
    while len(fc_fancy) < len(forecast_months):
        fc_fancy.append(np.nan)
    while len(fc_regular) < len(forecast_months):
        fc_regular.append(np.nan)
    price_ctx = _build_price_context(fc_fancy, fc_regular, forecast_months)
    yield_ctx = _harvest_interpretation(forecast_quarterly_yield, y_labels)

    next_yield_val = float(pd.Series(forecast_quarterly_yield).dropna().iloc[0]) if forecast_quarterly_yield and len(pd.Series(forecast_quarterly_yield).dropna())>0 else None
    yield_lo = yield_ctx.get("lo")
    yield_hi = yield_ctx.get("hi")
    try:
        if "quarterly_yield_mt_per_ha" in provincial_df.columns:
            prev_yield = float(pd.to_numeric(provincial_df["quarterly_yield_mt_per_ha"], errors="coerce").dropna().tail(4).mean())
        else:
            prev_yield = None
    except Exception:
        prev_yield = None
    yield_delta_prev = (next_yield_val - prev_yield) if (next_yield_val is not None and prev_yield is not None and not pd.isna(prev_yield)) else None

    muni_label_col = _pick_column(municipality_df, ["municipality", "Municipality", "Mun"])
    mprod_label_col = None
    if _prod_muni is not None and not _prod_muni.empty:
        mprod_label_col = _pick_column(_prod_muni, ["municipality", "Municipality"])
        all_munis = sorted(_prod_muni[mprod_label_col].dropna().astype(str).str.title().unique().tolist()) if mprod_label_col else []
    else:
        all_munis = sorted(municipality_df[muni_label_col].dropna().astype(str).str.title().unique().tolist()) if muni_label_col else []
    if not all_munis and not df_municipal_forecasts.empty:
        mc = _pick_column(df_municipal_forecasts, ["Municipality", "municipality"])
        if mc:
            all_munis = sorted(df_municipal_forecasts[mc].dropna().astype(str).str.title().unique().tolist())
    if not all_munis:
        all_munis = ["Balanga City","Abucay","Bagac","Dinalupihan","Hermosa","Limay","Mariveles","Morong","Orani","Orion","Pilar","Samal"]

    QUICK_VIEW_GROUPS = [("OVERVIEW", [("Overview", "dashboard")]), ("DETAILS", [("Price Forecast", "payments"), ("Harvest Forecast", "eco"), ("Municipal Forecast", "location_on")]), ("SUPPORT", [("Guide and Advice", "lightbulb")])]
    st.session_state.setdefault("overview_section", "Overview")
    _valid = {"Overview","Price Forecast","Harvest Forecast","Municipal Forecast","Guide and Advice"}
    # normalize Harvest Forecast (Ani) -> Harvest Forecast for English
    if st.session_state.get("overview_section") == "Harvest Forecast (Ani)":
        st.session_state["overview_section"] = "Harvest Forecast"
    if st.session_state.get("overview_section") not in _valid:
        st.session_state["overview_section"] = "Overview"
    section_choice = st.session_state.get("overview_section", "Overview")
    # Farmer-friendly display names for sidebar (simple English, official tone)
    _farmer_display = {"Municipal Forecast": "Prices per Town", "Guide and Advice": "Guide (Gabay)", "Harvest Forecast": "Harvest Forecast (Ani)", "Price Forecast": "Price Forecast"}

    st.session_state.setdefault("farmer_price_type", "Regular")
    st.session_state.setdefault("farmer_selected_muni", all_munis[0] if all_munis else "Mariveles")
    if st.session_state["farmer_selected_muni"] not in all_munis and all_munis:
        st.session_state["farmer_selected_muni"] = all_munis[0]

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=DM+Serif+Display&display=swap');
    section[data-testid="stSidebar"] {
        background:#123524 !important;
        border-right:1px solid rgba(255,255,255,0.08) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] { padding-top:0.4rem !important; }
    section[data-testid="stSidebar"] .stButton > button {
        background:transparent !important; border:none !important; color:rgba(255,255,255,0.85) !important;
        font-family:'Plus Jakarta Sans', sans-serif !important; font-weight:500 !important; font-size:13px !important;
        text-align:left !important; justify-content:flex-start !important; align-items:center !important; border-radius:10px !important; padding:9px 14px !important; min-height:38px !important; height:auto !important;
        display:flex !important; gap:10px !important;
    }
    section[data-testid="stSidebar"] .stButton > button p { color:rgba(255,255,255,0.85) !important; text-align:left !important; margin:0 !important; }
    section[data-testid="stSidebar"] .stButton > button div[data-testid="stMarkdownContainer"] { text-align:left !important; justify-content:flex-start !important; display:flex !important; align-items:center !important; width:100% !important; }
    section[data-testid="stSidebar"] .stButton > button div[data-testid="stMarkdownContainer"] p { text-align:left !important; justify-content:flex-start !important; }
    section[data-testid="stSidebar"] .stButton > button:hover { background:rgba(255,255,255,0.08) !important; color:#FFFFFF !important; }
    section[data-testid="stSidebar"] .stButton > button:hover p { color:#FFFFFF !important; }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] { background:#1E5C3A !important; color:#FFFFFF !important; font-weight:700 !important; border-left:3px solid #A3E4A0 !important; }
    section[data-testid="stSidebar"] .stButton > button[kind="primary"] p { color:#FFFFFF !important; font-weight:700 !important; }
    .farmer-sidebar-label { font-family:'Plus Jakarta Sans', sans-serif; font-size:11px; font-weight:700; color:#7FB094; letter-spacing:0.8px; margin:16px 0 6px 4px; text-transform:uppercase; opacity:0.95; }
    .farmer-sidebar-card { background:#FFFFFF; border:1px solid #E8EFDE; border-radius:14px; padding:14px; margin-top:16px; box-shadow:0 4px 12px rgba(0,0,0,0.18); }
    .block-container { padding-top:0 !important; margin-top:0 !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.6rem !important; }
    div[data-testid="stVerticalBlock"] > div:has(.farmer-hero) { padding-top: 0 !important; margin-top: 0 !important; }
    div[data-testid="stVerticalBlock"]:has(.farmer-card-anchor) {
        background: white !important; border:1px solid #E8EFDE !important; border-radius:16px !important; box-shadow: 0 2px 10px rgba(0,0,0,0.03) !important; padding:16px 16px 14px 16px !important; margin-bottom: 0 !important;
    }
    div[data-testid="stVerticalBlock"]:has(.farmer-card-anchor.harvest) { background: #FFFEF8 !important; border-color: #F2E8C8 !important; }
    div[data-testid="stVerticalBlock"]:has(.farmer-muni-card-anchor) {
        background: white !important; border:1px solid #E8EFDE !important; border-radius:16px !important; box-shadow: 0 2px 10px rgba(0,0,0,0.03) !important; padding:16px !important; margin-bottom: 0 !important;
    }
    .farmer-card, .farmer-what-card, .farmer-muni-card { background: white !important; border:1px solid #E8EFDE !important; border-radius:16px !important; box-shadow: 0 2px 10px rgba(0,0,0,0.03) !important; padding:16px !important; margin-bottom: 0 !important; }
    .farmer-hero { position:relative; background: linear-gradient(90deg, rgba(255,255,255,0.96) 0%, rgba(255,255,255,0.82) 45%, rgba(255,255,255,0.10) 100%), url("https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=2070"); background-size:cover; background-position:center; border-radius:0 0 16px 16px; padding:26px 28px; border:1px solid #E8EFDE; border-top:none; overflow:hidden; margin: -12px -16px 16px -16px; width: calc(100% + 32px); min-height: 132px; display:flex; align-items:center; }
    .farmer-hero-title { font-family:'DM Serif Display', serif; font-size:22px; color:#1B4332; margin:0; font-weight:400; }
    .farmer-hero-sub { font-family:'Plus Jakarta Sans', sans-serif; font-size:13px; color:#3A4D3D; margin-top:2px; }
    .farmer-hero-meta { display:flex; gap:8px; align-items:center; margin-top:10px; }
    .farmer-pill { display:inline-flex; align-items:center; gap:6px; background:white; border:1px solid #E0EAD6; padding:5px 10px; border-radius:999px; font-size:12px; color:#1B4332; font-weight:600; }
    .farmer-card-title { font-family:'Plus Jakarta Sans', sans-serif; font-size:13px; font-weight:700; color:#1B4332; margin-bottom:10px; display:grid; grid-template-columns:32px 1fr; align-items:center; column-gap:10px; line-height:1; min-height:32px; }
    .farmer-card-title > span:first-child { width:32px; height:32px; flex-shrink:0; display:flex; align-items:center; justify-content:center; }
    .farmer-card-title .material-symbols-outlined { line-height:1 !important; font-size:18px !important; display:flex; align-items:center; justify-content:center; margin:0 !important; }
    .farmer-card-title > span:last-child { display:flex; align-items:center; height:32px; }
    .farmer-big-price { font-family:'DM Serif Display', serif; font-size:30px; color:#0F2A1A; line-height:1; margin:6px 0 4px 0; }
    .farmer-expected-big { font-family:'DM Serif Display', serif; font-size:28px; color:#0F2A1A; line-height:1; margin:4px 0 4px 0; }
    .farmer-trend { font-size:12px; color:#1B7A3D; font-weight:600; display:flex; align-items:center; gap:4px; }
    .farmer-mini-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:10px; background:#FAFAF7; border:1px solid #F0EDE0; border-radius:10px; padding:10px; }
    .farmer-mini-label { font-size:11px; color:#6B7C6E; font-weight:600; }
    .farmer-mini-value { font-size:14px; color:#0F2A1A; font-weight:800; margin-top:2px; }
    .farmer-range-bar { height:8px; background:#F0F0EA; border-radius:999px; overflow:hidden; display:flex; margin-top:8px; }
    .farmer-low-high { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px; }
    .farmer-lh-card { background:white; border:1px solid #E8EFDE; border-radius:10px; padding:10px 12px; }
    .farmer-lh-label { font-size:11px; font-weight:700; color:#6B7C6E; text-transform:uppercase; letter-spacing:0.4px; }
    .farmer-lh-month { font-size:12px; font-weight:600; color:#3A4D3D; }
    .farmer-lh-value { font-size:15px; font-weight:800; color:#0F2A1A; margin-top:2px; }
    @media (max-width: 900px) { .farmer-hero { padding:16px; } }
    </style>
    """, unsafe_allow_html=True)

    with st.sidebar:
        st.markdown('<div style="display:flex; align-items:center; padding:14px 6px 10px 6px;"><div style="font-family:DM Serif Display, serif; font-size:16px; color:#FFFFFF; line-height:1;">PalaySense</div></div>', unsafe_allow_html=True)
        st.markdown('<hr style="border:none; border-top:1px solid rgba(255,255,255,0.12); margin:8px 0;">', unsafe_allow_html=True)
        for grp_label, items in QUICK_VIEW_GROUPS:
            st.markdown(f'<div class="farmer-sidebar-label">{grp_label}</div>', unsafe_allow_html=True)
            for label, icon in items:
                is_active = (st.session_state.get("overview_section") == label)
                display = _farmer_display.get(label, label)
                if st.button(display, icon=f":material/{icon}:" if icon else None, use_container_width=True, type="primary" if is_active else "secondary", key=f"farmer_side_{icon}"):
                    st.session_state["overview_section"] = label
                    st.rerun()
    st.session_state.setdefault("ov_mobile_nav_open", False)
    st.markdown("""
    <style>
    div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] { display: none !important; }
    @media (max-width: 768px) {
        div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] { display: block !important; position: fixed !important; top: 10px !important; right: 12px !important; z-index: 1001 !important; }
        div[data-testid="stElementContainer"]:has(.ov-phone-marker) + div[data-testid="stElementContainer"] .stButton > button { background: #123524 !important; color: #FFFFFF !important; border: none !important; border-radius: 8px !important; padding: 8px 14px !important; height: 38px !important; min-height: 38px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.25) !important; font-weight: 600 !important; }
        section[data-testid="stSidebar"] { display: none !important; }
    }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="ov-phone-marker" style="display:none;"></div>', unsafe_allow_html=True)
    _is_open = st.session_state.get("ov_mobile_nav_open", False)
    _lbl = "Close" if _is_open else "Menu"; _ico = "close" if _is_open else "menu"
    if st.button(_lbl, icon=f":material/{_ico}:", key="ov_phone_toggle", type="primary"):
        st.session_state["ov_mobile_nav_open"] = not _is_open; st.rerun()
    if st.session_state.get("ov_mobile_nav_open", False):
        st.markdown("""<style>@media (max-width: 768px) { section[data-testid="stSidebar"] { display:flex !important; position:fixed !important; left:0 !important; top:0 !important; bottom:0 !important; width:78% !important; max-width:300px !important; min-width:260px !important; z-index:1000 !important; box-shadow:4px 0 24px rgba(0,0,0,0.35) !important; overflow-y:auto !important; } }</style>""", unsafe_allow_html=True)

    price_type = st.session_state.get("farmer_price_type", "Regular")
    ctx = price_ctx["regular"] if price_type=="Regular" else price_ctx["fancy"]
    vals = ctx["vals"]
    labels = ctx["labels"]
    try:
        today = pd.Timestamp.today()
        p_idx = 0
        for i,m in enumerate(forecast_months):
            if m.to_period("M") >= today.to_period("M"):
                p_idx = i
                break
        if p_idx >= len(vals):
            p_idx = 0
    except Exception:
        p_idx = 1 if len(vals)>=2 else 0
    primary_val = float(vals[p_idx]) if p_idx < len(vals) and vals[p_idx] is not None and not pd.isna(vals[p_idx]) else (float(pd.Series(vals).dropna().iloc[0]) if len(pd.Series(vals).dropna())>0 else 0)
    primary_label = labels[p_idx] if p_idx < len(labels) else (labels[0] if labels else "Forecast")
    next_vals = []
    next_labels = []
    for off in range(1,4):
        idx = p_idx+off
        if idx < len(vals) and idx < len(labels):
            if not pd.isna(vals[idx]):
                next_vals.append(float(vals[idx])); next_labels.append(labels[idx])
    if len(next_vals) < 3:
        for i,v in enumerate(vals):
            if labels[i] not in next_labels and labels[i]!=primary_label and not pd.isna(v):
                if len(next_vals)>=3: break
                next_vals.append(float(v)); next_labels.append(labels[i])
    next_vals = next_vals[:3]; next_labels = next_labels[:3]
    yield_avg = yield_ctx.get("avg")
    yield_lo = yield_ctx.get("lo"); yield_hi = yield_ctx.get("hi")
    if yield_lo is None and forecast_quarterly_yield:
        s = pd.Series(forecast_quarterly_yield, dtype=float).dropna()
        if not s.empty:
            yield_lo = float(s.min()); yield_hi = float(s.max())
    price_watch = ctx["trend_sentence"]
    if "rising" in price_watch.lower():
        price_watch_full = f"Prices are forecast to increase toward {ctx['highest'][0] if ctx['highest'] else 'December'}."
    elif "easing" in price_watch.lower():
        price_watch_full = f"Prices are forecast to ease toward {ctx['lowest'][0] if ctx['lowest'] else 'the next months'}."
    else:
        price_watch_full = f"{price_watch}."
    harvest_watch = yield_ctx.get("sentence", "Expected yield remains around 4 MT/ha.")
    if not harvest_watch:
        harvest_watch = f"Expected yield remains around {yield_avg:.2f} MT/ha." if yield_avg else "Expected yield remains around 4 MT/ha."
    lowest = ctx["lowest"]
    highest = ctx["highest"]

    def _render_hero():
        st.markdown(f"""
        <div class="farmer-hero">
            <div style="display:flex; align-items:flex-start; gap:12px;">
                <div style="width:38px; height:38px; background:#E8F5E9; border-radius:10px; display:flex; align-items:center; justify-content:center; border:1px solid #C8E6C9; flex-shrink:0;">
                    <i class="material-symbols-outlined" style="font-size:20px; color:#2E7D32;">eco</i>
                </div>
                <div>
                    <div class="farmer-hero-title">Good day, Farmer!</div>
                    <div class="farmer-hero-sub">Your palay outlook for Bataan — prices and harvest (<i>ani</i>) at a glance</div>
                    <div class="farmer-hero-meta">
                        <span class="farmer-pill"><i class="material-symbols-outlined" style="font-size:16px; color:#2E7D32;">location_on</i> Bataan Province</span>
                        <span class="farmer-pill"><i class="material-symbols-outlined" style="font-size:16px; color:#2E7D32;">calendar_month</i> {primary_label} forecast ()</span>
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    def _render_top_cards(show_harvest=True):
        # helper to render palay price card (shared)
        def _render_price_card():
            with st.container():
                st.markdown('<div class="farmer-card-anchor" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="farmer-card-title"><span style="width:32px; height:32px; background:#E8F5E9; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; border:1px solid #C8E6C9; flex-shrink:0;"><i class="material-symbols-outlined" style="font-size:18px; color:#2E7D32; line-height:1;">payments</i></span><span style="display:flex; align-items:center; line-height:1;">Palay Price Forecast </span></div>', unsafe_allow_html=True)
                t1, t2, t_spacer = st.columns([1,1,2], gap="small")
                with t1:
                    if st.button("Regular", key="farmer_toggle_regular", type="primary" if price_type=="Regular" else "secondary", use_container_width=True):
                        st.session_state["farmer_price_type"]="Regular"; st.rerun()
                with t2:
                    if st.button("Fancy", key="farmer_toggle_fancy", type="primary" if price_type=="Fancy" else "secondary", use_container_width=True):
                        st.session_state["farmer_price_type"]="Fancy"; st.rerun()
                st.markdown(f'<div class="farmer-big-price">₱{primary_val:.2f}/kg</div>', unsafe_allow_html=True)
                st.markdown(f'<div style="font-size:12px; color:#6B7C6E; font-weight:500; margin-top:2px;">{price_type.lower()} palay • {primary_label} forecast </div>', unsafe_allow_html=True)
                st.markdown(f'<div class="farmer-trend" style="margin-top:8px;"><i class="material-symbols-outlined" style="font-size:16px; color:#1B7A3D;">trending_up</i> {ctx["trend_sentence"]}</div>', unsafe_allow_html=True)
                if next_vals and next_labels:
                    cols_html = ""
                    for lab,val in zip(next_labels, next_vals):
                        short = lab
                        cols_html += f'<div><div class="farmer-mini-label">{short}</div><div class="farmer-mini-value">₱{val:.2f}/kg</div></div>'
                    st.markdown(f'<div class="farmer-mini-grid">{cols_html}</div>', unsafe_allow_html=True)

        if not show_harvest:
            # Price Forecast: show only Palay Price card full-width, hide Expected Harvest
            _render_price_card()
            return

        c1, c2 = st.columns([1.15, 0.85], gap="medium")
        with c1:
            _render_price_card()
        with c2:
            with st.container():
                st.markdown('<div class="farmer-card-anchor harvest" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="farmer-card-title"><span style="width:32px; height:32px; background:#FFF8E1; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; border:1px solid #FFE082; flex-shrink:0;"><i class="material-symbols-outlined" style="font-size:18px; color:#F9A825; line-height:1;">eco</i></span><span style="display:flex; align-items:center; line-height:1;">Expected Harvest (Inaasahang Ani)</span></div>', unsafe_allow_html=True)
                if next_yield_val is not None:
                    st.markdown(f'<div class="farmer-expected-big">{next_yield_val:.2f} tons/ha</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:12px; color:#6B7C6E; font-weight:500;">Forecast for {y_labels[0] if y_labels else "next harvest"} • about {next_yield_val*1000:,.0f} kg per hectare</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="farmer-expected-big">Not yet available</div>', unsafe_allow_html=True)
                if yield_lo is not None and yield_hi is not None:
                    st.markdown(f"""
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; background:white; border:1px solid #F2E8C8; border-radius:10px; padding:10px;">
                        <div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">Expected range</div><div style="font-size:13px; font-weight:800; color:#0F2A1A; margin-top:2px;">{yield_lo:.2f} – {yield_hi:.2f} tons/ha</div></div>
                        <div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">Change vs last harvest (<i>ani</i>)</div><div style="font-size:13px; font-weight:800; color:#1B7A3D; margin-top:2px; display:flex; align-items:center; gap:4px;"><i class="material-symbols-outlined" style="font-size:14px; color:#1B7A3D;">{"trending_up" if (yield_delta_prev is not None and yield_delta_prev>=0) else "trending_down"}</i> {f"{yield_delta_prev:+.2f} tons/ha" if yield_delta_prev is not None else "No data yet"}</div></div>
                    </div>
                    """, unsafe_allow_html=True)
                    try:
                        span = (yield_hi - yield_lo) if yield_hi!=yield_lo else 0.2
                        pct = ((next_yield_val - yield_lo)/span*100) if next_yield_val is not None else 50
                        pct = max(8, min(92, pct))
                        bar_w = pct
                        st.markdown(f'<div class="farmer-range-bar"><div style="width:{bar_w:.0f}%; background:#2E7D32; border-radius:999px;"></div><div style="flex:1; background:#AED581; opacity:0.6;"></div></div>', unsafe_allow_html=True)
                    except Exception:
                        pass

    def _render_chart_and_what():
        c_chart, c_what = st.columns([1.65, 0.85], gap="medium")
        with c_chart:
            with st.container():
                st.markdown('<div class="farmer-card-anchor" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="farmer-card-title"><i class="material-symbols-outlined" style="font-size:18px; color:#1B4332;">show_chart</i> Palay Price Trend ( ng Presyo)</div>', unsafe_allow_html=True)
                fig = _farmer_price_chart(forecast_months, vals, color="#1B5E20")
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
                if lowest and highest and lowest[1] is not None and highest[1] is not None:
                    st.markdown(f"""
                    <div class="farmer-low-high">
                        <div class="farmer-lh-card" style="border-left:3px solid #C62828;">
                            <div class="farmer-lh-label"><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; color:#C62828;">trending_down</i> Lowest price</div>
                            <div class="farmer-lh-month">{lowest[0]}</div>
                            <div class="farmer-lh-value">₱{lowest[1]:.2f}/kg</div>
                        </div>
                        <div class="farmer-lh-card" style="border-left:3px solid #2E7D32;">
                            <div class="farmer-lh-label"><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; color:#2E7D32;">trending_up</i> Highest price</div>
                            <div class="farmer-lh-month">{highest[0]}</div>
                            <div class="farmer-lh-value">₱{highest[1]:.2f}/kg</div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown(f'<div style="background:#E8F5E9; border:1px solid #C8E6C9; border-radius:8px; padding:8px 12px; margin-top:10px; font-size:12px; color:#1B5E20; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="font-size:16px; color:#1B5E20;">lightbulb</i> {ctx["recover_sentence"]}</div>', unsafe_allow_html=True)
        with c_what:
            with st.container():
                st.markdown('<div class="farmer-card-anchor" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="farmer-card-title"><i class="material-symbols-outlined" style="font-size:18px; color:#1B4332;">visibility</i> What to Watch — Gabay</div>', unsafe_allow_html=True)
                st.markdown(f"""
                <div class="farmer-what-row" style="background: transparent; border: none; border-bottom: 1px solid #F3F4F6; border-radius: 0; padding: 10px 0; display:flex; gap:12px; align-items:flex-start;">
                    <div style="width:28px; height:28px; background:#FFF8E1; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:1px solid #FFE082;"><i class="material-symbols-outlined" style="font-size:16px; color:#F9A825;">sell</i></div>
                    <div><div style="font-size:11px; font-weight:700; color:#6B7C6E; text-transform:uppercase; letter-spacing:0.4px;">Price</div><div style="font-size:12px; color:#3A4D3D; line-height:1.5; margin-top:2px;">{price_watch_full}</div></div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(f"""
                <div class="farmer-what-row" style="background: transparent; border: none; border-bottom: 1px solid #F3F4F6; border-radius: 0; padding: 10px 0; display:flex; gap:12px; align-items:flex-start;">
                    <div style="width:28px; height:28px; background:#E8F5E9; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:1px solid #C8E6C9;"><i class="material-symbols-outlined" style="font-size:16px; color:#2E7D32;">eco</i></div>
                    <div><div style="font-size:11px; font-weight:700; color:#6B7C6E; text-transform:uppercase;">Harvest</div><div style="font-size:12px; color:#3A4D3D; line-height:1.5; margin-top:2px;">{harvest_watch}</div></div>
                </div>
                """, unsafe_allow_html=True)
                st.markdown("""
                <div class="farmer-what-row" style="background: transparent; border: none; padding: 10px 0; display:flex; gap:12px; align-items:flex-start;">
                    <div style="width:28px; height:28px; background:#FFEBEE; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:1px solid #FFCDD2;"><i class="material-symbols-outlined" style="font-size:16px; color:#C62828;">info</i></div>
                    <div><div style="font-size:11px; font-weight:700; color:#6B7C6E; text-transform:uppercase;">Reminder (Paalala)</div><div style="font-size:12px; color:#3A4D3D; line-height:1.5; margin-top:2px;">Actual price from your buyer (farmgate price) may be different. Please check your buyer offer, drying and storage costs, and your <i>abono</i> (fertilizer) expenses before deciding when to sell.</div></div>
                </div>
                """, unsafe_allow_html=True)

    def _render_municipal_outlook():
        with st.container():
            st.markdown('<div class="farmer-muni-card-anchor" style="display:none;"></div>', unsafe_allow_html=True)
            st.markdown('<div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;">', unsafe_allow_html=True)
            st.markdown('<div><div class="farmer-card-title" style="margin-bottom:2px;"><i class="material-symbols-outlined" style="font-size:18px; color:#1B4332;">location_on</i> Price by Town (Presyo per Bayan)</div><div style="font-size:12px; color:#6B7C6E;">Choose your town to see the palay price forecast (<i> ng presyo</i>) for the next 3 months — based on local data.</div></div>', unsafe_allow_html=True)
            sel = st.selectbox("Choose town (Piliin ang bayan)", options=all_munis, key="farmer_muni_select", label_visibility="collapsed", index=all_munis.index(st.session_state["farmer_selected_muni"]) if st.session_state["farmer_selected_muni"] in all_munis else 0)
            if sel != st.session_state["farmer_selected_muni"]:
                st.session_state["farmer_selected_muni"] = sel
            st.markdown('</div>', unsafe_allow_html=True)
            _muni = st.session_state["farmer_selected_muni"]
            _df = df_municipal_forecasts
            if _df is None or _df.empty:
                st.info("No price forecast per town is available yet. Please check again later.")
                return
            _df_tmp = _df.copy()
            _df_tmp.columns = [str(c).strip() for c in _df_tmp.columns]
            _mcol = next((c for c in _df_tmp.columns if c.lower()=="municipality"), None)
            if _mcol is None:
                st.info("No price forecast per town is available.")
                return
            _sub = _df_tmp[_df_tmp[_mcol].astype(str).str.lower() == str(_muni).lower()]
            if _sub.empty:
                st.info(f"No forecast data for {_muni} yet. Please try another town.")
                return
            _m1 = next((c for c in _df_tmp.columns if c.lower()=="month 1"), None)
            _m2 = next((c for c in _df_tmp.columns if c.lower()=="month 2"), None)
            _m3 = next((c for c in _df_tmp.columns if c.lower()=="month 3"), None)
            _l1 = next((c for c in _df_tmp.columns if c.lower()=="forecast_month_1_label"), None)
            _l2 = next((c for c in _df_tmp.columns if c.lower()=="forecast_month_2_label"), None)
            _l3 = next((c for c in _df_tmp.columns if c.lower()=="forecast_month_3_label"), None)
            # --- Binhi + Klase specific: Inbred vs Hybrid x Regular (ordinary) vs Premium ---
            _type_col = next((c for c in _df_tmp.columns if c.lower()=="rice type & season"), None)
            try:
                # Helper to filter by binhi + klase
                def _filt(binhi, klase):
                    if _type_col is None or _type_col not in _sub.columns:
                        return _sub
                    mask = _sub[_type_col].astype(str).str.contains(binhi, case=False, na=False) & _sub[_type_col].astype(str).str.contains(klase, case=False, na=False)
                    return _sub[mask]
                _ir_sub = _filt("inbred", "ordinary")
                _hr_sub = _filt("hybrid", "ordinary")
                _ip_sub = _filt("inbred", "premium")
                _hp_sub = _filt("hybrid", "premium")
                # Also keep Regular/Premium aggregates (avg across binhi) for backward compat & insight
                _reg_sub = _sub[_sub[_type_col].astype(str).str.contains("ordinary", case=False, na=False)] if _type_col else _sub
                _prem_sub = _sub[_sub[_type_col].astype(str).str.contains("premium", case=False, na=False)] if _type_col else pd.DataFrame()
                if _reg_sub.empty:
                    _reg_sub = _sub
                if _prem_sub.empty:
                    _prem_sub = _sub
                # fallback for specific combos: if empty, use aggregate
                if _ir_sub.empty:
                    _ir_sub = _reg_sub
                if _hr_sub.empty:
                    _hr_sub = _reg_sub
                if _ip_sub.empty:
                    _ip_sub = _prem_sub
                if _hp_sub.empty:
                    _hp_sub = _prem_sub
                p1_ir = float(pd.to_numeric(_ir_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2_ir = float(pd.to_numeric(_ir_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3_ir = float(pd.to_numeric(_ir_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
                p1_hr = float(pd.to_numeric(_hr_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2_hr = float(pd.to_numeric(_hr_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3_hr = float(pd.to_numeric(_hr_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
                p1_ip = float(pd.to_numeric(_ip_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2_ip = float(pd.to_numeric(_ip_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3_ip = float(pd.to_numeric(_ip_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
                p1_hp = float(pd.to_numeric(_hp_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2_hp = float(pd.to_numeric(_hp_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3_hp = float(pd.to_numeric(_hp_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
                p1_reg = float(pd.to_numeric(_reg_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2_reg = float(pd.to_numeric(_reg_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3_reg = float(pd.to_numeric(_reg_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
                p1_prem = float(pd.to_numeric(_prem_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2_prem = float(pd.to_numeric(_prem_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3_prem = float(pd.to_numeric(_prem_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
                # for backward compat, keep overall avg as p1/p2/p3
                p1 = float(pd.to_numeric(_sub[_m1], errors="coerce").dropna().mean()) if _m1 else None
                p2 = float(pd.to_numeric(_sub[_m2], errors="coerce").dropna().mean()) if _m2 else None
                p3 = float(pd.to_numeric(_sub[_m3], errors="coerce").dropna().mean()) if _m3 else None
            except Exception:
                p1=p2=p3=None
                p1_reg=p2_reg=p3_reg=None
                p1_prem=p2_prem=p3_prem=None
                p1_ir=p2_ir=p3_ir=None
                p1_hr=p2_hr=p3_hr=None
                p1_ip=p2_ip=p3_ip=None
                p1_hp=p2_hp=p3_hp=None
            try:
                lab1 = str(_sub[_l1].dropna().iloc[0]) if _l1 and not _sub[_l1].dropna().empty else "Month 1"
                lab2 = str(_sub[_l2].dropna().iloc[0]) if _l2 and not _sub[_l2].dropna().empty else "Month 2"
                lab3 = str(_sub[_l3].dropna().iloc[0]) if _l3 and not _sub[_l3].dropna().empty else "Month 3"
            except Exception:
                lab1, lab2, lab3 = "Month 1","Month 2","Month 3"
            muni_vals = [v for v in [p1,p2,p3] if v is not None and not pd.isna(v)]
            muni_avg = float(pd.Series(muni_vals).mean()) if muni_vals else None
            muni_lo = float(pd.Series(muni_vals).min()) if muni_vals else None
            muni_hi = float(pd.Series(muni_vals).max()) if muni_vals else None
            if muni_vals and p1 is not None and p3 is not None and muni_hi is not None and muni_lo is not None:
                delta = float(p3 - p1)
                spread = float(muni_hi - muni_lo)
                if delta > 0.30:
                    trend_label = "Prices Rising"
                    badge = "Prices Rising"
                    bcol="#E8F5E9"; tcol="#1B5E20"; ico="trending_up"
                    insight = f"Prices in <b>{_muni}</b> are forecast to <b>increase</b> from {lab1} (₱{p1:.2f}/kg) to {lab3} (₱{p3:.2f}/kg) on average. This varies by <b>binhi</b> (Inbred/Hybrid) and <b>klase</b> (Regular/Premium) — see the specific table below. Please compare with your buyer offer, moisture level, and drying or storage costs when planning."
                elif delta < -0.30:
                    trend_label = "Prices Easing"
                    badge = "Prices Easing"
                    bcol="#FFEBEE"; tcol="#C62828"; ico="trending_down"
                    insight = f"Prices in <b>{_muni}</b> are forecast to <b>ease</b> from {lab1} (₱{p1:.2f}/kg) to {lab3} (₱{p3:.2f}/kg) on average. This varies by <b>binhi</b> (Inbred/Hybrid) and <b>klase</b> (Regular/Premium) — see the specific table below. Please compare with your buyer offer, moisture level, and drying or storage costs when planning."
                else:
                    if spread < 0.35:
                        trend_label = "Steady Prices"
                        badge = "Steady Prices"
                        bcol="#F5F5F5"; tcol="#2E7D32"; ico="trending_flat"
                        insight = f"Prices in <b>{_muni}</b> are forecast to remain <b>fairly steady</b> around <b>₱{muni_avg:.2f}/kg</b> on average (range ₱{muni_lo:.2f}–₱{muni_hi:.2f}/kg). This varies by <b>binhi</b> and <b>klase</b> — see the specific table below. Please compare with your buyer offer, moisture level, and drying or storage costs when planning."
                    else:
                        trend_label = "Slightly Variable"
                        badge = "Slightly Variable"
                        bcol="#FFF8E1"; tcol="#8D6E00"; ico="swap_vert"
                        insight = f"Prices in <b>{_muni}</b> vary slightly in the next 3 months (range ₱{muni_lo:.2f}–₱{muni_hi:.2f}/kg, average ₱{muni_avg:.2f}/kg). The trend from {lab1} to {lab3} is generally stable but differs by binhi and klase — see Inbred/Hybrid × Regular/Premium table below. Please compare with your buyer offer and field conditions."
            else:
                trend_label = "Town Forecast"
                badge="Town Forecast"; bcol="#E3F2FD"; tcol="#1565C0"; ico="info"
                insight = f"In <b>{_muni}</b>, the next 3 months are forecast around <b>₱{muni_avg:.2f}/kg</b> on average. This may be different for Regular and Premium types — see the table below. Please compare with your buyer offer and field conditions."
            if muni_vals:
                # Binhi x Klase breakdown (specific hybrid/inbred)
                reg_vals = [v for v in [p1_reg,p2_reg,p3_reg] if v is not None and not pd.isna(v)]
                prem_vals = [v for v in [p1_prem,p2_prem,p3_prem] if v is not None and not pd.isna(v)]
                reg_avg = float(pd.Series(reg_vals).mean()) if reg_vals else None
                prem_avg = float(pd.Series(prem_vals).mean()) if prem_vals else None
                # Ensure specific values have fallbacks
                def _fmt(v):
                    return f"₱{v:.2f}/kg" if v is not None and not pd.isna(v) else "—"
                st.markdown(f"""
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px;">
                    <div style="background:#F6FBF6; border:1px solid #C8E6C9; border-radius:12px; padding:12px;">
                        <div style="font-size:11px; font-weight:600; color:#6B7C6E; margin-bottom:8px; display:flex; align-items:center; gap:6px;"><i class="material-symbols-outlined" style="font-size:16px; color:#2E7D32;">payments</i> Forecast price — {_muni} <span style="font-weight:400; color:#8AA090; font-size:10px; margin-left:4px;">(by binhi & palay type — avg of dry & wet)</span></div>
                        <div style="background:white; border:1px solid #E8EFDE; border-radius:10px; padding:10px; margin-bottom:8px;">
                            <div style="font-size:10px; font-weight:700; color:#7FB094; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:6px;">By binhi & palay type — specific (hybrid / inbred)</div>
                            <div style="display:grid; grid-template-columns: 140px 1fr 1fr 1fr; gap:6px; align-items:center; font-size:11px; color:#6B7C6E; font-weight:600; padding-bottom:4px; border-bottom:1px solid #F3F4F6;">
                                <div></div><div style="text-align:center;">{lab1}</div><div style="text-align:center;">{lab2}</div><div style="text-align:center;">{lab3}</div>
                            </div>
                            <div style="display:grid; grid-template-columns: 140px 1fr 1fr 1fr; gap:6px; align-items:center; padding:6px 0; border-bottom:1px solid #F3F4F6;">
                                <div style="font-size:11px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:4px;"><span style="width:8px; height:8px; background:#C8E6C9; border-radius:50%; display:inline-block;"></span> Inbred – Regular</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p1_ir)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p2_ir)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p3_ir)}</div>
                            </div>
                            <div style="display:grid; grid-template-columns: 140px 1fr 1fr 1fr; gap:6px; align-items:center; padding:6px 0; border-bottom:1px solid #F3F4F6;">
                                <div style="font-size:11px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:4px;"><span style="width:8px; height:8px; background:#AED581; border-radius:50%; display:inline-block;"></span> Hybrid – Regular</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p1_hr)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p2_hr)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p3_hr)}</div>
                            </div>
                            <div style="display:grid; grid-template-columns: 140px 1fr 1fr 1fr; gap:6px; align-items:center; padding:6px 0; border-bottom:1px solid #F3F4F6;">
                                <div style="font-size:11px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:4px;"><span style="width:8px; height:8px; background:#A3E4A0; border-radius:50%; display:inline-block;"></span> Inbred – Premium</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p1_ip)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p2_ip)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p3_ip)}</div>
                            </div>
                            <div style="display:grid; grid-template-columns: 140px 1fr 1fr 1fr; gap:6px; align-items:center; padding:6px 0;">
                                <div style="font-size:11px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:4px;"><span style="width:8px; height:8px; background:#66BB6A; border-radius:50%; display:inline-block;"></span> Hybrid – Premium</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p1_hp)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p2_hp)}</div>
                                <div style="text-align:center; font-size:12.5px; font-weight:800; color:#0F2A1A;">{_fmt(p3_hp)}</div>
                            </div>
                            <div style="font-size:10px; color:#8AA090; margin-top:6px; line-height:1.4;">Specific na <i>prediksyon </i> kada <b>binhi</b> (Inbred / Hybrid) at <b>klase</b> (Regular = ordinary, Premium). Each value is average of Dry & Wet season for that town. See chart below for full season breakdown.</div>
                        </div>
                        <div style="display:flex; align-items:center; gap:8px; margin-top:8px; flex-wrap:wrap;">
                            <span style="background:{bcol}; color:{tcol}; padding:4px 10px; border-radius:999px; font-size:11px; font-weight:700; display:inline-flex; align-items:center; gap:4px; border:1px solid rgba(0,0,0,0.06);"><i class="material-symbols-outlined" style="font-size:14px; color:{tcol};">{ico}</i> {badge}</span>
                            <span style="font-size:11px; color:#6B7C6E;">Avg ₱{muni_avg:.2f}/kg • Range ₱{muni_lo:.2f}–₱{muni_hi:.2f}</span>
                        </div>
                    </div>
                    <div style="background:white; border:1px solid #E8EFDE; border-radius:12px; padding:12px; display:flex; gap:12px; align-items:flex-start; border-left:4px solid {tcol};">
                        <div style="width:38px; height:38px; background:{bcol}; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0; border:1px solid rgba(0,0,0,0.06);"><i class="material-symbols-outlined" style="font-size:18px; color:{tcol};">{ico}</i></div>
                        <div style="flex:1;">
                            <div style="display:inline-flex; align-items:center; gap:4px; background:{bcol}; color:{tcol}; padding:4px 10px; border-radius:999px; font-weight:700; font-size:11px; margin-bottom:6px; border:1px solid rgba(0,0,0,0.06); text-transform:uppercase; letter-spacing:0.4px;"><i class="material-symbols-outlined" style="font-size:14px; color:{tcol};">{ico}</i> {trend_label}</div>
                            <div style="font-size:12px; color:#3A4D3D; line-height:1.6;">{insight}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                    st.info("No price forecast data for this town yet. Please check again later.")
        st.markdown('<div style="background:#FFFDF0; border:1px solid #F2E8C8; border-radius:10px; padding:8px 12px; margin-top:10px; display:flex; align-items:center; gap:8px; font-size:11px; color:#6B7C6E;"><i class="material-symbols-outlined" style="font-size:16px; color:#F9A825;">lightbulb</i> These are estimates for palay prices per town for the next 3 months. Actual prices from your buyer (farmgate price) may be different depending on variety, moisture, and location. <span style="margin-left:auto; color:#1B4332; font-weight:700; cursor:pointer;">Learn more →</span></div>', unsafe_allow_html=True)

    if section_choice == "Overview":
        _render_hero()
        _render_top_cards()
        _render_chart_and_what()
        _render_municipal_outlook()
    elif section_choice == "Price Forecast":
        _render_hero()
        st.markdown('<div style="background:linear-gradient(90deg,#F6FBF6 0%, #FFFFFF 100%); border:1px solid #E8EFDE; border-radius:14px; padding:14px 16px; margin-bottom:12px; display:flex; align-items:center; gap:12px;"><i class="material-symbols-outlined" style="font-size:22px; color:#1B4332;">payments</i><div><div style="font-weight:700; color:#1B4332; font-size:14px;">Palay Price Forecast (<i> ng Presyo</i>)</div><div style="font-size:12px; color:#6B7C6E;">See the current forecast, the coming months, and what it means for you.</div></div></div>', unsafe_allow_html=True)
        _render_top_cards(show_harvest=False)
        _render_chart_and_what()
        st.markdown('<div style="background:#FFFDF0; border:1px solid #F2E8C8; border-radius:10px; padding:8px 12px; margin-top:10px; font-size:11px; color:#6B7C6E; text-align:center;">Tip: Please compare this outlook with your buyer offer, storage and drying costs, and field conditions before deciding when to sell.</div>', unsafe_allow_html=True)
    elif section_choice == "Harvest Forecast":
        _render_hero()
        c1,c2 = st.columns([1.05,0.95], gap="medium")
        with c1:
            with st.container():
                st.markdown('<div class="farmer-card-anchor harvest" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="farmer-card-title"><span style="width:32px; height:32px; background:#FFF8E1; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; border:1px solid #FFE082; flex-shrink:0;"><i class="material-symbols-outlined" style="font-size:18px; color:#F9A825; line-height:1;">eco</i></span><span style="display:flex; align-items:center; line-height:1;">Expected Harvest (Inaasahang Ani)</span></div>', unsafe_allow_html=True)
                if next_yield_val is not None:
                    st.markdown(f'<div class="farmer-expected-big">{next_yield_val:.2f} tons/ha</div>', unsafe_allow_html=True)
                    st.markdown(f'<div style="font-size:12px; color:#6B7C6E;">Forecast (<i></i>) for {y_labels[0] if y_labels else "next harvest"} — about {next_yield_val*1000:,.0f} kg per hectare</div>', unsafe_allow_html=True)
                    if yield_lo is not None and yield_hi is not None:
                        st.markdown(f"""
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:12px; background:white; border:1px solid #F2E8C8; border-radius:10px; padding:10px;">
                            <div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">Expected range</div><div style="font-size:13px; font-weight:800; color:#0F2A1A; margin-top:2px;">{yield_lo:.2f} – {yield_hi:.2f} tons/ha</div></div>
                            <div><div style="font-size:11px; color:#6B7C6E; font-weight:600;">Change vs last harvest (<i>ani</i>)</div><div style="font-size:13px; font-weight:800; color:#1B7A3D; margin-top:2px; display:flex; align-items:center; gap:4px;"><i class="material-symbols-outlined" style="font-size:14px; color:#1B7A3D;">{"trending_up" if (yield_delta_prev is not None and yield_delta_prev>=0) else "trending_down"}</i> {f"{yield_delta_prev:+.2f} tons/ha" if yield_delta_prev is not None else "No data yet"}</div></div>
                        </div>
                        """, unsafe_allow_html=True)
                        try:
                            span = (yield_hi - yield_lo) if yield_hi!=yield_lo else 0.2
                            pct = ((next_yield_val - yield_lo)/span*100) if next_yield_val is not None else 50
                            pct = max(8, min(92, pct))
                            bar_w = pct
                            st.markdown(f'<div class="farmer-range-bar"><div style="width:{bar_w:.0f}%; background:#2E7D32; border-radius:999px;"></div><div style="flex:1; background:#AED581; opacity:0.6;"></div></div>', unsafe_allow_html=True)
                        except Exception:
                            pass
            with st.container():
                st.markdown('<div class="farmer-card-anchor harvest" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div style="background:white; border:1px solid #E8EFDE; border-radius:12px; padding:12px; display:flex; gap:10px; align-items:center; border-left:4px solid #2E7D32;"><i class="material-symbols-outlined" style="font-size:18px; color:#2E7D32;">visibility</i><div><div style="font-size:12px; font-weight:700; color:#1B4332;">What to Watch (Gabay)</div><div style="font-size:12px; color:#6B7C6E;">Simple guide for the next harvest period.</div></div></div>', unsafe_allow_html=True)

        # ---- Harvest (Ani) — Historical Yield Trend + Benchmark Filters ----
        st.markdown("""
        <style>
        .harvest-filter-card { background:white; border:1px solid #E8EFDE; border-radius:16px; padding:14px 16px; margin-top:14px; box-shadow:0 2px 8px rgba(0,0,0,0.04); }
        .harvest-filter-title { font-size:12px; font-weight:700; color:#1B4332; display:flex; align-items:center; gap:6px; margin-bottom:10px; }
        </style>
        """, unsafe_allow_html=True)
        with st.container():
            st.markdown('<div class="farmer-card-anchor" style="display:none;"></div>', unsafe_allow_html=True)
            st.markdown('<div class="harvest-filter-card"><div class="harvest-filter-title"><i class="material-symbols-outlined" style="font-size:18px; color:#1B4332;">tune</i> View Options — Past Harvest & Comparison (Gabay)</div>', unsafe_allow_html=True)
            st.session_state.setdefault("harvest_trend_range", "Last 10 Years")
            st.session_state.setdefault("harvest_agg", "Annual (Yearly Avg)")
            st.session_state.setdefault("harvest_benchmarks", [])
            f1, f2, f3 = st.columns([1,1,1.2], gap="small")
            with f1:
                trend_range = st.selectbox("Years to Show", options=["Last 5 Years","Last 10 Years","All Years (2015–2026)"], key="harvest_trend_range", help="Choose how many past years to show")
            with f2:
                agg = st.selectbox("View", options=["Yearly Average","Every Quarter (Q1–Q4)","Dry vs Wet Season"], key="harvest_agg", help="Yearly = average per year, Quarterly = every quarter, Season = dry vs wet season (tag-araw vs tag-ulan)")
            with f3:
                benchmarks = st.multiselect("Compare With", options=["Bataan 10-Year Average","DA Target (4.5 tons/ha)"], key="harvest_benchmarks", help="Show a guide line for comparison")
            st.markdown('</div>', unsafe_allow_html=True)

        # Prepare historical yield data
        try:
            hist_df = provincial_df.copy() if provincial_df is not None and not provincial_df.empty else pd.DataFrame()
            # Determine year window
            _end_year = int(pd.to_datetime(hist_df["date"]).dt.year.max()) if not hist_df.empty and "date" in hist_df.columns else 2026
            if trend_range == "Last 5 Years":
                _start_year = _end_year - 4
            elif trend_range == "Last 10 Years":
                _start_year = _end_year - 9
            else:
                _start_year = int(pd.to_datetime(hist_df["date"]).dt.year.min()) if not hist_df.empty else 2015
            # Filter by year window for display
            if not hist_df.empty and "date" in hist_df.columns:
                _y = pd.to_datetime(hist_df["date"]).dt.year
                hist_view = hist_df[(_y >= _start_year) & (_y <= _end_year)].copy()
            else:
                hist_view = hist_df.copy()
            # Keep quarterly yield series
            _qdf = dl.get_quarterly_yield(hist_view) if not hist_view.empty else pd.DataFrame()
            # Compute 10yr avg benchmark value (last 10 years mean)
            try:
                _all_q = dl.get_quarterly_yield(provincial_df) if provincial_df is not None and not provincial_df.empty else pd.DataFrame()
                if not _all_q.empty and "quarterly_yield_mt_per_ha" in _all_q.columns:
                    _all_q["_yr"] = pd.to_numeric(_all_q["year"], errors="coerce")
                    _last10 = _all_q[_all_q["_yr"] >= (_end_year - 9)]
                    ten_yr_avg = float(pd.to_numeric(_last10["quarterly_yield_mt_per_ha"], errors="coerce").dropna().mean()) if not _last10.empty else float(pd.to_numeric(_all_q["quarterly_yield_mt_per_ha"], errors="coerce").dropna().mean())
                else:
                    ten_yr_avg = None
            except Exception:
                ten_yr_avg = None
            da_target = 4.50
            # Build historical trend chart data by aggregation
            if not _qdf.empty:
                if agg == "Yearly Average":
                    grp = _qdf.groupby("year")["quarterly_yield_mt_per_ha"].mean().reset_index()
                    grp["label"] = grp["year"].astype(str)
                    x_title = "Year"
                elif agg == "Every Quarter (Q1–Q4)":
                    grp = _qdf.copy()
                    grp["label"] = "Q" + grp["quarter"].astype(str) + " " + grp["year"].astype(str)
                    x_title = "Quarter"
                else:  # Dry vs Wet Season
                    _qdf["season"] = np.where(_qdf["quarter"].isin([1,2]), "Dry", "Wet")
                    grp = _qdf.groupby(["year","season"])["quarterly_yield_mt_per_ha"].mean().reset_index()
                    grp["label"] = grp["year"].astype(str) + " " + grp["season"]
                    grp = grp.sort_values(["year","season"], key=lambda s: s.map({"Dry":0,"Wet":1}) if s.name=="season" else s)
                    x_title = "Year – Season (Dry/Wet)"
            else:
                grp = pd.DataFrame()
                x_title = "Year"
        except Exception:
            grp = pd.DataFrame()
            ten_yr_avg = None
            da_target = 4.50
            x_title = "Year"
            hist_view = pd.DataFrame()

        # Render two charts side-by-side: Historical Trend | Forecast + Benchmark
        ch1, ch2 = st.columns([1.35, 0.95], gap="medium")
        with ch1:
            with st.container():
                st.markdown('<div class="farmer-card-anchor" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="farmer-card-title"><i class="material-symbols-outlined" style="font-size:18px; color:#5D4037;">show_chart</i> Historical Yield Trend — {trend_range} • {agg}</div>', unsafe_allow_html=True)
                if grp.empty:
                    st.info("No historical yield data for the selected range.")
                else:
                    # Line chart with markers
                    fig_hist = go.Figure()
                    fig_hist.add_trace(go.Scatter(x=grp["label"], y=grp["quarterly_yield_mt_per_ha"], mode="lines+markers", name="Historical Yield", line=dict(color="#2E7D32", width=2.4), marker=dict(size=6, color="#2E7D32", line=dict(width=1.5, color="white")), hovertemplate="<b>%{x}</b><br>Yield: %{y:.2f} MT/ha<extra></extra>"))
                    # Peak annotation
                    try:
                        _peak_idx = grp["quarterly_yield_mt_per_ha"].idxmax()
                        if pd.notna(_peak_idx):
                            _pr = grp.loc[_peak_idx]
                            fig_hist.add_annotation(x=_pr["label"], y=float(_pr["quarterly_yield_mt_per_ha"]), text=f"▲ Peak {float(_pr['quarterly_yield_mt_per_ha']):.2f}", showarrow=True, arrowhead=2, ax=0, ay=-32, font=dict(size=10, color="#1B5E20"), bgcolor="rgba(255,255,255,0.92)", bordercolor="#2E7D32", borderwidth=1, borderpad=3)
                    except Exception:
                        pass
                    # Benchmark lines — farmer-friendly labels
                    if "Bataan 10-Year Average" in benchmarks and ten_yr_avg is not None and not pd.isna(ten_yr_avg):
                        try:
                            fig_hist.add_hline(y=float(ten_yr_avg), line_dash="dot", line_width=1.4, line_color="#78909C", annotation_text=f"Bataan 10-Yr Avg {float(ten_yr_avg):.2f}", annotation_position="top left", annotation=dict(font=dict(size=10, color="#607D8B"), bgcolor="rgba(255,255,255,0.9)"))
                        except Exception:
                            pass
                    if "DA Target (4.5 tons/ha)" in benchmarks:
                        try:
                            fig_hist.add_hline(y=4.50, line_dash="dot", line_width=1.4, line_color="#2E7D32", annotation_text="DA Target 4.5", annotation_position="bottom left", annotation=dict(font=dict(size=10, color="#2E7D32"), bgcolor="rgba(232,245,233,0.95)"))
                        except Exception:
                            pass
                    # Y zoom with 0.05 dtick like LGU
                    try:
                        import math
                        _mn = float(grp["quarterly_yield_mt_per_ha"].min()); _mx = float(grp["quarterly_yield_mt_per_ha"].max())
                        _lo = math.floor((_mn - 0.12)/0.05)*0.05; _hi = math.ceil((_mx + 0.12)/0.05)*0.05
                        if "DA Target (4.5 tons/ha)" in benchmarks:
                            _hi = max(_hi, 4.62)
                        _lo = max(3.0, _lo)
                    except Exception:
                        _lo, _hi = None, None
                    fig_hist.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10), xaxis_title=x_title, yaxis_title="tons/ha", plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.28, xanchor="center", x=0.5, font=dict(size=10)), xaxis=dict(gridcolor="#F3F4F6", showgrid=True, tickangle=-30 if agg=="Every Quarter (Q1–Q4)" else 0), yaxis=dict(gridcolor="#F3F4F6", showgrid=True, range=[_lo,_hi] if _lo is not None else None, dtick=0.10 if agg!="Every Quarter (Q1–Q4)" else 0.12))
                    st.plotly_chart(fig_hist, use_container_width=True, config={"displayModeBar": False})
                    # Compact stats under chart
                    try:
                        _avg = float(grp["quarterly_yield_mt_per_ha"].mean()); _mnv = float(grp["quarterly_yield_mt_per_ha"].min()); _mxv = float(grp["quarterly_yield_mt_per_ha"].max())
                        _delta = float(grp["quarterly_yield_mt_per_ha"].iloc[-1] - grp["quarterly_yield_mt_per_ha"].iloc[0]) if len(grp)>1 else 0.0
                        _trend_icon = "trending_up" if _delta>=0 else "trending_down"
                        _trend_col = "#1B7A3D" if _delta>=0 else "#C62828"
                        st.markdown(f"""
                        <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; margin-top:8px;">
                            <div style="background:#FAFAF7; border:1px solid #F0EDE0; border-radius:10px; padding:8px; text-align:center;"><div style="font-size:10px; color:#6B7C6E; font-weight:600;">Average</div><div style="font-size:13px; font-weight:800; color:#0F2A1A;">{_avg:.2f} tons/ha</div></div>
                            <div style="background:white; border:1px solid #E8EFDE; border-radius:10px; padding:8px; text-align:center;"><div style="font-size:10px; color:#6B7C6E; font-weight:600;">Range</div><div style="font-size:12px; font-weight:700; color:#0F2A1A;">{_mnv:.2f} – {_mxv:.2f}</div></div>
                            <div style="background:white; border:1px solid #E8EFDE; border-radius:10px; padding:8px; text-align:center; display:flex; flex-direction:column; align-items:center; justify-content:center;"><div style="font-size:10px; color:#6B7C6E; font-weight:600;">Change</div><div style="font-size:12px; font-weight:700; color:{_trend_col}; display:flex; align-items:center; gap:4px;"><i class="material-symbols-outlined" style="font-size:14px; color:{_trend_col};">{_trend_icon}</i> { _delta:+.2f}</div></div>
                        </div>
                        """, unsafe_allow_html=True)
                        # Benchmark comparison caption — simple language
                        if benchmarks:
                            _caps = []
                            if "Bataan 10-Year Average" in benchmarks and ten_yr_avg is not None:
                                _diff = float(_avg - ten_yr_avg)
                                _caps.append(f"vs Bataan 10-yr avg ({ten_yr_avg:.2f}): <b style='color:{'#1B7A3D' if _diff>=0 else '#C62828'};'>{_diff:+.2f} tons/ha</b>")
                            if "DA Target (4.5 tons/ha)" in benchmarks:
                                _diff2 = float(_avg - 4.50)
                                _caps.append(f"vs DA target (4.5): <b style='color:{'#1B7A3D' if _diff2>=0 else '#C62828'};'>{_diff2:+.2f} tons/ha</b>")
                            if _caps:
                                st.markdown(f"<div style='font-size:11px; color:#3A4D3D; background:#F6FBF6; border:1px solid #E8EFDE; border-radius:8px; padding:8px 10px; margin-top:8px; text-align:center;'>{' &nbsp;•&nbsp; '.join(_caps)}</div>", unsafe_allow_html=True)
                    except Exception:
                        pass
        with ch2:
            with st.container():
                st.markdown('<div class="farmer-card-anchor harvest" style="display:none;"></div>', unsafe_allow_html=True)
                st.markdown('<div class="farmer-card-title"><span style="width:32px; height:32px; background:#FFF8E1; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; border:1px solid #FFE082;"><i class="material-symbols-outlined" style="font-size:18px; color:#F9A825;">eco</i></span><span>Harvest Forecast vs Comparison (Gabay)</span></div>', unsafe_allow_html=True)
                # Forecast bars with benchmark overlay
                if not forecast_quarterly_yield:
                    st.info("No forecast data.")
                else:
                    _fc_vals = list(forecast_quarterly_yield)[:4]
                    _fc_labels = y_labels[:len(_fc_vals)] if y_labels else [f"Q{i+1}" for i in range(len(_fc_vals))]
                    # Bar chart amber gradient like LGU
                    _gold = ["#B45309","#D97706","#F59E0B","#FBBF24"]
                    _cols = [_gold[i % len(_gold)] for i in range(len(_fc_vals))]
                    fig_fc = go.Figure()
                    fig_fc.add_trace(go.Bar(x=_fc_labels, y=_fc_vals, name="Forecast", marker=dict(color=_cols, line=dict(width=0), cornerradius=8, opacity=0.95), text=[f"{v:.2f}" for v in _fc_vals], textposition="outside", textfont=dict(size=10, color="#78350F"), hovertemplate="<b>%{x}</b><br>Forecast: %{y:.2f} tons/ha<extra></extra>"))
                    if "Bataan 10-Year Average" in benchmarks and ten_yr_avg is not None and not pd.isna(ten_yr_avg):
                        try:
                            fig_fc.add_hline(y=float(ten_yr_avg), line_dash="dot", line_width=1.4, line_color="#78909C", annotation_text=f"10-Yr Avg {float(ten_yr_avg):.2f}", annotation_position="top left", annotation=dict(font=dict(size=9, color="#607D8B"), bgcolor="rgba(255,255,255,0.9)"))
                        except Exception:
                            pass
                    if "DA Target (4.5 tons/ha)" in benchmarks:
                        try:
                            fig_fc.add_hline(y=4.50, line_dash="dot", line_width=1.4, line_color="#2E7D32", annotation_text="DA Target 4.5", annotation_position="bottom left", annotation=dict(font=dict(size=9, color="#2E7D32"), bgcolor="rgba(232,245,233,0.95)"))
                        except Exception:
                            pass
                    # Peak annotation
                    try:
                        _pv = float(pd.Series(_fc_vals).max()); _pi = _fc_vals.index(_pv)
                        fig_fc.add_annotation(x=_fc_labels[_pi], y=_pv, text=f"▲ Peak {_pv:.2f}", showarrow=True, arrowhead=2, ax=0, ay=-28, font=dict(size=10, color="#C2410C"), bgcolor="rgba(255,255,255,0.92)", bordercolor="#F59E0B", borderwidth=1, borderpad=3)
                    except Exception:
                        pass
                    try:
                        import math
                        _mn = float(pd.Series(_fc_vals).min()); _mx = float(pd.Series(_fc_vals).max())
                        _lo = math.floor((_mn - 0.10)/0.05)*0.05; _hi = math.ceil((_mx + 0.12)/0.05)*0.05
                        if "DA Target (4.5 tons/ha)" in benchmarks:
                            _hi = max(_hi, 4.62)
                    except Exception:
                        _lo,_hi = None,None
                    fig_fc.update_layout(height=300, margin=dict(l=10,r=10,t=10,b=10), xaxis_title=None, yaxis_title="tons/ha", plot_bgcolor="white", paper_bgcolor="white", hovermode="closest", bargap=0.35, xaxis=dict(gridcolor="#F3F4F6", showgrid=False), yaxis=dict(gridcolor="#F3F4F6", showgrid=True, range=[_lo,_hi] if _lo is not None else None, dtick=0.05))
                    st.plotly_chart(fig_fc, use_container_width=True, config={"displayModeBar": False})
                    # Insight vs benchmark — plain language
                    try:
                        _fav = float(pd.Series(_fc_vals).mean())
                        _msgs = []
                        if "Bataan 10-Year Average" in benchmarks and ten_yr_avg is not None:
                            _d = _fav - float(ten_yr_avg)
                            _msgs.append(f"Forecast avg <b>{_fav:.2f} tons/ha</b> is <b style='color:{'#1B7A3D' if _d>=0 else '#C62828'};'>{_d:+.2f}</b> vs 10-yr avg ({float(ten_yr_avg):.2f})")
                        if "DA Target (4.5 tons/ha)" in benchmarks:
                            _d2 = _fav - 4.50
                            _msgs.append(f"Forecast avg <b>{_fav:.2f} tons/ha</b> is <b style='color:{'#1B7A3D' if _d2>=0 else '#C62828'};'>{_d2:+.2f}</b> vs DA target (4.5)")
                        if _msgs:
                            st.markdown(f"<div style='font-size:11px; color:#3A4D3D; background:#FFFEF8; border:1px solid #F2E8C8; border-radius:8px; padding:8px 10px; line-height:1.5;'>{'<br>'.join(_msgs)}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"<div style='font-size:11px; color:#6B7C6E; background:#FFFEF8; border:1px solid #F2E8C8; border-radius:8px; padding:8px 10px;'>Tip: Choose a comparison above to see how the forecast compares with the Bataan average or DA target (4.5 tons/ha).</div>", unsafe_allow_html=True)
                    except Exception:
                        pass
        st.markdown('<div style="background:#F6FBF6; border:1px solid #E8EFDE; border-radius:10px; padding:10px 12px; margin-top:10px; font-size:11px; color:#3A4D3D; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="font-size:16px; color:#2E7D32;">lightbulb</i> <div><b>How to use:</b> Use <b>Years to Show</b> to change the time range, <b>View</b> to switch between yearly, quarterly, or season, and <b>Compare With</b> to show guide lines. Dashed lines show if your <i>ani</i> (harvest) is above or below the Bataan average or DA target of 4.5 tons per hectare.</div></div>', unsafe_allow_html=True)
    elif section_choice == "Municipal Forecast":
        _render_hero()
        st.markdown('<div style="background:linear-gradient(90deg,#F6FBF6 0%, #FFFFFF 100%); border:1px solid #E8EFDE; border-radius:14px; padding:14px 16px; margin-bottom:12px; display:flex; align-items:center; gap:12px;"><i class="material-symbols-outlined" style="font-size:22px; color:#1B4332;">location_on</i><div><div style="font-weight:700; color:#1B4332; font-size:14px;">Prices per Town (Presyo per Bayan)</div><div style="font-size:12px; color:#6B7C6E;">Compare the palay price outlook for each town in Bataan — full view of all municipalities.</div></div></div>', unsafe_allow_html=True)
        _render_municipal_outlook()
        st.markdown('<div style="background:white; border:1px solid #E8EFDE; border-radius:16px; padding:12px; margin-top:12px;">', unsafe_allow_html=True)
        st.markdown('<div class="farmer-card-title"><i class="material-symbols-outlined" style="font-size:18px; color:#1B4332;">payments</i> Town Price Comparison — Next 3 Months (All Municipalities)</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px; color:#6B7C6E; margin-bottom:8px;">Choose your <i>binhi</i> (seed type) and palay moisture (<b>Dry = Tuyo</b> / <b>Wet = Basa</b>) to compare prices across <b>all 12 towns</b> in Bataan at once.</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3, gap="small")
        with c1:
            rt = st.radio("Binhi (Seed)", options=["Inbred", "Hybrid"], horizontal=True, key="muni_rt2")
        with c2:
            grade_raw = st.radio("Palay Type", options=["Regular","Premium"], horizontal=True, key="muni_grade2")
            cls = "Ordinary" if grade_raw=="Regular" else "Premium"
        with c3:
            cyc = st.radio("Moisture (Tuyo/Basa)", options=["Dry","Wet"], horizontal=True, key="muni_cyc2")
        sel_cycle = "Dry Palay" if cyc=="Dry" else "Wet Palay"
        # Full view: show all municipalities instead of one-by-one (isa-isa)
        selected_for_chart = all_munis
        _render_municipal_crop_cycle_chart(df_municipal_forecasts, rice_type=rt, classification=cls, selected_municipalities=selected_for_chart, selected_cycle=sel_cycle)
        st.markdown('</div>', unsafe_allow_html=True)
    elif section_choice == "Guide and Advice":
        _render_hero()
        st.markdown("""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:14px;">
            <div style="background:white; border:1px solid #E8EFDE; border-radius:16px; padding:14px;">
                <div style="font-weight:700; color:#1B4332; font-size:14px; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="color:#2E7D32;">help</i> What is a price forecast? (<i> ng Presyo</i>)</div>
                <div style="font-size:12px; color:#3A4D3D; line-height:1.6; margin-top:6px;">A price forecast (<i> ng presyo</i>) is our estimate of how much your palay may sell for in the coming months. It is based on past prices and market trends. Use it as a guide to plan when to sell for better income.</div>
            </div>
            <div style="background:white; border:1px solid #E8EFDE; border-radius:16px; padding:14px;">
                <div style="font-weight:700; color:#1B4332; font-size:14px; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="color:#F9A825;">eco</i> What is a harvest forecast? (<i> ng Ani</i>)</div>
                <div style="font-size:12px; color:#3A4D3D; line-height:1.6; margin-top:6px;">A harvest forecast (<i> ng ani</i>) estimates your yield in tons per hectare. Example: 4.02 tons/ha means about 4,020 kilos per hectare. It is based on past <i>ani</i> (harvest) and weather. Use it to plan your <i>abono</i> (fertilizer), labor, and drying needs.</div>
            </div>
            <div style="background:white; border:1px solid #E8EFDE; border-radius:16px; padding:14px;">
                <div style="font-weight:700; color:#1B4332; font-size:14px; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="color:#1565C0;">visibility</i> How do I read the forecast? (Gabay)</div>
                <div style="font-size:12px; color:#3A4D3D; line-height:1.6; margin-top:6px;">Check the current price or yield and the line on the chart. If the line goes up, prices or harvest are expected to rise. Always compare the forecast with your buyer offer, storage and drying costs, and your field condition before you decide.</div>
            </div>
            <div style="background:white; border:1px solid #E8EFDE; border-radius:16px; padding:14px;">
                <div style="font-weight:700; color:#1B4332; font-size:14px; display:flex; align-items:center; gap:8px;"><i class="material-symbols-outlined" style="color:#6B7C6E;">info</i> Why do actual prices vary?</div>
                <div style="font-size:12px; color:#3A4D3D; line-height:1.6; margin-top:6px;">Actual price from your buyer (farmgate price) depends on moisture, variety, <i>peste</i> (pest) damage, and your location. The forecast is for the whole province. Please confirm with your local buyer.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("""
        <div style="background:#F6FBF6; border:1px solid #E8EFDE; border-radius:12px; padding:12px; border-left:4px solid #2E7D32;">
            <div style="font-weight:700; color:#1B4332; font-size:13px;">Important Reminder from the Office of the Provincial Agriculturist — Bataan</div>
            <div style="font-size:12px; color:#3A4D3D; line-height:1.6; margin-top:4px;">PalaySense provides price and harvest forecasts as a guide for your decisions — it does not tell you to "SELL NOW" or "WAIT." Please compare this outlook with your buyer offer, storage and drying costs, and your actual field condition, including <i>abono</i> (fertilizer) and <i>peste</i> (pest) management, before you decide.</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; padding:12px 0 6px 0; font-size:11px; color:#A8B5A0; border-top:1px solid #E8EFDE; margin-top:18px;">PalaySense — Official palay price and harvest forecast service of the Province of Bataan • Forecasts are estimates only; actual results may vary</div>', unsafe_allow_html=True)
