import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.Dashboard_Ready import load_provincial_history

#Design
PRIMARY = "#1E5C3A"
PRIMARY_LIGHT = "#2E7D32"
DARK = "#123524"
BORDER = "#E6EAE6"
BG_CARD = "#FFFFFF"
TEXT = "#1F2937"
MUTED = "#6B7280"
AMBER = "#D97706"
AMBER_BG = "#FFFBEB"
AMBER_BORDER = "#FDE68A"


def _inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');
        .material-symbols-outlined { font-family:'Material Symbols Outlined' !important; }
        /* Sakto lang — gaya sa filter bar sa pic: compact, no dead space */
        .ps-dsp-card { background:#fff; border:1px solid #E5E7EB; border-radius:10px; padding:0.65rem 0.85rem 0.60rem 0.85rem; box-shadow:0 1px 2px rgba(0,0,0,0.04); margin:0 0 0.50rem 0; overflow:visible; }
        .ps-dsp-kpi { background:#fff; border:1px solid #E5E7EB; border-radius:8px; padding:0.60rem 0.65rem; text-align:center; box-shadow:0 1px 2px rgba(0,0,0,0.04); overflow:visible; }
        .ps-dsp-kpi-val { font-size:1.15rem; font-weight:800; color:#123524; line-height:1.15; letter-spacing:-0.3px; }
        .ps-dsp-kpi-label { font-size:10px !important; font-weight:700 !important; color:#1B5E20 !important; text-transform:uppercase !important; letter-spacing:0.4px !important; line-height:1.3 !important; margin-bottom:2px !important; white-space:nowrap; overflow:visible; }
        /* Compact (Overview, no-scroll): denser grid — gaya sa pic, sakto lang spacing */
        .ps-dsp-compact .ps-dsp-kpi { padding:0.50rem 0.60rem; border-radius:8px; }
        .ps-dsp-compact .ps-dsp-kpi-val { font-size:1.05rem; }
        .ps-dsp-compact .ps-dsp-kpi-label { font-size:9px !important; letter-spacing:0.3px !important; line-height:1.3 !important; }
        .ps-dsp-compact .ps-dsp-kpi-sub { font-size:0.62rem !important; line-height:1.3 !important; }
        .ps-dsp-grid { display:grid; grid-template-columns:1fr 1fr; gap:0.60rem; margin:0; overflow:visible; }
        /* Tighten Streamlit vertical rhythm for DSP — gaya sa filter bar */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-dsp-card),
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-dsp-compact) {
            padding:0 !important; margin:0 0 0.50rem 0 !important; overflow:visible !important;
            background:#FFFFFF !important; border:1px solid #E5E7EB !important; border-radius:10px !important; box-shadow:0 1px 2px rgba(0,0,0,0.04) !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-dsp-card) > div,
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-dsp-compact) > div { padding:0.65rem 0.85rem 0.60rem 0.85rem !important; gap:0 !important; overflow:visible !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-dsp-card) div[data-testid="stHorizontalBlock"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.ps-dsp-compact) div[data-testid="stHorizontalBlock"] { gap:0.60rem !important; align-items:end !important; overflow:visible !important; }
        section[data-testid="stMain"] div[data-testid="stVerticalBlock"]:has(.ps-dsp-card),
        section[data-testid="stMain"] div[data-testid="stVerticalBlock"]:has(.ps-dsp-compact) { gap:0.30rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_decision_support_panel(
    supply_shortfall: float = -9.6,
    price_outlook: float = -3.6,
    avg_yield: float = 4.07,
    low_yield: float = 4.04,
    price_month: str = "Sep 2026",
    yield_period: str = "Next 4 quarters",
    compact: bool = False,
):
    """
    Executive Decision Support Panel for Bataan.
    All numbers are real-time forecasted inputs — defaults match your current
    Yield Summary (4.07 avg vs 4.50 DA target = -9.6% shortfall, low 4.04).
    price_month: e.g. "Sep 2026" for price outlook
    yield_period: e.g. "Q4 2026 – Q3 2027" for yield horizon
    When clean state (no dataset), pass 0 for all numbers — panel auto-shows
    "No reading" instead of interpretations.
    compact=True: dense no-scroll variant for Overview — pure HTML 2x2 grid,
    no Streamlit columns/popover buttons, details behind "View Full Insights".
    """
    _inject_css()
    is_clean = (avg_yield == 0 and low_yield == 0 and supply_shortfall == 0 and price_outlook == 0)

    # Municipal price spread — computed from existing municipal forecast output
    # (in-scope: same model output, disaggregated per bayan; no new operation).
    _muni_line = ""
    _muni_count = 0
    try:
        from data.Dashboard_Ready import load_municipal_forward_forecasts
        _mdf = load_municipal_forward_forecasts()
        if _mdf is not None and not getattr(_mdf, "empty", True) and "Municipality" in _mdf.columns:
            _price_cols = [c for c in ("Month 1", "Month 2", "Month 3") if c in _mdf.columns]
            if _price_cols:
                _tmp = _mdf.copy()
                for _c in _price_cols:
                    _tmp[_c] = pd.to_numeric(_tmp[_c], errors="coerce")
                _tmp["_muni_avg"] = _tmp[_price_cols].mean(axis=1, skipna=True)
                _per_muni = _tmp.groupby("Municipality")["_muni_avg"].mean().dropna()
                if not _per_muni.empty:
                    _muni_count = int(_per_muni.shape[0])
                    _hi_m = _per_muni.idxmax(); _hi_v = float(_per_muni.max())
                    _lo_m = _per_muni.idxmin(); _lo_v = float(_per_muni.min())
                    _spread = _hi_v - _lo_v
                    _muni_line = (
                        f"Across {_muni_count} municipalities: "
                        f"highest {str(_hi_m).title()} (₱{_hi_v:.2f}/kg), "
                        f"lowest {str(_lo_m).title()} (₱{_lo_v:.2f}/kg), "
                        f"spread ₱{_spread:.2f}/kg."
                    )
    except Exception:
        _muni_line = ""

    # Magnitude words — still pure forecast description, no prescription.
    try:
        _gap_mag = abs(float(supply_shortfall))
        _gap_word = "narrow" if _gap_mag < 5 else ("moderate" if _gap_mag < 10 else "wide")
    except Exception:
        _gap_word = "moderate"
    try:
        _p_mag = abs(float(price_outlook))
        _p_word = "mild" if _p_mag < 3 else ("moderate" if _p_mag < 5 else "sharp")
    except Exception:
        _p_word = "mild"

    # ---- Compact no-scroll variant (Overview): single HTML block, no columns/popovers ----
    if compact:
        _sup_col = PRIMARY if (supply_shortfall >= 0 and not is_clean) else AMBER
        _pr_col = PRIMARY if (price_outlook >= -1 and not is_clean) else AMBER
        _dir1 = "above" if supply_shortfall >= 0 else "below"
        _pdir = "increase" if price_outlook >= 0 else "decrease"
        st.markdown(
            f"""
            <div class="ps-dsp-compact" style="background:#fff; border:1px solid {BORDER}; border-radius:10px; padding:0.65rem 0.85rem 0.60rem 0.85rem; box-shadow:0 1px 2px rgba(0,0,0,0.04); overflow:visible;">
                <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.35rem;">
                    <span style="display:inline-flex; align-items:center; justify-content:center; width:26px; height:26px; background:{PRIMARY}; color:#fff; border-radius:7px; flex-shrink:0;">
                        <i class="material-symbols-outlined" style="font-size:15px; line-height:1;">agriculture</i>
                    </span>
                    <div style="min-width:0;">
                        <div style="font-size:0.85rem; font-weight:800; color:{DARK}; letter-spacing:-0.2px; line-height:1.15;">Decision Support Panel</div>
                        <div style="font-size:0.66rem; color:{MUTED}; font-weight:500; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Bataan • Price: {price_month if not is_clean else "No data"} • Yield: {yield_period if not is_clean else "No data"}</div>
                    </div>
                </div>
                <div class="ps-dsp-grid">
                    <div class="ps-dsp-kpi" style="border-top:2px solid {_sup_col}">
                        <div class="ps-dsp-kpi-label">Production vs Target</div>
                        <div class="ps-dsp-kpi-val" style="color:{_sup_col}">{supply_shortfall:+.1f}%</div>
                        <div class="ps-dsp-kpi-sub" style="font-size:0.66rem; color:{MUTED};">{abs(supply_shortfall):.1f}% {_dir1} DA target</div>
                    </div>
                    <div class="ps-dsp-kpi" style="border-top:2px solid {_pr_col}">
                        <div class="ps-dsp-kpi-label">Farmgate Price • {price_month if not is_clean else "—"}</div>
                        <div class="ps-dsp-kpi-val" style="color:{_pr_col}">{price_outlook:+.1f}%</div>
                        <div class="ps-dsp-kpi-sub" style="font-size:0.66rem; color:{MUTED};">Projected to {_pdir} {abs(price_outlook):.1f}%</div>
                    </div>
                    <div class="ps-dsp-kpi" style="border-top:2px solid {PRIMARY}">
                        <div class="ps-dsp-kpi-label">Expected Avg Harvest</div>
                        <div class="ps-dsp-kpi-val">{avg_yield:.2f} <span style="font-size:0.65rem; font-weight:700; color:{MUTED};">MT/ha</span></div>
                        <div class="ps-dsp-kpi-sub" style="font-size:0.66rem; color:{MUTED};">Avg over {yield_period if not is_clean else "next 4Q"}</div>
                    </div>
                    <div class="ps-dsp-kpi" style="border-top:2px solid #6B7280">
                        <div class="ps-dsp-kpi-label">Worst-Case Estimate</div>
                        <div class="ps-dsp-kpi-val">{low_yield:.2f} <span style="font-size:0.65rem; font-weight:700; color:{MUTED};">MT/ha</span></div>
                        <div class="ps-dsp-kpi-sub" style="font-size:0.66rem; color:{MUTED};">Lowest quarter in period</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.expander("View Full Insights", expanded=bool(st.session_state.get("dsp_view_full_insights", False))):
            if is_clean:
                st.info("No reading — no dataset. Upload historical price & yield data via Import Data.", icon="ℹ️")
            else:
                _pw = "decrease" if price_outlook < 0 else "increase"
                if is_clean:
                    pass
                elif (supply_shortfall >= 0) and (price_outlook >= -1):
                    st.success(f"**On Track:** Harvest **{supply_shortfall:+.1f}% vs DA target** (avg **{avg_yield:.2f}**, low **{low_yield:.2f} MT/ha**); farmgate **{price_outlook:+.1f}%** in {price_month}. Supply sufficient — routine monitoring.", icon="✅")
                else:
                    st.warning(f"**Early warning ({yield_period} / {price_month}):** harvest **{abs(supply_shortfall):.1f}% below** DA target (avg **{avg_yield:.2f}**, low **{low_yield:.2f} MT/ha**); farmgate to **{_pw} by {abs(price_outlook):.1f}%**. Validate volume vs harvested area before planning.", icon="⚠️")
                if _muni_line:
                    st.caption(_muni_line)
        st.caption("⚠️ *Forecast interpretation vs DA 4.50 MT/ha & historical avg — Bataan. Not an operations directive.*")
        return

    # Header — executive — KPIs first, View Full Insights toggle (forest-green, color-scheme aligned)
    _hdr_left, _hdr_right = st.columns([0.68, 0.32])
    with _hdr_left:
        st.markdown(
            f"""
            <div style="display:flex; align-items:center; gap:0.6rem; margin:0.2rem 0 0.2rem 0;">
                <span style="display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; background:{PRIMARY}; color:#fff; border-radius:8px; flex-shrink:0;">
                    <i class="material-symbols-outlined" style="font-size:18px; line-height:1;">agriculture</i>
                </span>
                <div>
                    <div style="font-size:1.05rem; font-weight:800; color:{DARK}; letter-spacing:-0.3px; line-height:1.1;">PalaySense Decision Support Panel</div>
                    <div style="font-size:0.76rem; color:{MUTED}; font-weight:500;">Province of Bataan • Price: {price_month if not is_clean else "No data"} • Yield: {yield_period if not is_clean else "No data"}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with _hdr_right:
        _view_full = st.toggle("View Full Insights", value=st.session_state.get("dsp_view_full_insights", False), key="dsp_view_full_insights", help="ON: show Core Problem + sub-problem details (floating). OFF: KPIs only.")
    st.markdown(
        f"""
        <div style="margin:0 0 0.9rem 0;">
            <span style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; padding:0.25rem 0.55rem; border-radius:999px;">LGU Executive Brief — KPIs only</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPIs — use yield gap, not volume shortfall — 2x2 grid (fits dual-view right column, no dead space)
    is_good_supply = supply_shortfall >= 0
    is_good_price = price_outlook >= -1

    _row1c1, _row1c2 = st.columns(2)
    _row2c1, _row2c2 = st.columns(2)
    c1, c2, c3, c4 = _row1c1, _row1c2, _row2c1, _row2c2
    with c1:
        col = PRIMARY if is_good_supply and not is_clean else AMBER
        label = "Production vs Target"
        _dir1 = "above" if supply_shortfall >= 0 else "below"
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid {col}"><div class="ps-dsp-kpi-label">{label} • {yield_period}</div><div class="ps-dsp-kpi-val" style="color:{col}">{supply_shortfall:+.1f}%</div><div style="font-size:0.70rem; color:{MUTED};">Rice harvest volume is {abs(supply_shortfall):.1f}% {_dir1} the Department of Agriculture target.</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Rice harvest volume is {abs(supply_shortfall):.1f}% {_dir1} the DA target (4.50 MT/ha).")
            try:
                hist = load_provincial_history()
                if hist.empty or "quarterly_yield_mt_per_ha" not in hist.columns:
                    st.info("No yield history to show.")
                else:
                    y = hist.dropna(subset=["quarterly_yield_mt_per_ha"]).tail(16)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=y["date"], y=y["quarterly_yield_mt_per_ha"], mode="lines+markers", name="Yield", line=dict(color=PRIMARY, width=2)))
                    fig.add_hline(y=4.50, line_dash="dash", line_color=AMBER, annotation_text="DA Target 4.50")
                    fig.add_hline(y=avg_yield, line_dash="dot", line_color="#6B7280", annotation_text=f"Forecast avg {avg_yield:.2f}")
                    fig.update_layout(height=180, margin=dict(t=10, b=20, l=30, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(size=10), yaxis_title="MT/ha", xaxis_title="")
                    st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.info("No data for chart.")
    with c2:
        col = PRIMARY if is_good_price and not is_clean else AMBER
        _pdir = "increase" if price_outlook >= 0 else "decrease"
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid {col}"><div class="ps-dsp-kpi-label">Market Farmgate Price • {price_month}</div><div class="ps-dsp-kpi-val" style="color:{col}">{price_outlook:+.1f}%</div><div style="font-size:0.70rem; color:{MUTED};">Buying prices at the farmgate are projected to {_pdir} by {abs(price_outlook):.1f}%.</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Buying prices at the farmgate are projected to {_pdir} by {abs(price_outlook):.1f}% vs historical average.")
            try:
                hist = load_provincial_history()
                if hist.empty or "fancy_palay_price" not in hist.columns:
                    st.info("No price history to show.")
                else:
                    p = hist.dropna(subset=["fancy_palay_price", "other_variety_price"]).tail(16)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=p["date"], y=p["fancy_palay_price"], mode="lines", name="Fancy", line=dict(color="#1B5E20", width=1.5)))
                    fig.add_trace(go.Scatter(x=p["date"], y=p["other_variety_price"], mode="lines", name="Regular", line=dict(color="#6D28D9", width=1.5)))
                    fig.add_hline(y=p["fancy_palay_price"].mean(), line_dash="dot", line_color="#9CA3AF")
                    fig.update_layout(height=180, margin=dict(t=10, b=20, l=30, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(size=10), yaxis_title="PhP/kg", xaxis_title="", legend=dict(orientation="h", y=1.05))
                    st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.info("No data for chart.")
    with c3:
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid {PRIMARY}"><div class="ps-dsp-kpi-label">Expected Average Harvest • {yield_period}</div><div class="ps-dsp-kpi-val">{avg_yield:.2f} MT/ha</div><div style="font-size:0.70rem; color:{MUTED};">Estimated total harvest is {avg_yield:.2f} metric tons per hectare.</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Estimated total harvest is {avg_yield:.2f} metric tons per hectare ({yield_period}).")
            try:
                fig = go.Figure(go.Bar(x=["Avg", "Low"], y=[avg_yield, low_yield], marker_color=[PRIMARY, "#9CA3AF"], text=[f"{avg_yield:.2f}", f"{low_yield:.2f}"], textposition="outside", marker_cornerradius=8))
                fig.add_hline(y=4.50, line_dash="dash", line_color=AMBER)
                fig.update_layout(height=180, margin=dict(t=10, b=20, l=30, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(size=10), yaxis_title="MT/ha", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.info("No forecast to show.")
    with c4:
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid #6B7280"><div class="ps-dsp-kpi-label">Worst-Case Estimate • {yield_period}</div><div class="ps-dsp-kpi-val">{low_yield:.2f} MT/ha</div><div style="font-size:0.70rem; color:{MUTED};">Lowest expected harvest for the period is {low_yield:.2f} metric tons per hectare.</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Lowest expected harvest for the period is {low_yield:.2f} metric tons per hectare.")
            try:
                fig = go.Figure(go.Bar(x=["Low", "Target"], y=[low_yield, 4.50], marker_color=["#DC2626", AMBER], text=[f"{low_yield:.2f}", "4.50"], textposition="outside", marker_cornerradius=8))
                fig.update_layout(height=180, margin=dict(t=10, b=20, l=30, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(size=10), yaxis_title="MT/ha", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.info("No data for chart.")


    if not _view_full:
        st.caption("Toggle **View Full Insights** above for Core Problem + sub-problem details (floating popovers, no page scroll).")
        st.markdown(
            """
            <div style="text-align:center; margin-top:0.9rem; padding:0.6rem 0.8rem; border-top:1px solid #E5E7EB;">
                <span style="font-size:0.72rem; color:#6B7280; font-style:italic; line-height:1.4;">
                ⚠️ <em>Disclaimer: Figures above are forecast interpretations (price + yield models vs DA 4.50 MT/ha and historical average) for the Province of Bataan. This panel does not prescribe LGU operations, procurement, or infrastructure actions.</em>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Core problem (inline) — sub-problems float via popovers below
    with st.container(border=True):
        if is_clean:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.45rem; margin-bottom:0.5rem;">
                    <i class="material-symbols-outlined" style="font-size:18px; color:{MUTED};">warning</i>
                    <span style="font-size:0.85rem; font-weight:800; color:{DARK}; letter-spacing:0.2px;">1 &nbsp; Core Problem Statement</span>
                    <span style="margin-left:auto; font-size:0.65rem; font-weight:700; color:{MUTED}; background:#F3F4F6; border:1px solid {BORDER}; padding:0.15rem 0.45rem; border-radius:999px;">NO DATA</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.info("No reading — no dataset. Upload historical price & yield data via Import Data to generate the forecast summary.", icon="ℹ️")
        elif is_good_supply and is_good_price:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.45rem; margin-bottom:0.5rem;">
                    <i class="material-symbols-outlined" style="font-size:18px; color:{PRIMARY};">check_circle</i>
                    <span style="font-size:0.85rem; font-weight:800; color:{DARK}; letter-spacing:0.2px;">1 &nbsp; Core Status — Stable</span>
                    <span style="margin-left:auto; font-size:0.65rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; padding:0.15rem 0.45rem; border-radius:999px;">ON TRACK</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.success(
                f"**Governor's Summary — Province is On Track:**\n"
                f"- **Problem:** None at this time. Harvest is **{supply_shortfall:+.1f}% vs the DA target** (avg **{avg_yield:.2f}**, worst-case **{low_yield:.2f} MT/ha**) and farmgate prices are **{price_outlook:+.1f}%**.\n"
                f"- **Impact:** Supply for {yield_period} is sufficient and farmer income for {price_month} is holding.\n"
                f"- **Next step:** Continue routine monitoring and confirm with the next forecast cycle.",
                icon="✅",
            )
        else:
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.45rem; margin-bottom:0.5rem;">
                    <i class="material-symbols-outlined" style="font-size:18px; color:{AMBER};">warning</i>
                    <span style="font-size:0.85rem; font-weight:800; color:{DARK}; letter-spacing:0.2px;">1 &nbsp; Core Problem Statement</span>
                    <span style="margin-left:auto; font-size:0.65rem; font-weight:700; color:{AMBER}; background:{AMBER_BG}; border:1px solid {AMBER_BORDER}; padding:0.15rem 0.45rem; border-radius:999px;">HIGH PRIORITY</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            # Fixed: yield gap (not volume), price direction and logic match sign
            price_word = "decrease" if price_outlook < 0 else "increase"
            if price_outlook < 0:
                pressure = "double strain on farmer income"
            else:
                pressure = "single strain — the price increase partly cushions the harvest shortfall"
            st.warning(
                f"**Governor's Brief — {yield_period} / {price_month}:**\n"
                f"- **Problem:** Rice harvest volume is **{abs(supply_shortfall):.1f}% below** the DA target (avg **{avg_yield:.2f}**, worst-case **{low_yield:.2f} MT/ha**), while farmgate prices are projected to **{price_word} by {abs(price_outlook):.1f}%**.\n"
                f"- **Impact:** {pressure} for our farmers this period.\n"
                f"- **Next step:** Treat the harvest gap as an early warning and validate total volume against actual harvested area before any planning decision.",
                icon="⚠️",
            )

    # 2, 3, 4 — three responsive columns
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.45rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; color:{PRIMARY};">inventory_2</i>
                    <span style="font-size:0.80rem; font-weight:800; color:{DARK};">2 &nbsp; Supply Reading</span>
                </div>
                <div style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; display:inline-block; padding:0.15rem 0.4rem; border-radius:999px; margin-bottom:0.6rem;">Yield vs DA Target 4.50</div>
                """,
                unsafe_allow_html=True,
            )
            if is_clean:
                st.info("No reading — no dataset.", icon="ℹ️")
            elif is_good_supply:
                _low_gap = (avg_yield - low_yield) if avg_yield and low_yield else 0
                st.markdown(
                    f"""
                    - **Problem:** None. Expected harvest is **{avg_yield:.2f} MT/ha**, **{supply_shortfall:+.1f}% vs target** ({_gap_word} gap).
                    - **Impact:** Supply for {yield_period} is sufficient; worst-case quarter holds at **{low_yield:.2f} MT/ha** (only {max(0, _low_gap):.2f} below average).
                    - **Next step:** Keep the provincial forecast on watch; municipal yield split is not modeled — provincial figure only.
                    """
                )
            else:
                _low_gap = (avg_yield - low_yield) if avg_yield and low_yield else 0
                st.markdown(
                    f"""
                    - **Problem:** Expected harvest is **{avg_yield:.2f} MT/ha**, **{abs(supply_shortfall):.1f}% below target** ({_gap_word} gap); weakest quarter drops to **{low_yield:.2f} MT/ha**.
                    - **Impact:** Tighter provincial supply in {yield_period} — shortfall of {max(0, _low_gap):.2f} MT/ha between average and worst quarter.
                    - **Next step:** Flag the worst quarter for review and confirm total volume with harvested-area records.
                    """
                )

    with col_b:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.45rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; color:{PRIMARY};">payments</i>
                    <span style="font-size:0.80rem; font-weight:800; color:{DARK};">3 &nbsp; Price Reading</span>
                </div>
                <div style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; display:inline-block; padding:0.15rem 0.4rem; border-radius:999px; margin-bottom:0.6rem;">Forecast vs Historical Average</div>
                """,
                unsafe_allow_html=True,
            )
            if is_clean:
                st.info("No reading — no dataset.", icon="ℹ️")
            elif is_good_price:
                st.markdown(
                    f"""
                    - **Problem:** None. Buying prices at the farmgate are projected to **increase by {price_outlook:+.1f}%** in {price_month} ({_p_word} movement).
                    - **Impact:** Firmer income outlook for farmers this month. {_muni_line if _muni_line else "Municipal split unavailable for this cycle."}
                    - **Next step:** Track whether the gain holds in the next monthly update.
                    """
                )
            else:
                st.markdown(
                    f"""
                    - **Problem:** Buying prices at the farmgate are projected to **decrease by {abs(price_outlook):.1f}%** in {price_month} ({_p_word} movement).
                    - **Impact:** Softer income outlook for farmers this month. {_muni_line if _muni_line else "Municipal split unavailable for this cycle."}
                    - **Next step:** Monitor the next price update to confirm if the softness persists.
                    """
                )

    with col_c:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.45rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; color:{PRIMARY};">visibility</i>
                    <span style="font-size:0.80rem; font-weight:800; color:{DARK};">4 &nbsp; Combined Outlook</span>
                </div>
                <div style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; display:inline-block; padding:0.15rem 0.4rem; border-radius:999px; margin-bottom:0.6rem;">Yield + Price Together</div>
                """,
                unsafe_allow_html=True,
            )
            if is_clean:
                st.info("No reading — no dataset.", icon="ℹ️")
            elif is_good_supply and is_good_price:
                st.markdown(
                    f"""
                    - **Problem:** None. Harvest is **{supply_shortfall:+.1f}% vs target** ({_gap_word}) and farmgate prices are **{price_outlook:+.1f}%** ({_p_word}).
                    - **Impact:** No added strain on provincial supply or farmer income.
                    - **Next step:** {_muni_line + " Continue routine monitoring." if _muni_line else "Continue routine monitoring into the next forecast cycle."}
                    """
                )
            else:
                st.markdown(
                    f"""
                    - **Problem:** Harvest is **{abs(supply_shortfall):.1f}% below target** ({_gap_word} gap) with prices **{price_outlook:+.1f}%** ({_p_word}).
                    - **Impact:** {"Single strain — the price increase partly cushions the harvest shortfall." if price_outlook >= 0 else "Double strain — softer harvest plus softer prices squeeze farmer income."}
                    - **Next step:** {_muni_line + " " if _muni_line else ""}Prioritize review of the worst-case quarter ({low_yield:.2f} MT/ha) and the {price_month} price update.
                    """
                )

    # Disclaimer — exact wording, small font
    st.markdown(
        """
        <div style="text-align:center; margin-top:0.9rem; padding:0.6rem 0.8rem; border-top:1px solid #E5E7EB;">
            <span style="font-size:0.72rem; color:#6B7280; font-style:italic; line-height:1.4;">
            ⚠️ <em>Disclaimer: Figures above are forecast interpretations (price + yield models vs DA 4.50 MT/ha and historical average) for the Province of Bataan. This panel does not prescribe LGU operations, procurement, or infrastructure actions.</em>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

