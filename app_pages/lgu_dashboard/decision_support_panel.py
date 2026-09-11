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
        .ps-dsp-card { background:#fff; border:1px solid #E6EAE6; border-radius:14px; padding:1rem 1.1rem; box-shadow:0 2px 8px rgba(0,0,0,0.04); }
        .ps-dsp-kpi { background:#fff; border:1px solid #E6EAE6; border-radius:12px; padding:0.85rem 1rem; text-align:center; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
        .ps-dsp-kpi-val { font-size:1.35rem; font-weight:800; color:#123524; line-height:1.1; letter-spacing:-0.3px; }
        .ps-dsp-kpi-label { font-size:0.68rem; font-weight:700; color:#6B7280; text-transform:uppercase; letter-spacing:0.4px; }
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
):
    """
    Executive Decision Support Panel for Bataan.
    All numbers are real-time forecasted inputs — defaults match your current
    Yield Summary (4.07 avg vs 4.50 DA target = -9.6% shortfall, low 4.04).
    price_month: e.g. "Sep 2026" for price outlook
    yield_period: e.g. "Q4 2026 – Q3 2027" for yield horizon
    When clean state (no dataset), pass 0 for all numbers — panel auto-shows
    "No recommendation" instead of actions.
    """
    _inject_css()
    is_clean = (avg_yield == 0 and low_yield == 0 and supply_shortfall == 0 and price_outlook == 0)

    # Header — executive — now shows both horizons to avoid confusion
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:0.6rem; margin:0.2rem 0 0.9rem 0;">
            <span style="display:inline-flex; align-items:center; justify-content:center; width:32px; height:32px; background:{PRIMARY}; color:#fff; border-radius:8px;">
                <i class="material-symbols-outlined" style="font-size:18px; line-height:1;">agriculture</i>
            </span>
            <div>
                <div style="font-size:1.05rem; font-weight:800; color:{DARK}; letter-spacing:-0.3px; line-height:1.1;">PalaySense Decision Support Panel</div>
                <div style="font-size:0.76rem; color:{MUTED}; font-weight:500;">Province of Bataan • Price: {price_month if not is_clean else "No data"} • Yield: {yield_period if not is_clean else "No data"}</div>
            </div>
            <span style="margin-left:auto; font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; padding:0.25rem 0.55rem; border-radius:999px;">LGU Executive Brief</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPIs — use yield gap, not volume shortfall
    is_good_supply = supply_shortfall >= 0
    is_good_price = price_outlook >= -1

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        col = PRIMARY if is_good_supply and not is_clean else AMBER
        label = "Yield Gap" if not is_good_supply or is_clean else "Yield Surplus"
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid {col}"><div class="ps-dsp-kpi-label">{label} • {yield_period}</div><div class="ps-dsp-kpi-val" style="color:{col}">{supply_shortfall:+.1f}%</div><div style="font-size:0.70rem; color:{MUTED};">vs DA Target 4.50 MT/ha (yield, not volume)</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Supports {supply_shortfall:+.1f}% — yield vs DA target 4.50")
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
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid {col}"><div class="ps-dsp-kpi-label">Price Outlook • {price_month}</div><div class="ps-dsp-kpi-val" style="color:{col}">{price_outlook:+.1f}%</div><div style="font-size:0.70rem; color:{MUTED};">farmgate — farmer income vs hist</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Supports {price_outlook:+.1f}% — farmgate price vs hist avg")
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
            f'<div class="ps-dsp-kpi" style="border-left:3px solid {PRIMARY}"><div class="ps-dsp-kpi-label">Avg Yield Forecast • {yield_period}</div><div class="ps-dsp-kpi-val">{avg_yield:.2f} MT/ha</div><div style="font-size:0.70rem; color:{MUTED};">{yield_period}</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Avg {avg_yield:.2f} of 4 quarters — {yield_period}")
            try:
                fig = go.Figure(go.Bar(x=["Avg", "Low"], y=[avg_yield, low_yield], marker_color=[PRIMARY, "#9CA3AF"], text=[f"{avg_yield:.2f}", f"{low_yield:.2f}"], textposition="outside"))
                fig.add_hline(y=4.50, line_dash="dash", line_color=AMBER)
                fig.update_layout(height=180, margin=dict(t=10, b=20, l=30, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(size=10), yaxis_title="MT/ha", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.info("No forecast to show.")
    with c4:
        st.markdown(
            f'<div class="ps-dsp-kpi" style="border-left:3px solid #6B7280"><div class="ps-dsp-kpi-label">Low Yield Limit • {yield_period}</div><div class="ps-dsp-kpi-val">{low_yield:.2f} MT/ha</div><div style="font-size:0.70rem; color:{MUTED};">lowest of 4 quarters</div></div>',
            unsafe_allow_html=True,
        )
        with st.popover("Show chart", use_container_width=True):
            st.caption(f"Low {low_yield:.2f} is minimum of next 4 quarters")
            try:
                fig = go.Figure(go.Bar(x=["Low", "Target"], y=[low_yield, 4.50], marker_color=["#DC2626", AMBER], text=[f"{low_yield:.2f}", "4.50"], textposition="outside"))
                fig.update_layout(height=180, margin=dict(t=10, b=20, l=30, r=10), plot_bgcolor="white", paper_bgcolor="white", font=dict(size=10), yaxis_title="MT/ha", showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            except Exception:
                st.info("No data for chart.")


    # Core problem — changes if outcome is good
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
            st.info("No recommendation — no dataset. Upload historical price & yield data via Import Data to generate the decision brief.", icon="ℹ️")
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
                f"**Stable:** Bataan shows **{supply_shortfall:+.1f}% surplus** (avg **{avg_yield:.2f} MT/ha** vs 4.50, low **{low_yield:.2f} MT/ha**) and **{price_outlook:+.1f}% price movement** — supply buffer is adequate and farmer margins are stable. Maintain monitoring and prepare market expansion.",
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
            price_word = "drop" if price_outlook < 0 else "rise"
            if price_outlook < 0:
                pressure = "lower yield + lower farmgate price = double pressure on farmer margins"
            else:
                pressure = "lower yield but higher farmgate price = single pressure — price rise partially offsets yield loss"
            st.warning(
                f"**Risk:** Bataan shows a **{abs(supply_shortfall):.1f}% yield gap** (avg **{avg_yield:.2f} MT/ha** vs DA target 4.50, low **{low_yield:.2f} MT/ha**; volume gap depends on harvested area) combined with a **{price_outlook:+.1f}% farmgate price {price_word}** — {pressure}. Use yield gap as early warning, confirm volume with area data.",
                icon="⚠️",
            )

    # 2, 3, 4 — three responsive columns
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.45rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; color:{PRIMARY};">local_shipping</i>
                    <span style="font-size:0.80rem; font-weight:800; color:{DARK};">2 &nbsp; Logistics & Supply Action</span>
                </div>
                <div style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; display:inline-block; padding:0.15rem 0.4rem; border-radius:999px; margin-bottom:0.6rem;">Bataan Food Security Protocol</div>
                """,
                unsafe_allow_html=True,
            )
            if is_clean:
                st.info("No recommendation — no dataset.", icon="ℹ️")
            elif is_good_supply:
                st.markdown(
                    f"""
                    - **Maintain buffer and plan inter-municipal sale** — surplus vs 4.50 allows market expansion.
                    - **Optimize warehouse use** — keep FIFO but prioritize quality preservation for surplus.
                    - **Coordinate surplus distribution** — high yield ({avg_yield:.2f} MT/ha, low {low_yield:.2f}) supports stable supply.
                    """
                )
            else:
                st.markdown(
                    f"""
                    - **Calculate net volume gap** for Bataan municipalities (target 4.50 vs forecast {avg_yield:.2f} MT/ha × harvested area) to size the buffer needed.
                    - **FIFO warehouse rotation** for local palay buffers — release oldest stock first to keep quality and free space.
                    - **Emergency silo coordination** — pre-book provincial silos and schedule inter-municipal transfer for the low-yield quarter approaching {low_yield:.2f} MT/ha.
                    """
                )

    with col_b:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.45rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; color:{PRIMARY};">payments</i>
                    <span style="font-size:0.80rem; font-weight:800; color:{DARK};">3 &nbsp; Economic Intervention</span>
                </div>
                <div style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; display:inline-block; padding:0.15rem 0.4rem; border-radius:999px; margin-bottom:0.6rem;">Sagip Saka Act / R.A. 11321 Compliance</div>
                """,
                unsafe_allow_html=True,
            )
            if is_clean:
                st.info("No recommendation — no dataset.", icon="ℹ️")
            elif is_good_price:
                st.markdown(
                    """
                    - **Maintain current support** — price stable, continue voucher monitoring.
                    - **Advise timing for sales** — help farmers capture favorable prices.
                    - **Keep PCIC desk on standby** — no immediate surge needed.
                    """
                )
            else:
                st.markdown(
                    f"""
                    - **Localized fertilizer/seed vouchers** — prioritize cooperatives near the {low_yield:.2f} MT/ha low-yield limit.
                    - **Direct LGU procurement** at a **minimum floor price** to shield farmers from the {price_outlook:+.1f}% dip.
                    - **Fast-track PCIC claims** for affected cooperatives — use forecast as early proof.
                    """
                )

    with col_c:
        with st.container(border=True):
            st.markdown(
                f"""
                <div style="display:flex; align-items:center; gap:0.4rem; margin-bottom:0.45rem;">
                    <i class="material-symbols-outlined" style="font-size:16px; color:{PRIMARY};">water_drop</i>
                    <span style="font-size:0.80rem; font-weight:800; color:{DARK};">4 &nbsp; Infrastructure & Resource Mitigation</span>
                </div>
                <div style="font-size:0.68rem; font-weight:700; color:{PRIMARY}; background:#ECFDF5; border:1px solid #A7F3D0; display:inline-block; padding:0.15rem 0.4rem; border-radius:999px; margin-bottom:0.6rem;">PalaySense Extension Framework</div>
                """,
                unsafe_allow_html=True,
            )
            if is_clean:
                st.info("No recommendation — no dataset.", icon="ℹ️")
            elif is_good_supply:
                st.markdown(
                    """
                    - **Standard irrigation schedule** — maintain current water allocation.
                    - **Maintain solar pump readiness** — keep for peak demand.
                    - **Monthly soil-moisture checks** — routine monitoring while yield is stable.
                    """
                )
            else:
                st.markdown(
                    f"""
                    - **Rotational irrigation** across Bataan sectors — stagger water for the 4-quarter low window.
                    - **Deploy solar-powered pumps** in priority low-yield zones to cut fuel cost.
                    - **Weekly soil-moisture monitoring** — trigger alerts before {low_yield:.2f} MT/ha threshold.
                    """
                )

    # Disclaimer — exact wording, small font
    st.markdown(
        """
        <div style="text-align:center; margin-top:0.9rem; padding:0.6rem 0.8rem; border-top:1px solid #E5E7EB;">
            <span style="font-size:0.72rem; color:#6B7280; font-style:italic; line-height:1.4;">
            ⚠️ <em>Disclaimer: PalaySense insights are decision support recommendations aligned with Department of Agriculture (DA), PCIC, and R.A. 11321 frameworks for the Province of Bataan. Final execution requires localized LGU council approval and budget appropriation.</em>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

