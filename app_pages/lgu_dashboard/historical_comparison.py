"""
PalaySense OPA Dashboard — Historical Comparison
================================================
Consolidates municipal historical views into a single page with 2 tabs:

  Tab 1: Municipal Production Comparison
  Tab 2: Top Municipalities by Production (ranking snapshot)

Provincial Price History removed from Comparison per OPA IA cleanup
(2026-09-22) — now lives solely in Analytics > Provincial > Monthly Price Detail
(single-year bar view) for provincial-level decision support.
Comparison is now strictly municipal-focused.

Municipal Price Trends was moved to
Analytics > Municipal > Municipal Prices — see municipal_analytics.py
(_municipal_price_tab) so that history lives under Analytics and
Comparison stays for cross-municipality trends.

Year filtering uses an unlimited st.multiselect (no arbitrary range limits).
Display is 2019-2025 — 2026 hidden (partial Jan-Jul), 2009-2018 kept for lag/training only.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from . import theme


# ------------------------------------------------------------------
# Tab helpers
# ------------------------------------------------------------------
def _year_multiselect(df, key, label="Select Years"):
    """Unlimited multi-select year picker (no range slider). 2019-2025 display — 2026 hidden (partial), 2009-2018 lag/cleaning."""
    years = sorted(df["year"].dropna().unique().tolist())
    years = [y for y in years if 2019 <= int(y) <= 2025]
    if not years:
        return []
    selected = st.multiselect(
        label,
        options=years,
        default=years,
        key=key,
        help="Select any number of years — no range limit.",
    )
    return selected


# ------------------------------------------------------------------
# Tab 1: Municipal Production Comparison
# ------------------------------------------------------------------
def _production_comparison_tab(dr):
    with theme.section_card(title="Municipal Production Comparison",
                            desc="Historical production comparison across municipalities.",
                            icon_name="compare_arrows"):
        # Use production dataset (84 rows, palay_production), fallback to municipality_df if needed
        muni = getattr(dr, "municipal_production_df", None)
        if muni is None or getattr(muni, "empty", True) or "palay_production" not in muni.columns:
            muni = getattr(dr, "municipality_df", None)
        if muni is None or getattr(muni, "empty", True) or "palay_production" not in muni.columns:
            st.info("Municipality production dataset not available.")
            return

        m = muni.copy()
        m["year"] = pd.to_datetime(m["date"]).dt.year
        m = m[(m["year"] >= 2019) & (m["year"] <= 2025)]
        if "year" not in m.columns or m["year"].dropna().empty:
            st.info("No municipality year data.")
            return

        # Unlimited year selector (replaces the restricted range slider) — 2019-2025 only, 2026 hidden
        selected_years = _year_multiselect(m, key="hist_prod_years", label="Select Years")
        if not selected_years:
            st.info("Please select at least one year.")
            return

        # Municipality multiselect
        munis = sorted(m["municipality"].dropna().unique().tolist())
        selected_munis = st.multiselect(
            "Municipalities", options=munis, default=munis, key="hist_prod_munis"
        )

        sub = m[m["year"].isin(selected_years)].copy()
        if selected_munis:
            sub = sub[sub["municipality"].isin(selected_munis)]

        if sub.empty:
            st.info("No data for the selected filters.")
            return

        # Aggregate by municipality + year
        agg = sub.groupby(["municipality", "year"])["palay_production"].sum().reset_index()

        # --- Insight computations (for summary card) ---
        try:
            _tot_by_muni = agg.groupby("municipality")["palay_production"].sum().sort_values(ascending=False)
            _hi_muni = str(_tot_by_muni.index[0]) if not _tot_by_muni.empty else "—"
            _hi_val = float(_tot_by_muni.iloc[0]) if not _tot_by_muni.empty else 0.0
            _lo_muni = str(_tot_by_muni.index[-1]) if not _tot_by_muni.empty else "—"
            _lo_val = float(_tot_by_muni.iloc[-1]) if not _tot_by_muni.empty else 0.0
            _avg_muni = float(_tot_by_muni.mean()) if not _tot_by_muni.empty else 0.0
            _total_all = float(_tot_by_muni.sum()) if not _tot_by_muni.empty else 0.0
            _share_hi = (_hi_val / _total_all * 100) if _total_all else 0.0
            # Yearly trend
            _year_tot = agg.groupby("year")["palay_production"].sum().sort_index()
            if len(_year_tot) >= 2:
                _first, _last = float(_year_tot.iloc[0]), float(_year_tot.iloc[-1])
                _chg = ((_last - _first) / _first * 100) if _first else 0.0
                _trend_label = "INCREASING" if _last > _first else "DECREASING" if _last < _first else "STABLE"
                _trend_color = "#2E7D32" if _chg > 1 else "#C62828" if _chg < -1 else "#6B7280"
                _trend_arrow = "↑" if _chg > 0 else "↓" if _chg < 0 else "→"
            else:
                _chg, _trend_label, _trend_color, _trend_arrow = 0.0, "STABLE", "#6B7280", "→"
                _year_tot = _year_tot  # noop
            _yr_label = f"{min(selected_years)}–{max(selected_years)}" if len(selected_years) > 1 else str(selected_years[0])
        except Exception:
            _hi_muni, _hi_val, _lo_muni, _lo_val, _avg_muni, _share_hi = "—", 0.0, "—", 0.0, 0.0, 0.0
            _chg, _trend_label, _trend_color, _trend_arrow, _yr_label = 0.0, "STABLE", "#6B7280", "→", "—"

        # Grouped bar — better for 11 munis × 3 yrs (was line, spaghetti)
        agg["year"] = agg["year"].astype(str)
        fig = px.bar(agg, x="palay_production", y="municipality", color="year", barmode="group",
                     orientation="h", text=agg["palay_production"].round(0).astype(int),
                     color_discrete_sequence=px.colors.qualitative.Set2)
        _gtitle = f"Municipal Palay Production Comparison ({_yr_label}) — Total MT per Municipality per Year"
        fig.update_layout(
            title=dict(text=_gtitle, x=0.5, xanchor="center", font=dict(size=13, color="#1B4332", family=theme.FONT)),
            xaxis_title="Production (MT)", yaxis_title="Municipality",
            height=420, plot_bgcolor="white", paper_bgcolor="white",
            font=dict(family=theme.FONT, size=12),
            legend=dict(title="Year", orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,0,0,0.05)", categoryorder="total ascending"),
            xaxis=dict(gridcolor="rgba(0,0,0,0.05)"),
            margin=dict(t=55, b=40, l=40, r=40),
        )
        fig.update_traces(texttemplate='%{text:,}', textposition='outside', marker_cornerradius=6)

        col_chart, col_insight = st.columns([0.68, 0.32], gap="small", vertical_alignment="top")
        with col_chart:
            st.plotly_chart(fig, use_container_width=True, key="hist_prod_chart")
        with col_insight:
            st.markdown(f"""
            <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:12px 0 0 0;">
              <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
                <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">insights</i>
                <span style="font-weight:800; color:#1B4332; font-size:0.85rem;">Comparison Insight</span>
                <span style="font-size:0.65rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:2px 6px; border-radius:999px; margin-left:auto;">{_yr_label}</span>
              </div>
              <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.70rem; color:#6B7280;">Highest (Total {_yr_label}):</span>
                    <b style="color:#1B4332; font-size:0.82rem;">{_hi_muni} — {_hi_val:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:flex-start; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#DC2626; font-size:14px; margin-top:1px;">trending_down</i>
                  <div style="display:flex; flex-direction:column; line-height:1.2;">
                    <span style="font-size:0.70rem; color:#6B7280;">Lowest (Total {_yr_label}):</span>
                    <b style="color:#DC2626; font-size:0.82rem;">{_lo_muni} — {_lo_val:,.0f} MT</b>
                  </div>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">analytics</i>
                  <span>Mean (per muni):</span> <b style="color:#1B4332;">{_avg_muni:,.0f} MT</b>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                  <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">pie_chart</i>
                  <span>Top Share:</span> <b style="color:#1B4332;">{_share_hi:.1f}% of total</b>
                </div>
                <hr style="border:none; border-top:1px solid #C8E6C9; margin:4px 0;">
                <div style="display:flex; align-items:center; gap:6px; font-size:0.78rem;">
                  <i class="material-symbols-outlined" style="color:{_trend_color}; font-size:14px;">trending_up</i>
                  <span>Overall Trend:</span> <b style="color:{_trend_color};">{_trend_arrow} {_trend_label} ({_chg:+.1f}%)</b>
                </div>
                <div style="font-size:0.68rem; color:#6B7280;">Selected: {len(sub["municipality"].unique())} munis · {len(selected_years)} yrs</div>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Helpers for Top Municipalities (moved from municipal_analytics)
# ------------------------------------------------------------------
_MUNI_VARIETY_COLS = (
  "hybridpremium_dry", "hybridpremium_wet",
  "hybridordinary_dry", "hybridordinary_wet",
  "inbredpremium_dry", "inbredpremium_wet",
  "inbredordinary_dry", "inbredordinary_wet",
)

def _derive_municipal_columns(m):
  """Derive palay_production/dry_season/wet_season if missing."""
  m = m.copy()
  available = [c for c in _MUNI_VARIETY_COLS if c in m.columns]
  if not available:
    return m
  if "palay_production" not in m.columns:
    m["palay_production"] = m[available].sum(axis=1, numeric_only=True)
  if "dry_season" not in m.columns:
    dry = [c for c in available if c.endswith("_dry")]
    if dry:
      m["dry_season"] = m[dry].sum(axis=1, numeric_only=True)
  if "wet_season" not in m.columns:
    wet = [c for c in available if c.endswith("_wet")]
    if wet:
      m["wet_season"] = m[wet].sum(axis=1, numeric_only=True)
  return m

def _year_only_filter(dr, key="hist_year_simple"):
  """Compact single Year dropdown (1 column layout). 2019-2025 display — 2026 hidden (partial)."""
  year_list = []
  try:
    hist = dr.municipality_history_df
    if hist is not None and not getattr(hist, "empty", True):
      year_list = sorted(hist["year"].dropna().unique().tolist())
  except Exception:
    year_list = []
  # fallback: derive from municipal_production_df if history missing
  if not year_list:
    try:
      _tmp = getattr(dr, "municipal_production_df", None)
      if _tmp is None or getattr(_tmp, "empty", True):
        _tmp = getattr(dr, "municipality_df", None)
      if _tmp is not None and not getattr(_tmp, "empty", True) and "date" in _tmp.columns:
        _tmp2 = _tmp.copy()
        _tmp2["date"] = pd.to_datetime(_tmp2["date"], errors="coerce")
        year_list = sorted(_tmp2["date"].dt.year.dropna().astype(int).unique().tolist())
    except Exception:
      pass
  year_list = [y for y in year_list if 2019 <= int(y) <= 2025]
  col_year, _ = st.columns([1, 4])
  with col_year:
    if year_list:
      selected_year = st.selectbox("Year", options=year_list,
                     index=len(year_list) - 1,
                     key=key, label_visibility="visible")
    else:
      selected_year = None
      st.selectbox("Year", options=["N/A"], disabled=True,
             key=f"{key}_na", label_visibility="visible")
  return selected_year


# ------------------------------------------------------------------
# Tab 2: Top Municipalities by Production (moved from Municipal Analytics)
# ------------------------------------------------------------------
def _top_municipalities_bar(dr):
  """Top municipalities by production (horizontal bar) — now in Comparison."""
  with theme.section_card(title="Top Municipalities by Production",
              desc="Ranking of municipalities by palay production.",
              icon_name="leaderboard"):
    selected_year = _year_only_filter(dr, key="hist_top_year")

    muni = getattr(dr, "municipal_production_df", None)
    if muni is None or getattr(muni, "empty", True):
      muni = getattr(dr, "municipality_df", None)
    if muni is None or getattr(muni, "empty", True):
      st.info("Municipality production dataset not available.")
      return

    m = _derive_municipal_columns(muni)
    if "palay_production" not in m.columns:
      st.info("Municipality production dataset not available.")
      return

    m["date"] = pd.to_datetime(m["date"])
    m["year"] = m["date"].dt.year
    m = m[(m["year"] >= 2019) & (m["year"] <= 2025)]
    if selected_year is not None:
      m = m[m["year"] == selected_year]

    if m.empty:
      st.info("No production data for the selected year.")
      return

    top5 = (
      m.groupby("municipality")["palay_production"]
      .sum().reset_index()
      .sort_values("palay_production", ascending=False)
      .head(5)
    )

    plot_top5 = top5.sort_values("palay_production")

    year_label = f"({selected_year})" if selected_year is not None else ""
    _gtitle = f"Top 5 Municipalities by Palay Production {year_label}" if year_label else "Top 5 Municipalities by Palay Production"
    fig = px.bar(
      plot_top5,
      x="palay_production", y="municipality", orientation="h",
      color="palay_production",
      color_continuous_scale=["#FFF9C4", "#FFF176", "#FBC02D"],
      text=plot_top5["palay_production"].round(0).astype(int),
      title=_gtitle,
    )
    fig.update_layout(
      xaxis_title="Production (MT)", yaxis_title="Municipality",
      title=dict(text=_gtitle, x=0.5, xanchor="center", font=dict(size=13, color="#123524", family=theme.FONT)),
      showlegend=False, plot_bgcolor="white", paper_bgcolor="white",
      height=380, margin=dict(t=55, b=40, l=40, r=40),
      yaxis={"categoryorder": "total ascending"},
    )
    fig.update_traces(texttemplate='%{text:,}', textposition='outside', marker_cornerradius=8)
    col_chart, col_insight = st.columns([0.66, 0.34], gap="small", vertical_alignment="top")
    with col_chart:
      st.plotly_chart(fig, use_container_width=True, key="hist_top5_bar")
    with col_insight:
      try:
        _hi = top5.iloc[0]
        _lo = top5.iloc[-1]
        _hi_m, _hi_v = str(_hi["municipality"]), float(_hi["palay_production"])
        _lo_m, _lo_v = str(_lo["municipality"]), float(_lo["palay_production"])
        _avg = float(top5["palay_production"].mean())
        _total = float(top5["palay_production"].sum())
        _total_all = float(m.groupby("municipality")["palay_production"].sum().sum())
        _share = (_total / _total_all * 100) if _total_all else 0
        st.markdown(f"""
        <div style="background:#F1F8E9; border-left:4px solid #2D6A4F; border-radius:10px; padding:10px 12px; box-shadow:0 1px 6px rgba(0,0,0,0.05); margin:22px 0 0 0;">
          <div style="display:flex; align-items:center; gap:6px; margin-bottom:8px;">
            <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:16px; line-height:1;">insights</i>
            <span style="font-weight:800; color:#1B4332; font-size:0.85rem;">Production Summary</span>
          </div>
          <div style="display:flex; flex-direction:column; gap:5px; font-size:0.80rem; color:#374151; line-height:1.35;">
            <div style="display:flex; align-items:flex-start; gap:6px;">
              <i class="material-symbols-outlined" style="color:#B45309; font-size:14px; margin-top:1px;">emoji_events</i>
              <div style="display:flex; flex-direction:column; line-height:1.2;">
                <span style="font-size:0.75rem; color:#6B7280;">Highest Total Production:</span>
                <b style="color:#1B4332; font-size:0.82rem;">{_hi_m} — { _hi_v:,.0f} MT</b>
              </div>
            </div>
            <div style="display:flex; align-items:flex-start; gap:6px;">
              <i class="material-symbols-outlined" style="color:#DC2626; font-size:14px; margin-top:1px;">trending_down</i>
              <div style="display:flex; flex-direction:column; line-height:1.2;">
                <span style="font-size:0.75rem; color:#6B7280;">Lowest Total Production (Top 5):</span>
                <b style="color:#DC2626; font-size:0.82rem;">{_lo_m} — { _lo_v:,.0f} MT</b>
              </div>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">analytics</i>
              <span>Mean Production (Top 5 Municipalities):</span> <b style="color:#1B4332;">{_avg:,.0f} MT</b>
            </div>
            <div style="display:flex; align-items:center; gap:6px;">
              <i class="material-symbols-outlined" style="color:#2D6A4F; font-size:14px;">pie_chart</i>
              <span>Share of Total Production (Top 5):</span> <b style="color:#1B4332;">{_share:.1f}% of total</b>
            </div>
            <div style="font-size:0.70rem; color:#6B7280; background:white; border:1px solid #D8EED8; padding:3px 7px; border-radius:999px; width:fit-content; margin-top:1px;">Reporting Year: {selected_year if selected_year else "All Years"}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
      except Exception:
        pass


# ------------------------------------------------------------------
# Tab 3: Provincial Price History — REMOVED (2026-09-22)
# Redundant with Analytics > Provincial > Monthly Price Detail.
# Kept as no-op stub for backward compatibility; not rendered.
# See git history for original _provincial_price_trends_tab implementation.
# ------------------------------------------------------------------
def _provincial_price_trends_tab(df):  # pragma: no cover
    st.info("Provincial Price History has moved to **Analytics > Provincial > Monthly Price Detail**.")
    return


# ------------------------------------------------------------------
# Tab 3: Municipal Price Trends — MOVED
# Now lives at Analytics > Municipal > Municipal Prices
# See app_pages/lgu_dashboard/municipal_analytics.py::_municipal_price_tab
# Kept as stub alias so old imports don't break.
# ------------------------------------------------------------------
_RICE_TYPE_PREFIX = {
    "Hybrid": "hybrid",
    "Inbred": "inbred",
}
_RICE_CLASS_SUFFIX = {
    "Premium": "premium",
    "Ordinary": "ordinary",
}
_SEASON_SUFFIX = {"Dry": "dry", "Wet": "wet"}

_MUNICIPALITY_COLORS = {
    "Abucay": "#1f77b4", "Bagac": "#ff7f0e", "Balanga": "#2ca02c",
    "Dinalupihan": "#d62728", "Hermosa": "#9467bd", "Limay": "#8c564b",
    "Mariveles": "#e377c2", "Morong": "#7f7f7f", "Orani": "#bcbd22",
    "Orion": "#17becf", "Pilar": "#ff9896", "Samal": "#98df8a",
}


def _municipal_price_trends_tab(dr):
    """Deprecated stub — chart moved to municipal_analytics."""
    st.info("Municipal Price Trends has moved to **Analytics > Municipal > Municipal Prices**.")


# Actual implementation now imported from municipal_analytics to keep
# a single source of truth if Comparison still needs to embed it.
try:
    from .municipal_analytics import _municipal_price_tab as _muni_price_impl  # noqa: E402
    _municipal_price_trends_tab = _muni_price_impl  # type: ignore
except Exception:
    pass


# ------------------------------------------------------------------
# Main page
# ------------------------------------------------------------------
def render(df, dr):
    if dr is None or not getattr(dr, "has_provincial_data", False):
        st.info("No historical data — comparison hidden (0 values). Upload data via Import Data.")
        return
    theme.page_title("Historical Comparison",
                     "Compare municipalities and historical trends across the selected range.")

    tab_prod, tab_top = st.tabs([
        ":material/bar_chart: Municipal Production Comparison",
        ":material/leaderboard: Top Municipalities",
    ])

    with tab_prod:
        _production_comparison_tab(dr)
    with tab_top:
        _top_municipalities_bar(dr)
