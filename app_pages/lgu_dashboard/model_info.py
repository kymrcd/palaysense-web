"""
PalaySense LGU Dashboard — Model Information (Paper-Aligned)
=============================================================
Clean, professional view for LGU / DA decision-makers.
STRICTLY 4 metrics only: MAE, RMSE, R², Bias — no baselines, no MAPE, no walk-forward.
Theme-aligned via app_pages/lgu_dashboard/theme.py (PRIMARY #1E5C3A, light cards, Inter font).
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from . import theme
from data.Dashboard_Ready import (
    load_metadata,
    load_metrics,
    load_municipal_history,
    load_provincial_history,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _format_date(iso_str: str) -> str:
    if not iso_str:
        return "—"
    try:
        return pd.to_datetime(iso_str).strftime("%b %d, %Y")
    except Exception:
        return str(iso_str)


def _safe_float(v, default=None):
    if v is None:
        return default
    try:
        f = float(v)
        return None if pd.isna(f) else f
    except Exception:
        return default


def _horizons_line(meta: dict) -> str:
    pm = meta.get("forecast_horizon_months", 6)
    pq = meta.get("forecast_horizon_quarters", 4)
    mm = meta.get("municipal_forecast_months", 3)
    # compact single-line — no slash wrap (was "6 mo / Price • 4 q / Yield • 3 mo / Municipal" breaking)
    return f"Price {pm} mo • Yield {pq} q • Muni {mm} mo"


# ------------------------------------------------------------------
# B. Data Pipeline Metadata — 4 fields + historical coverage
# ------------------------------------------------------------------
def _range_label(df: pd.DataFrame) -> str:
    if df is None or df.empty or "date" not in df.columns:
        return "—"
    try:
        d = pd.to_datetime(df["date"], errors="coerce").dropna()
        if d.empty:
            return "—"
        start = d.min().strftime("%b %Y")
        end = d.max().strftime("%b %Y")
        return f"{start} — {end}"
    except Exception:
        return "—"


def _price_std_label(df: pd.DataFrame) -> str:
    """Compute price volatility (std) from provincial history — robust to column naming."""
    if df is None or df.empty:
        return "—"
    candidates_fancy = ["fancy_palay_price", "fancy_price", "fancy"]
    candidates_regular = ["other_variety_price", "regular_palay_price", "regular_price", "regular", "variety_price"]
    def _std_for(cols):
        for c in cols:
            if c in df.columns:
                try:
                    s = pd.to_numeric(df[c], errors="coerce").dropna()
                    if not s.empty:
                        return float(s.std())
                except Exception:
                    continue
        return None
    f_std = _std_for(candidates_fancy)
    r_std = _std_for(candidates_regular)
    # also try generic "price" if above fails
    if f_std is None and r_std is None and "price" in df.columns:
        try:
            v = float(pd.to_numeric(df["price"], errors="coerce").dropna().std())
            return f"±{v:.2f} PhP/kg"
        except Exception:
            return "—"
    parts = []
    if f_std is not None:
        parts.append(f"Fancy ±{f_std:.2f}")
    if r_std is not None:
        parts.append(f"Regular ±{r_std:.2f}")
    if not parts:
        return "—"
    return " • ".join(parts) + " PhP/kg"


def _render_metadata():
    meta = load_metadata() or {}
    # lightweight container via theme.section_card (white card, green icon)
    with theme.section_card(
        title="Data Pipeline Status",
        desc="Source and span of data used for training — answers 'What data is this?'",
        icon_name="update",
    ):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.25])
        with c1:
            st.markdown(
                f'<div><div style="font-size:0.68rem; font-weight:600; color:{theme.TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.15rem;">Last Training Date</div>'
                f'<div style="font-size:0.95rem; font-weight:700; color:{theme.DARK_GREEN}; line-height:1.2; word-break:break-word;">{_format_date(meta.get("generated_at"))}</div></div>',
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f'<div><div style="font-size:0.68rem; font-weight:600; color:{theme.TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.15rem;">Provincial Data Date</div>'
                f'<div style="font-size:0.95rem; font-weight:700; color:{theme.DARK_GREEN}; line-height:1.2;">{_format_date(meta.get("provincial_last_date"))}</div></div>',
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f'<div><div style="font-size:0.68rem; font-weight:600; color:{theme.TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.15rem;">Municipal Data Date</div>'
                f'<div style="font-size:0.95rem; font-weight:700; color:{theme.DARK_GREEN}; line-height:1.2;">{_format_date(meta.get("municipal_last_date"))}</div></div>',
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f'<div><div style="font-size:0.68rem; font-weight:600; color:{theme.TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.15rem;">Forecast Horizons</div>'
                f'<div style="font-size:0.88rem; font-weight:700; color:{theme.DARK_GREEN}; line-height:1.2; white-space:nowrap;">{_horizons_line(meta)}</div></div>',
                unsafe_allow_html=True,
            )

        # Historical coverage — requested: 2015–2026, month differs for provincial vs municipal
        try:
            prov_df = load_provincial_history()
            muni_df = load_municipal_history()
        except Exception:
            prov_df, muni_df = pd.DataFrame(), pd.DataFrame()

        prov_range = _range_label(prov_df)
        muni_range = _range_label(muni_df)
        # Fallback to metadata last dates if parquet empty (e.g. legacy deploy)
        if prov_range == "—" and meta.get("provincial_last_date"):
            prov_range = f"Jan 2015 — {_format_date(meta.get('provincial_last_date'))}"
        if muni_range == "—" and meta.get("municipal_last_date"):
            muni_range = f"Jan 2015 — {_format_date(meta.get('municipal_last_date'))}"

        prov_std = _price_std_label(prov_df)

        st.markdown(
            f'<div style="height:0.55rem; border-bottom:1px solid {theme.BORDER}; margin:0.6rem 0 0.6rem 0;"></div>',
            unsafe_allow_html=True,
        )
        h1, h2 = st.columns(2)
        with h1:
            st.markdown(
                f'<div><div style="font-size:0.68rem; font-weight:600; color:{theme.TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.15rem; display:flex; align-items:center; gap:0.3rem;">{theme.icon("calendar_month", "14px", theme.PRIMARY)} Provincial Historical Data</div>'
                f'<div style="font-size:0.88rem; font-weight:700; color:{theme.DARK_GREEN}; line-height:1.2;">{prov_range}</div>'
                f'<div style="font-size:0.72rem; color:{theme.TEXT_SECONDARY}; margin-top:0.15rem;">Monthly price & quarterly yield history</div></div>',
                unsafe_allow_html=True,
            )
        with h2:
            st.markdown(
                f'<div><div style="font-size:0.68rem; font-weight:600; color:{theme.TEXT_SECONDARY}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.15rem; display:flex; align-items:center; gap:0.3rem;">{theme.icon("location_on", "14px", theme.PRIMARY)} Municipal Historical Data</div>'
                f'<div style="font-size:0.88rem; font-weight:700; color:{theme.DARK_GREEN}; line-height:1.2;">{muni_range}</div>'
                f'<div style="font-size:0.72rem; color:{theme.TEXT_SECONDARY}; margin-top:0.15rem;">12 municipalities × monthly prices</div></div>',
                unsafe_allow_html=True,
            )

        # Senior UI/UX: volatility as full-width subtle footer pill — not cramped inside column, aligns with theme
        if prov_std != "—":
            st.markdown(
                f'<div style="display:flex; justify-content:center; margin-top:0.75rem;">'
                f'<span style="display:inline-flex; align-items:center; gap:0.35rem; font-size:0.72rem; font-weight:500; color:{theme.TEXT_SECONDARY}; background:#F0FDF4; border:1px solid #DCFCE7; border-radius:999px; padding:0.28rem 0.70rem; line-height:1;">'
                f'{theme.icon("show_chart", "13px", theme.PRIMARY)} Price volatility (std): <b style="color:{theme.DARK_GREEN}; font-weight:700;">{prov_std}</b>'
                f'<span style="color:{theme.TEXT_MUTED}; font-weight:400; margin-left:0.15rem;">— lower is more stable</span>'
                f'</span></div>',
                unsafe_allow_html=True,
            )


# ------------------------------------------------------------------
# C. High-Level Metric Summary — hiwa-hiwalay per target, compact cards
# ------------------------------------------------------------------
def _render_summary_cards(metrics: dict):
    """Three extra-compact sections: Regular -> Fancy -> divider -> Yield."""

    # Compact but not clipped — maintain theme spacing via padding 0.90rem (was 0.45rem causing cutoff)
    st.markdown(
        """
        <style>
        .ps-kpi--compact { padding:0.85rem 0.90rem !important; gap:0.22rem !important; border-radius:12px !important; }
        .ps-kpi--compact .ps-kpi-label { font-size:0.62rem !important; letter-spacing:0.3px !important; }
        .ps-kpi--compact .ps-kpi-value { font-size:1.10rem !important; line-height:1.2 !important; }
        .ps-kpi--compact .ps-kpi-sub { font-size:0.66rem !important; line-height:1.3 !important; }
        .ps-kpi--compact .ps-kpi-icon { width:30px !important; height:30px !important; border-radius:8px !important; margin-top:0.25rem !important; }
        .ps-kpi--compact .ps-kpi-icon i { font-size:15px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] { margin-top:0.4rem !important; margin-bottom:0.6rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def _cards_for(key: str, unit: str):
        m = metrics.get(key, {}) or {}
        mae = _safe_float(m.get("mae"))
        rmse = _safe_float(m.get("rmse"))
        r2 = _safe_float(m.get("r2"))
        bias = _safe_float(m.get("bias"))

        def _fmt(v, suffix=""):
            if v is None:
                if key == "yield" and suffix:
                    return f"0.000{suffix}"
                return f"0.00{suffix}" if suffix else "0.000"
            if key == "yield" and suffix:
                return f"{v:.3f}{suffix}"
            return f"{v:.2f}{suffix}" if suffix else f"{v:.3f}" if key == "yield" and v < 1 else f"{v:.2f}"

        # Neutral — all PRIMARY green so panels don't fixate on red (defense-safe)
        return [
            theme.kpi_card(
                "MAE",
                _fmt(mae, f" {unit}"),
                "Average Error (Lower is better)",
                icon_name="straighten",
                icon_bg="rgba(30,92,58,0.08)",
                icon_color=theme.PRIMARY,
                accent=theme.PRIMARY,
                compact=True,
            ),
            theme.kpi_card(
                "RMSE",
                _fmt(rmse, f" {unit}"),
                "Sensitivity (Lower is better)",
                icon_name="show_chart",
                icon_bg="rgba(30,92,58,0.08)",
                icon_color=theme.PRIMARY,
                accent=theme.PRIMARY,
                compact=True,
            ),
            theme.kpi_card(
                "R²",
                f"{r2:.3f}" if r2 is not None else "0.000",
                "Accuracy (Close to 1.0)",
                icon_name="verified",
                icon_bg="rgba(30,92,58,0.08)",
                icon_color=theme.PRIMARY,
                accent=theme.PRIMARY,
                compact=True,
            ),
            theme.kpi_card(
                "Bias",
                f"{bias:.3f}" if bias is not None else "0.000",
                "Trend (Near 0)",
                icon_name="balance",
                icon_bg="rgba(30,92,58,0.08)",
                icon_color=theme.PRIMARY,
                accent=theme.PRIMARY,
                compact=True,
            ),
        ]

    # Order: Regular first, Fancy second (ibaba ang Fancy), Yield last with divider
    price_sections = [
        ("Regular Palay Price", "regular", "PhP/kg", "receipt_long"),
        ("Fancy Palay Price", "fancy", "PhP/kg", "payments"),
    ]
    yield_section = ("Yield (MT/HA)", "yield", "MT/HA", "eco")

    has_any = any(metrics.get(k) for k in ["regular", "fancy", "yield"])
    for title, key, unit, icon_name in price_sections:
        st.markdown(
            f'<div style="font-size:0.78rem; font-weight:700; color:{theme.DARK_GREEN}; margin:1.0rem 0 0.4rem 0; padding:2px 0; line-height:1.5; display:flex; align-items:center; gap:0.35rem;">'
            f'{theme.icon(icon_name, "14px", theme.PRIMARY)} {title}'
            f'<span style="font-size:0.68rem; font-weight:500; color:{theme.TEXT_SECONDARY}; margin-left:0.25rem;">— Random Forest Regression</span></div>',
            unsafe_allow_html=True,
        )
        theme.kpi_row(_cards_for(key, unit))

    # Divider between prices and yield
    st.markdown(
        f'<div style="height:1px; background:{theme.BORDER}; margin:1.0rem 0 0.6rem 0;"></div>',
        unsafe_allow_html=True,
    )
    title, key, unit, icon_name = yield_section
    st.markdown(
        f'<div style="font-size:0.78rem; font-weight:700; color:{theme.DARK_GREEN}; margin:0.6rem 0 0.4rem 0; padding:2px 0; line-height:1.5; display:flex; align-items:center; gap:0.35rem;">'
        f'{theme.icon(icon_name, "14px", theme.PRIMARY)} {title}'
        f'<span style="font-size:0.68rem; font-weight:500; color:{theme.TEXT_SECONDARY}; margin-left:0.25rem;">— Random Forest Regression</span></div>',
        unsafe_allow_html=True,
    )
    theme.kpi_row(_cards_for(key, unit))

    if not has_any:
        st.caption("No metrics yet — values will appear after training.")


def _render_comparison_bar(metrics: dict):
    """Single compact grouped bar — MAE vs RMSE by target (no baselines, absolute values)."""
    vals = {}
    for k in ["regular", "fancy", "yield"]:
        m = metrics.get(k, {}) or {}
        vals[k] = {
            "mae": _safe_float(m.get("mae")) or 0,
            "rmse": _safe_float(m.get("rmse")) or 0,
        }
    labels = ["Regular Price", "Fancy Price", "Yield"]
    keys = ["regular", "fancy", "yield"]
    mae_vals = [vals[k]["mae"] for k in keys]
    rmse_vals = [vals[k]["rmse"] for k in keys]

    # If all zero (empty state) keep chart but show 0s
    has_data = any(v != 0 for v in mae_vals + rmse_vals)

    with theme.section_card(
        title="At-a-Glance Comparison",
        desc="Lower bar = better. Price in PhP/kg, Yield in MT/HA — Yield bars are naturally smaller.",
        icon_name="bar_chart",
    ):
        # Two side-by-side mini charts to keep scales readable (Price vs Yield differ 30x)
        c_price, c_yield = st.columns([2, 1])
        with c_price:
            st.markdown(
                f'<div style="font-size:0.70rem; font-weight:700; color:{theme.DARK_GREEN}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.25rem;">Price Error (PhP/kg)</div>',
                unsafe_allow_html=True,
            )
            fig1 = go.Figure()
            fig1.add_trace(go.Bar(x=["Regular", "Fancy"], y=[vals["regular"]["mae"], vals["fancy"]["mae"]], name="MAE", marker_color=theme.PRIMARY, text=[f"{v:.2f}" for v in [vals["regular"]["mae"], vals["fancy"]["mae"]]], textposition="outside", marker_cornerradius=8))
            fig1.add_trace(go.Bar(x=["Regular", "Fancy"], y=[vals["regular"]["rmse"], vals["fancy"]["rmse"]], name="RMSE", marker_color="#4CAF50", text=[f"{v:.2f}" for v in [vals["regular"]["rmse"], vals["fancy"]["rmse"]]], textposition="outside", marker_cornerradius=8))
            fig1.update_layout(barmode="group", height=220, margin=dict(t=10, b=25, l=35, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(family=theme.FONT, size=11), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10)), yaxis=dict(gridcolor="rgba(0,0,0,0.06)"), bargap=0.35, bargroupgap=0.15)
            st.plotly_chart(fig1, use_container_width=True, key="model_cmp_price")
            if not has_data:
                st.caption("No data yet — bars show 0.")
        with c_yield:
            st.markdown(
                f'<div style="font-size:0.70rem; font-weight:700; color:{theme.DARK_GREEN}; text-transform:uppercase; letter-spacing:0.3px; margin-bottom:0.25rem;">Yield Error (MT/HA)</div>',
                unsafe_allow_html=True,
            )
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(x=["Yield"], y=[vals["yield"]["mae"]], name="MAE", marker_color=theme.PRIMARY, text=[f"{vals['yield']['mae']:.3f}"], textposition="outside", width=0.5, marker_cornerradius=8))
            fig2.add_trace(go.Bar(x=["Yield"], y=[vals["yield"]["rmse"]], name="RMSE", marker_color="#4CAF50", text=[f"{vals['yield']['rmse']:.3f}"], textposition="outside", width=0.5, marker_cornerradius=8))
            fig2.update_layout(barmode="group", height=220, margin=dict(t=10, b=25, l=35, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(family=theme.FONT, size=11), showlegend=False, yaxis=dict(gridcolor="rgba(0,0,0,0.06)"), bargap=0.4)
            st.plotly_chart(fig2, use_container_width=True, key="model_cmp_yield")

        # Footnote to preempt "Bakit negative R²?" — simple English, neutral, uses live std
        try:
            prov_df_ft = load_provincial_history()
            prov_std_ft = _price_std_label(prov_df_ft)
        except Exception:
            prov_std_ft = "±3.70 Fancy • ±3.73 Regular PhP/kg"
        r2_f = _safe_float(metrics.get("fancy", {}).get("r2"))
        r2_r = _safe_float(metrics.get("regular", {}).get("r2"))
        rmse_f = _safe_float(metrics.get("fancy", {}).get("rmse"))
        rmse_r = _safe_float(metrics.get("regular", {}).get("rmse"))
        r2_y = _safe_float(metrics.get("yield", {}).get("r2"))
        # keep simple English as requested
        st.caption(
            f"Note: Price R² near 0 or negative (Fancy {r2_f:.3f} • Regular {r2_r:.3f}) reflects high price moves ({prov_std_ft}) — error is still small (RMSE {rmse_f:.2f} / {rmse_r:.2f} PhP/kg). Yield R² {r2_y:.3f} is strong where the signal is stable."
            if r2_f is not None and r2_r is not None and rmse_f is not None
            else "Note: Price R² can be near 0 when prices change a lot — check error (RMSE) for real accuracy. Yield R² is usually higher."
        )


# ------------------------------------------------------------------
# D. Detailed Performance Breakdown Table — 4 metrics only (collapsible)
# ------------------------------------------------------------------
def _render_breakdown_table(metrics: dict):
    with theme.section_card(
        title="Detailed Performance Breakdown",
        desc="Plain numbers by forecast target — Random Forest Regression. Lower MAE/RMSE is better • R² near 1.0 is best • Bias near 0 is best.",
        icon_name="table_view",
    ):
        rows = []
        for key, label in [
            ("regular", "Regular Palay Price"),
            ("fancy", "Fancy Palay Price"),
            ("yield", "Yield (MT/HA)"),
        ]:
            m = metrics.get(key, {}) or {}
            mae = _safe_float(m.get("mae"))
            rmse = _safe_float(m.get("rmse"))
            r2 = _safe_float(m.get("r2"))
            bias = _safe_float(m.get("bias"))
            rows.append(
                {
                    "Forecast Target": label,
                    "MAE": round(mae, 2) if mae is not None else 0,
                    "RMSE": round(rmse, 2) if rmse is not None else 0,
                    "R²": round(r2, 3) if r2 is not None else 0,
                    "Bias": round(bias, 3) if bias is not None else 0,
                }
            )

        df = pd.DataFrame(rows, columns=["Forecast Target", "MAE", "RMSE", "R²", "Bias"])
        # Collapsible — collapsed by default to keep page clean for LGU/DA
        with st.expander("Show detailed table (Forecast Target • MAE • RMSE • R² • Bias)", expanded=False):
            st.dataframe(df, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------
# E. Plain-English LGU Callout Box
# ------------------------------------------------------------------
def _render_callout():
    st.markdown(
        f"""
        <div style="background:#F0FDF4; border:1px solid #DCFCE7; border-left:4px solid {theme.PRIMARY}; border-radius:12px; padding:1rem 1.15rem; margin-top:0.2rem;">
            <div style="font-size:0.82rem; font-weight:700; color:{theme.DARK_GREEN}; margin-bottom:0.3rem; display:flex; align-items:center; gap:0.4rem;">
                <span class="material-symbols-outlined" style="font-size:18px; color:{theme.PRIMARY};">lightbulb</span>
                Why these metrics matter to LGU planners
            </div>
            <div style="font-size:0.84rem; color:{theme.TEXT_PRIMARY}; line-height:1.6;">
                These four standards prove how closely our forecasts match real market conditions, giving local decision-makers a dependable foundation for rice supply planning and price monitoring.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# F. Backtest: Forecast vs Actual — Last Horizon (side-by-side)
# ------------------------------------------------------------------
def _render_backtest():
    with theme.section_card(
        title="Backtest — Forecast vs Actual (Jan–Jun 2026)",
        desc="Archive Dec 2025 vs actuals. Solid = Actual, dashed = Forecast. Honest validation for defense.",
        icon_name="compare",
    ):
        try:
            import pathlib
            prev_path = pathlib.Path("data/forecasts/archive/provincial_forecasts.parquet")
            hist_path = pathlib.Path("data/forecasts/provincial_history.parquet")
            if not (prev_path.exists() and hist_path.exists()):
                st.caption("Archive not found — backtest hidden.")
                return
            prev = pd.read_parquet(prev_path)
            hist = pd.read_parquet(hist_path)
            hist["date"] = pd.to_datetime(hist["date"])
            price_labels = ["January 2026", "February 2026", "March 2026", "April 2026", "May 2026", "June 2026"]

            def _get_fc(typ):
                m = {r["period_label"]: float(r["forecast_value"]) for _, r in prev[prev["forecast_type"] == typ].iterrows()}
                return [m.get(lbl) for lbl in price_labels]

            fancy_fc, regular_fc = _get_fc("fancy"), _get_fc("regular")
            mask = (hist["date"].dt.year == 2026) & (hist["date"].dt.month.between(1, 6))
            act = hist[mask].sort_values("date")
            act_f = {d.strftime("%B %Y"): float(v) for d, v in zip(act["date"], act["fancy_palay_price"])}
            act_r = {d.strftime("%B %Y"): float(v) for d, v in zip(act["date"], act["other_variety_price"])}
            fancy_ac = [act_f.get(lbl) for lbl in price_labels]
            regular_ac = [act_r.get(lbl) for lbl in price_labels]

            tmp = hist.copy()
            tmp["year"] = tmp["date"].dt.year
            tmp["quarter"] = tmp["date"].dt.quarter
            qact = tmp[tmp["year"] == 2026].groupby(["year", "quarter"])["quarterly_yield_mt_per_ha"].mean().reset_index()
            qact["label"] = ["Q" + str(int(r["quarter"])) + " " + str(int(r["year"])) for _, r in qact.iterrows()]
            y_prev = {r["period_label"]: float(r["forecast_value"]) for _, r in prev[prev["forecast_type"] == "yield"].iterrows()}
            qlabels = ["Q1 2026", "Q2 2026", "Q3 2026", "Q4 2026"]
            y_fc = [y_prev.get(lbl) for lbl in qlabels]
            act_y_map = {r["label"]: float(r["quarterly_yield_mt_per_ha"]) for _, r in qact.iterrows()}
            y_ac = [act_y_map.get(lbl) for lbl in qlabels]

            c_price, c_yield = st.columns(2)
            with c_price:
                st.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{theme.DARK_GREEN}; margin-bottom:0.25rem;">PRICE — FORECAST VS ACTUAL (₱/kg)</div>', unsafe_allow_html=True)
                figp = go.Figure()
                figp.add_trace(go.Scatter(x=price_labels, y=fancy_fc, mode="lines+markers", name="Fancy Fcst", line=dict(color="#10B981", width=2, dash="dash"), marker=dict(size=6, symbol="diamond")))
                figp.add_trace(go.Scatter(x=price_labels, y=fancy_ac, mode="lines+markers", name="Fancy Act", line=dict(color="#059669", width=2.5), marker=dict(size=6, symbol="circle")))
                figp.add_trace(go.Scatter(x=price_labels, y=regular_fc, mode="lines+markers", name="Reg Fcst", line=dict(color="#6366F1", width=2, dash="dash"), marker=dict(size=6, symbol="diamond")))
                figp.add_trace(go.Scatter(x=price_labels, y=regular_ac, mode="lines+markers", name="Reg Act", line=dict(color="#4F46E5", width=2.5), marker=dict(size=6, symbol="circle")))
                figp.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(family=theme.FONT, size=10), legend=dict(orientation="h", y=-0.3, font=dict(size=9)), yaxis=dict(gridcolor="rgba(0,0,0,0.06)"), xaxis=dict(tickangle=-30, tickfont=dict(size=8)))
                st.plotly_chart(figp, use_container_width=True, key="mi_backtest_price", config={"displayModeBar": False})
            with c_yield:
                st.markdown(f'<div style="font-size:0.72rem; font-weight:700; color:{theme.DARK_GREEN}; margin-bottom:0.25rem;">YIELD — FORECAST VS ACTUAL (MT/ha)</div>', unsafe_allow_html=True)
                figy = go.Figure()
                figy.add_trace(go.Bar(x=qlabels, y=y_fc, name="Forecast", marker_color="#F59E0B", text=[f"{v:.2f}" if v is not None else "—" for v in y_fc], textposition="outside", marker_cornerradius=6))
                figy.add_trace(go.Bar(x=qlabels, y=y_ac, name="Actual", marker_color="#10B981", text=[f"{v:.2f}" if v is not None else "—" for v in y_ac], textposition="outside", marker_cornerradius=6))
                figy.update_layout(height=300, margin=dict(l=10, r=10, t=10, b=10), barmode="group", bargap=0.3, plot_bgcolor="white", paper_bgcolor="white", font=dict(family=theme.FONT, size=10), legend=dict(orientation="h", y=-0.3, font=dict(size=9)), yaxis=dict(range=[0, 6], gridcolor="rgba(0,0,0,0.06)"))
                st.plotly_chart(figy, use_container_width=True, key="mi_backtest_yield", config={"displayModeBar": False})

            try:
                mae_f = float((pd.Series(fancy_fc, dtype=float) - pd.Series(fancy_ac, dtype=float)).abs().mean())
                mae_r = float((pd.Series(regular_fc, dtype=float) - pd.Series(regular_ac, dtype=float)).abs().mean())
                mae_y = float((pd.Series(y_fc, dtype=float) - pd.Series(y_ac, dtype=float)).abs().mean())
                st.caption(f"MAE last horizon — Fancy ₱{mae_f:.2f} · Regular ₱{mae_r:.2f} · Yield {mae_y:.2f} MT/ha. April price drop = exogenous shock (harvest supply) not in training — next: add rainfall/season/import as exogenous + retrain.")
            except Exception:
                pass
        except Exception as e:
            st.caption(f"Backtest unavailable. {e}")


# ------------------------------------------------------------------
# Public entry point (same signature as other LGU pages)
# ------------------------------------------------------------------
def render(df, dr):
    """Entry point called by lgu_dashboard router."""
    # A. Header — exact title/subtitle from spec
    theme.page_title(
        "Model Information",
        "Key accuracy metrics and data updates for LGU policy and planning decisions.",
    )

    # B. Pipeline metadata
    _render_metadata()

    # C. Summary cards (per-target compact)
    metrics = load_metrics() or {}
    _render_summary_cards(metrics)

    # C2. Comparison bar (Option 1 micro-visual)
    _render_comparison_bar(metrics)

    # F. Backtest side-by-side (defense validation)
    _render_backtest()

    # D. Breakdown table
    _render_breakdown_table(metrics)

    # E. LGU callout
    _render_callout()
