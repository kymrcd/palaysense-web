import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import numpy as np
import os
import plotly.graph_objects as go

# Only entry point into the data layer — all datasets are fetched inside
# overview_page() via reload_dashboard_data() and passed to helpers explicitly.
from data.Dashboard_Ready import reload_dashboard_data
from app_pages.lgu_dashboard import data_layer as dl

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


def _safe_mean(values, default=0.0):
  """NaN-aware mean of a list/series, returning default when empty."""
  if values is None or len(values) == 0:
    return default
  try:
    s = pd.Series(values, dtype="float64").dropna()
    return float(s.mean()) if not s.empty else default
  except Exception:
    return default


def _safe_max(values, default=0.0):
  """NaN-aware max of a list/series, returning default when empty."""
  if values is None or len(values) == 0:
    return default
  try:
    s = pd.Series(values, dtype="float64").dropna()
    return float(s.max()) if not s.empty else default
  except Exception:
    return default


def _safe_min(values, default=0.0):
  """NaN-aware min of a list/series, returning default when empty."""
  if values is None or len(values) == 0:
    return default
  try:
    s = pd.Series(values, dtype="float64").dropna()
    return float(s.min()) if not s.empty else default
  except Exception:
    return default


def _pct_change(current, baseline):
  """Percent change from baseline, returning None for missing/NaN/zero baseline.

  Prevents the '₱0.00/kg (-100.0%)' KPI bug and ZeroDivisionError when the
  baseline is zero, NaN, or the forecast value is unavailable.
  """
  if current is None or baseline is None:
    return None
  try:
    c = float(current)
    b = float(baseline)
  except (TypeError, ValueError):
    return None
  if pd.isna(c) or pd.isna(b):
    return None
  if b == 0:
    return 0.0
  return ((c - b) / b) * 100


def _pick_column(df, candidates):
  """Return the first candidate column name present in df, else None."""
  if df is None:
    return None
  return next((c for c in candidates if c in df.columns), None)


# ------------------------------------------------------------------
# BENCHMARK REFERENCE LINE HELPERS — Inflation-Aware Rolling + Policy Standards
# ------------------------------------------------------------------
def _add_benchmark_ref_line(fig, y_value, label, line_color="#78909C",
                annotation_position="top left"):
  """Add a THIN DOTTED benchmark hline to a Plotly figure.

  Visual hierarchy per spec:
  - Benchmark lines MUST be ``line_dash='dot'``, ``line_width=1.2``, ``opacity=0.6``
    so they never conflict with main forecast trendlines (which remain ``dash``).
  - Annotation kept at ``top left`` / ``bottom left`` to avoid peak markers
    (e.g. ₱27.04 / ₱20.52).
  """
  if fig is None or y_value is None:
    return fig
  try:
    y = float(y_value)
  except (TypeError, ValueError):
    return fig
  if pd.isna(y):
    return fig
  try:
    fig.add_hline(
      y=y,
      line_dash="dot",
      line_width=1.2,
      line_color=line_color,
      opacity=0.6,
      annotation_text=label,
      annotation_position=annotation_position,
      annotation=dict(
        font=dict(size=10, color=line_color),
        bgcolor="rgba(255,255,255,0.85)",
      ),
    )
  except Exception:
    # Fallback without annotation dict for older Plotly versions
    try:
      fig.add_hline(
        y=y,
        line_dash="dot",
        line_width=1.2,
        line_color=line_color,
        opacity=0.6,
        annotation_text=label,
        annotation_position=annotation_position,
      )
    except Exception:
      pass
  return fig


def _benchmark_yield_config(benchmark_option, historical_avg):
  """Return (y_value, label, color) for yield benchmark or None.

  Supported options (Tagalog refactor + legacy):
  - "Presyo sa Merkado" / "3-Year/Quarter Rolling Market Average" / "10-Year Historical Average" -> 10-year dynamic mean of quarterly_yield_mt_per_ha
  - "Target ng Gobyerno" / "NFA / DA Policy Baseline" / "DA Target (4.50 MT/ha)" -> DA Target 4.50
  """
  opt = str(benchmark_option).strip() if benchmark_option is not None else ""
  # Yield: rolling option still uses 10-year mean (per spec: Yield compute dynamic 10-year mean)
  if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
    if historical_avg is None or pd.isna(historical_avg):
      return None
    try:
      v = float(historical_avg)
    except (TypeError, ValueError):
      return None
    if pd.isna(v):
      return None
    return (v, f"Bataan 10-Yr Avg Yield ({v:.2f} MT/ha)", "#616161")
  if opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline", "DA Target (4.50 MT/ha)", "DA Target", "DA Target Yield (4.50 MT/ha)", "DA Target Yield"):
    return (4.50, "DA Target Yield (4.50 MT/ha)", "#2E7D32")
  return None


def _benchmark_price_config(benchmark_option, historical_avg):
  """Return (y_value, label, color) for price benchmark or None — legacy single-line helper.

  For "Presyo sa Merkado" / "3-Year/Quarter Rolling Market Average" this helper is NOT used for price;
  the multi-line rolling logic is handled directly in _apply_benchmarks_to_fig.
  Kept for backwards-compat with single-line callers.
  """
  opt = str(benchmark_option).strip() if benchmark_option is not None else ""
  if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
    if historical_avg is None or pd.isna(historical_avg):
      return None
    try:
      v = float(historical_avg)
    except (TypeError, ValueError):
      return None
    if pd.isna(v):
      return None
    return (v, f"Bataan 10-Yr Avg Regular Price (\u20B1{v:.2f}/kg)", "#616161")
  if opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline", "NFA Floor Price (₱19.00/kg)", "NFA Floor Price", "NFA Procurement Floor Price (₱19.00/kg)", "NFA Procurement Floor Price"):
    return (19.00, "NFA Procurement Floor Price (\u20B119.00/kg)", "#EF4444")
  return None


def _normalize_benchmarks(benchmark_option):
  """Normalize benchmark_option (str or list/set) to a set of strings.

  Supports Tagalog refactor:
  - "Presyo sa Merkado" / "Target ng Gobyerno" / "Wala"
  - legacy: "3-Year/Quarter Rolling Market Average" / "NFA / DA Policy Baseline" / "Itago (None)" / "10-Year Historical Average"
  - list/set for multi-select (kept for compat)
  Returns empty set for "Wala" / "Itago (None)".
  """
  if benchmark_option is None:
    return set()
  if isinstance(benchmark_option, (list, set, tuple)):
    return {str(o).strip() for o in benchmark_option if str(o).strip() and str(o).strip() not in ("Itago (None)", "Wala")}
  s = str(benchmark_option).strip()
  if not s or s in ("Itago (None)", "Wala"):
    return set()
  return {s}


def _apply_benchmarks_to_fig(fig, df, chart_type, benchmark_options, provincial_df=None):
  """Apply 0..N thin-dotted benchmark hlines per Refactored spec (Tagalog + legacy).

  Spec Tagalog:
  - "Presyo sa Merkado" (3-Year/Quarter Rolling Market Average, Inflation-Aware):
      Yield: 10-year mean of quarterly_yield_mt_per_ha (dynamic)
      Price: 3-Year Rolling Average = last 12 quarterly records (tail 12) for BOTH varieties -> two dotted lines
  - "Target ng Gobyerno" (NFA / DA Policy Baseline):
      Yield: DA Target 4.50 MT/ha
      Price: Regular 19.00 + Fancy Commercial Target 23.75 (19*1.25) -> two dotted lines
  - "Wala" / "Itago (None)": no lines
  All benchmark lines use line_dash="dot", line_width=1.2, opacity=0.6.
  """
  opts = _normalize_benchmarks(benchmark_options)
  if not opts:
    return fig
  src_df = provincial_df if provincial_df is not None and chart_type in ("yield", "price") else df
  if src_df is None:
    src_df = df
  for opt in opts:
    try:
      # --- Yield ---
      if chart_type == "yield":
        if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
          _col = "quarterly_yield_mt_per_ha"
          _col = _col if src_df is not None and _col in src_df.columns else _pick_column(src_df, ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha"])
          hist_avg = None
          if _col and src_df is not None and _col in src_df.columns:
            hist_avg = pd.to_numeric(src_df[_col], errors="coerce").dropna().mean()
            if pd.isna(hist_avg):
              hist_avg = None
          cfg = _benchmark_yield_config(opt, hist_avg)
          if cfg is not None:
            y_val, label, color = cfg
            pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
            fig = _add_benchmark_ref_line(fig, y_val, label, line_color=color, annotation_position=pos)
        elif opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline"):
          cfg = _benchmark_yield_config(opt, None)
          if cfg is not None:
            y_val, label, color = cfg
            pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
            fig = _add_benchmark_ref_line(fig, y_val, label, line_color=color, annotation_position=pos)
        elif opt in ("DA Target (4.50 MT/ha)", "DA Target", "DA Target Yield (4.50 MT/ha)"):
          cfg = _benchmark_yield_config(opt, None)
          if cfg is not None:
            y_val, label, color = cfg
            pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
            fig = _add_benchmark_ref_line(fig, y_val, label, line_color=color, annotation_position=pos)
        continue

      # --- Price ---
      if chart_type == "price":
        if opt in ("Presyo sa Merkado", "3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
          # Inflation-aware: tail(12) rolling for both varieties
          rolling_regular_avg = None
          rolling_fancy_avg = None
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
          # Plot both as thin dotted (spec: thin dotted reference lines)
          if rolling_regular_avg is not None and not pd.isna(rolling_regular_avg):
            try:
              v = float(rolling_regular_avg)
              label = f"Regular 3-Yr Rolling Avg (\u20B1{v:.2f}/kg)"
              pos = "top left" if fig.layout.shapes is None or len(fig.layout.shapes) == 0 else "bottom left"
              fig = _add_benchmark_ref_line(fig, v, label, line_color="#616161", annotation_position=pos)
            except Exception:
              pass
          if rolling_fancy_avg is not None and not pd.isna(rolling_fancy_avg):
            try:
              v = float(rolling_fancy_avg)
              label = f"Fancy 3-Yr Rolling Avg (\u20B1{v:.2f}/kg)"
              pos = "bottom left" if fig.layout.shapes is None or len(fig.layout.shapes) == 1 else "top left"
              fig = _add_benchmark_ref_line(fig, v, label, line_color="#78909C", annotation_position=pos)
            except Exception:
              pass
          if rolling_regular_avg is None and rolling_fancy_avg is None:
            pass
        elif opt in ("Target ng Gobyerno", "NFA / DA Policy Baseline"):
          # Regular NFA floor 19.00 (#EF4444 spec example) + Fancy commercial target 23.75 (19*1.25)
          fig = _add_benchmark_ref_line(fig, 19.00, "NFA Floor Price (\u20B119.00/kg)", line_color="#EF4444", annotation_position="bottom left")
          fig = _add_benchmark_ref_line(fig, 23.75, "Fancy Commercial Target (\u20B123.75/kg)", line_color="#F59E0B", annotation_position="top left")
        elif opt in ("NFA Floor Price (₱19.00/kg)", "NFA Floor Price", "NFA Procurement Floor Price (₱19.00/kg)"):
          fig = _add_benchmark_ref_line(fig, 19.00, "NFA Floor Price (\u20B119.00/kg)", line_color="#EF4444", annotation_position="bottom left")
        elif opt == "DA Target (4.50 MT/ha)":
          pass
        continue
    except Exception:
      continue
  return fig


# ------------------------------------------------------------------
# KPI SUBTEXT HELPERS — dynamic per Year Range / Period / Municipality
# ------------------------------------------------------------------
def _period_suffix(period: str) -> str:
  """Map PERIOD dropdown value to KPI subtext suffix.

  ANNUAL -> ""
  SEMESTER 1/2 -> " • Sem 1" / " • Sem 2"
  QUARTER 1-4 -> " • Q1" .. " • Q4"
  Legacy QUARTERLY/MONTHLY are also handled for backward compat.
  """
  if not period:
    return ""
  p = str(period).strip().upper()
  if p == "ANNUAL":
    return ""
  if p in ("SEMESTER 1", "SEM 1"):
    return " \u2022 Sem 1"
  if p in ("SEMESTER 2", "SEM 2"):
    return " \u2022 Sem 2"
  if p == "QUARTER 1":
    return " \u2022 Q1"
  if p == "QUARTER 2":
    return " \u2022 Q2"
  if p == "QUARTER 3":
    return " \u2022 Q3"
  if p == "QUARTER 4":
    return " \u2022 Q4"
  # legacy
  if p == "QUARTERLY":
    return " \u2022 Quarterly"
  if p == "MONTHLY":
    return " \u2022 Monthly"
  return ""


def _format_signed(num, suffix="", decimals=0):
  """Format number with explicit + sign for non-negative values."""
  try:
    n = float(num)
  except Exception:
    return f"0{suffix}"
  sign = "+" if n >= 0 else ""
  return f"{sign}{n:,.{decimals}f}{suffix}"


def _kpi_subtext_total_production(start_year: int, end_year: int, period: str, muni_name: str, has_data: bool = True) -> str:
  """Dynamic subtext for Total Production.

  Single year: "Total for 2025" / "Sum for Hermosa (2025)" (+ period suffix)
  Multi-year:  "Sum across 2015 \u2013 2025" (+ muni + period suffix)
  No-data fallback: original static string kept by caller.
  """
  suffix = _period_suffix(period)
  muni_is_all = (not muni_name or muni_name == "All Municipalities")
  if start_year == end_year:
    y = end_year
    if muni_is_all:
      base = f"Total for {y}"
    else:
      base = f"Sum for {muni_name} ({y})"
    return f"{base}{suffix}" if suffix else base
  else:
    base = f"Sum across {start_year} \u2013 {end_year}"
    if not muni_is_all:
      base += f" \u2022 {muni_name}"
    return f"{base}{suffix}" if suffix else base


def _kpi_subtext_yield_or_area(
  *,
  start_year: int,
  end_year: int,
  period: str,
  muni_name: str,
  delta: float | None,
  prev_year: int | None,
  has_prev: bool,
  unit: str,
  decimals: int = 2,
) -> str:
  """Dynamic subtext for Average Yield / Harvested Area.

  Single-year + has_prev: "+0.12 MT/ha vs 2024" (+ period suffix)
  Single-year fallback:  "Data as of 2025" (+ period suffix + muni)
  Multi-year:       "Average across 2015 \u2013 2025" (+ muni + period suffix)
  """
  suffix = _period_suffix(period)
  muni_is_all = (not muni_name or muni_name == "All Municipalities")
  muni_suffix = "" if muni_is_all else f" \u2022 {muni_name}"

  if start_year == end_year:
    if has_prev and delta is not None and prev_year is not None:
      try:
        d = float(delta)
        if pd.isna(d):
          raise ValueError
      except Exception:
        has_prev = False
      else:
        sign = "+" if d >= 0 else ""
        # keep decimals/unit as requested, e.g. " MT/ha" or " ha"
        delta_str = f"{sign}{d:,.{decimals}f}{unit} vs {prev_year}"
        return f"{delta_str}{suffix}" if suffix else delta_str
    # fallback: no prev data
    base = f"Data as of {end_year}"
    # For single-year fallback, include muni scope if specific
    if not muni_is_all:
      base += f" \u2022 {muni_name}"
    return f"{base}{suffix}" if suffix else base
  else:
    base = f"Average across {start_year} \u2013 {end_year}"
    if not muni_is_all:
      base += f" \u2022 {muni_name}"
    return f"{base}{suffix}" if suffix else base


def _filter_df_by_period(df: pd.DataFrame, period: str) -> pd.DataFrame:
  """Filter DataFrame rows to the selected PERIOD slice.

  ANNUAL -> no filtering
  SEMESTER 1 -> months 1-6, SEMESTER 2 -> months 7-12
  QUARTER 1-4 -> quarter == N
  Legacy / unknown -> no filtering (ANNUAL behaviour).
  """
  if df is None or df.empty or "date" not in df.columns:
    return df
  p = str(period).strip().upper() if period else "ANNUAL"
  try:
    d = pd.to_datetime(df["date"], errors="coerce")
    months = d.dt.month
    quarters = d.dt.quarter
  except Exception:
    return df
  if p in ("SEMESTER 1", "SEM 1"):
    return df[months.between(1, 6)]
  if p in ("SEMESTER 2", "SEM 2"):
    return df[months.between(7, 12)]
  if p == "QUARTER 1":
    return df[quarters == 1]
  if p == "QUARTER 2":
    return df[quarters == 2]
  if p == "QUARTER 3":
    return df[quarters == 3]
  if p == "QUARTER 4":
    return df[quarters == 4]
  return df


def _align_forecast_arrays(fancy_arr, regular_arr):
  """Align two differently-sized forecast arrays onto a shared index.

  Both arrays are wrapped as pd.Series and merged with an OUTER join on
  their positional index. The shorter array (e.g. 3-month Regular) is
  right-padded with NaN up to the length of the longer array (6-month
  Fancy), so months 4-6 become NaN instead of raising a length mismatch.

  Returns:
    (fancy_series, regular_series): two pd.Series of identical length.
  """
  fancy_s = pd.Series(
    list(fancy_arr) if fancy_arr is not None else [],
    name="fancy_palay_price",
  )
  regular_s = pd.Series(
    list(regular_arr) if regular_arr is not None else [],
    name="other_variety_price",
  )

  # Outer join on the default RangeIndex -> both series get max length,
  # missing trailing months are NaN.
  aligned = pd.concat([fancy_s, regular_s], axis=1, join="outer").sort_index()

  return aligned["fancy_palay_price"], aligned["other_variety_price"]


def _group_by_period(df, period="ANNUAL", value_cols=None):
  """Group DataFrame by the specified period and return aggregated data with period labels.

  Supports the updated PERIOD options: ANNUAL, SEMESTER 1/2, QUARTER 1-4
  plus legacy QUARTERLY/MONTHLY for backward compat.
  Semester/Quarter filters slice the DataFrame to that slice before grouping
  by year so charts stay meaningful when a narrow period is selected.

  Args:
    df: DataFrame with 'date' column
    period: one of the PERIOD dropdown values
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
  # semester derived from month (1-6 = Sem 1, 7-12 = Sem 2)
  temp["semester"] = np.where(temp["month"] <= 6, 1, 2)

  p = str(period).strip().upper() if period else "ANNUAL"

  # Narrow SEMESTER / QUARTER slices -> filter then group by year
  if p in ("SEMESTER 1", "SEM 1"):
    temp = temp[temp["semester"] == 1]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + " Sem 1"
    return grouped
  if p in ("SEMESTER 2", "SEM 2"):
    temp = temp[temp["semester"] == 2]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + " Sem 2"
    return grouped
  if p == "QUARTER 1":
    temp = temp[temp["quarter"] == 1]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q1"
    return grouped
  if p == "QUARTER 2":
    temp = temp[temp["quarter"] == 2]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q2"
    return grouped
  if p == "QUARTER 3":
    temp = temp[temp["quarter"] == 3]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q3"
    return grouped
  if p == "QUARTER 4":
    temp = temp[temp["quarter"] == 4]
    if temp.empty:
      return pd.DataFrame(columns=["period_label"] + value_cols)
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q4"
    return grouped

  if p == "ANNUAL":
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str)
    return grouped
  elif p == "QUARTERLY":
    grouped = temp.groupby(["year", "quarter"]).mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str) + "-Q" + grouped["quarter"].astype(str)
    return grouped
  elif p == "MONTHLY":
    grouped = temp.groupby(["year", "month"]).mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped.apply(lambda r: f"{r['month_name']} {r['year']}", axis=1)
    return grouped
  else:
    grouped = temp.groupby("year").mean(numeric_only=True).reset_index()
    grouped["period_label"] = grouped["year"].astype(str)
    return grouped


def _price_historical_chart(df, period="ANNUAL", benchmark_option="Itago (None)"):
  """Historical price chart grouped by the selected period with peak annotations.

  The period value now comes from the updated dropdown:
  ANNUAL / SEMESTER 1/2 / QUARTER 1-4 (legacy QUARTERLY/MONTHLY still supported).

  benchmark_option controls the optional horizontal reference line:
  - "10-Year Historical Average" -> mean of other_variety_price
  - "NFA / DA Policy Baseline" -> Php 19.00/kg NFA floor
  - "Itago (None)" -> no line
  """
  value_cols = []
  if "fancy_palay_price" in df.columns:
    value_cols.append("fancy_palay_price")
  if "other_variety_price" in df.columns:
    value_cols.append("other_variety_price")
  if not value_cols:
    return go.Figure()

  grouped = _group_by_period(df, period, value_cols)
  if grouped.empty:
    return go.Figure()

  _p = str(period).strip().upper() if period else "ANNUAL"
  if _p == "ANNUAL":
    xaxis_title = "Year"
  elif _p in ("SEMESTER 1", "SEM 1", "SEMESTER 2", "SEM 2"):
    xaxis_title = "Year (Semester)"
  elif _p in ("QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"):
    xaxis_title = "Year"
  elif _p == "QUARTERLY":
    xaxis_title = "Quarter"
  elif _p == "MONTHLY":
    xaxis_title = "Month"
  else:
    xaxis_title = "Year"
  fig = go.Figure()

  if "fancy_palay_price" in grouped.columns:
    fig.add_trace(go.Scatter(
      x=grouped["period_label"], y=grouped["fancy_palay_price"],
      mode="lines+markers", name="Fancy Palay",
      line=dict(color="#89a143", width=2.5), marker=dict(size=6),
    ))
    peak_idx = grouped["fancy_palay_price"].idxmax()
    if pd.notna(peak_idx):
      peak_row = grouped.loc[peak_idx]
      fig.add_annotation(
        x=peak_row["period_label"], y=peak_row["fancy_palay_price"],
        text=f"▲ Peak: ₱{peak_row['fancy_palay_price']:.2f}/kg",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#16A34A",
        ax=0, ay=-50,
        font=dict(size=10, color="#15803D", weight="bold"),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#16A34A", borderwidth=1, borderpad=4,
      )

  if "other_variety_price" in grouped.columns:
    fig.add_trace(go.Scatter(
      x=grouped["period_label"], y=grouped["other_variety_price"],
      mode="lines+markers", name="Regular Palay",
      line=dict(color="#d1a019", width=2.5), marker=dict(size=6),
    ))
    peak_idx = grouped["other_variety_price"].idxmax()
    if pd.notna(peak_idx):
      peak_row = grouped.loc[peak_idx]
      fig.add_annotation(
        x=peak_row["period_label"], y=peak_row["other_variety_price"],
        text=f"▲ Peak: ₱{peak_row['other_variety_price']:.2f}/kg",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#6D28D9",
        ax=0, ay=50,
        font=dict(size=10, color="#6D28D9", weight="bold"),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#6D28D9", borderwidth=1, borderpad=4,
      )

  # --- Benchmark / Reference line(s) — supports multi-select (Yield/Price split) ---
  fig = _apply_benchmarks_to_fig(fig, df, "price", benchmark_option)

  fig.update_layout(
    height=370, margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title=xaxis_title, yaxis_title="₱/kg",
    legend=dict(orientation="h", yanchor="bottom", y=-0.55, xanchor="center", x=0.5,
          font=dict(size=11, family="Poppins")),
    plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
    xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
  )
  return fig


def _price_forecast_chart(provincial_df, fancy_forecast, regular_forecast, benchmark_option="Itago (None)"):
  """Price forecast line chart (next 6 months) for Fancy & Regular.

  Fancy and Regular arrays are aligned via outer-join Series so they always
  share the same x axis; a missing month is NaN and is drawn as a gap
  (connectgaps=False) instead of breaking the layout.

  IMPORTANT: the x-axis is anchored to the LAST HISTORICAL DATE in the
  provincial data (where the forecast actually starts), NOT to the system
  clock. Using pd.Timestamp.today() would shift the whole line to e.g.
  September instead of January when the model runs on stale historical data.

  benchmark_option controls the optional horizontal reference line:
  Forecast View uses DA Target / NFA floor for Policy Baseline and
  historical average for "10-Year Historical Average".
  """
  fig = go.Figure()
  try:
    fancy_fc, regular_fc = _align_forecast_arrays(fancy_forecast, regular_forecast)
    if fancy_fc.dropna().empty and regular_fc.dropna().empty:
      return fig
    n = len(fancy_fc)

    # --- Baseline Alignment: strictly 1 month after last historical date ---
    # e.g. last Jan 2026 -> Feb, Mar, Apr, May, Jun, Jul — do NOT shift to Aug
    hist_dates = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
    if hist_dates.empty:
      raise ValueError("No valid historical dates in provincial data.")
    last_hist_date = hist_dates.max()
    fc_months = pd.date_range(
      start=last_hist_date + pd.DateOffset(months=1),
      periods=n, freq="MS"
    )
    # ------------------------------------------------------------

    fig.add_trace(go.Scatter(
      x=fc_months, y=fancy_fc.values,
      mode="lines+markers", name="Fancy Forecast",
      line=dict(color="#10B981", width=2.5, dash="dash"),
      marker=dict(size=6, symbol="diamond"),
      connectgaps=False,
    ))
    fig.add_trace(go.Scatter(
      x=fc_months, y=regular_fc.values,
      mode="lines+markers", name="Regular Forecast",
      line=dict(color="#F5CD63", width=2.5, dash="dash"),
      marker=dict(size=6, symbol="diamond"),
      connectgaps=False,
    ))
    # --- Benchmark / Reference line(s) — supports multi-select (Forecast View) ---
    fig = _apply_benchmarks_to_fig(fig, provincial_df, "price", benchmark_option)

    fig.update_layout(
      height=370, margin=dict(l=10, r=10, t=10, b=10),
      xaxis_title=None, yaxis_title="₱/kg",
      legend=dict(orientation="h", yanchor="bottom", y=-0.55, xanchor="center", x=0.5,
            font=dict(size=11, family="Poppins")),
      plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
      xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
    )
  except Exception:
    return go.Figure()
  return fig


def _yield_historical_chart(df, period="ANNUAL", benchmark_option="Itago (None)"):
  """Historical yield chart grouped by the selected period with peak annotation.

  benchmark_option controls the optional horizontal reference line:
  - "10-Year Historical Average" -> mean of quarterly_yield_mt_per_ha
  - "NFA / DA Policy Baseline" -> 4.50 MT/ha DA Target
  - "Itago (None)" -> no line
  """
  grouped = _group_by_period(df, period, ["quarterly_yield_mt_per_ha"])
  if grouped.empty or "quarterly_yield_mt_per_ha" not in grouped.columns:
    return go.Figure()

  _p = str(period).strip().upper() if period else "ANNUAL"
  if _p == "ANNUAL":
    xaxis_title = "Year"
  elif _p in ("SEMESTER 1", "SEM 1", "SEMESTER 2", "SEM 2"):
    xaxis_title = "Year (Semester)"
  elif _p in ("QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"):
    xaxis_title = "Year"
  elif _p == "QUARTERLY":
    xaxis_title = "Quarter"
  elif _p == "MONTHLY":
    xaxis_title = "Month"
  else:
    xaxis_title = "Year"
  fig = go.Figure()
  fig.add_trace(go.Scatter(
    x=grouped["period_label"], y=grouped["quarterly_yield_mt_per_ha"],
    mode="lines+markers", name="Historical Yield",
    line=dict(color="#7C3AED", width=3), marker=dict(size=7),
  ))

  peak_idx = grouped["quarterly_yield_mt_per_ha"].idxmax()
  if pd.notna(peak_idx):
    peak_row = grouped.loc[peak_idx]
    fig.add_annotation(
      x=peak_row["period_label"], y=peak_row["quarterly_yield_mt_per_ha"],
      text=f"▲ Peak: {peak_row['quarterly_yield_mt_per_ha']:.2f} MT/ha",
      showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
      ax=0, ay=-45,
      font=dict(size=10, color="#C2410C", weight="bold"),
      bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
    )

  # --- Benchmark / Reference line(s) — supports multi-select ---
  fig = _apply_benchmarks_to_fig(fig, df, "yield", benchmark_option)

  fig.update_layout(
    height=350, margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title=xaxis_title, yaxis_title="MT/ha",
    legend=dict(orientation="h", yanchor="bottom", y=-0.40, xanchor="center", x=0.5,
          font=dict(size=11, family="Poppins")),
    plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
    xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
  )
  return fig


def _yield_forecast_chart(provincial_df, yield_forecast, benchmark_option="Itago (None)"):
  """Yield forecast line chart (next forecast quarters) with peak annotation.

  Quarter axis is strictly 1 quarter after last historical date (baseline).

  benchmark_option controls the optional horizontal reference line
  (Forecast View: DA Target 4.50 MT/ha for Policy Baseline).
  """
  fig = go.Figure()
  try:
    fc_yield = list(yield_forecast) if yield_forecast is not None else []
    if not fc_yield:
      return fig

    hist_dates = pd.to_datetime(provincial_df["date"], errors="coerce").dropna()
    if hist_dates.empty:
      raise ValueError("No valid historical dates in provincial data.")
    last_hist_date = hist_dates.max()

    fc_quarters = pd.period_range(
      start=pd.Period(last_hist_date, freq="Q") + 1,
      periods=len(fc_yield), freq="Q"
    )
    fc_labels = [f"Q{q.quarter} {q.year}" for q in fc_quarters]
    fig.add_trace(go.Scatter(
      x=fc_labels, y=fc_yield,
      mode="lines+markers", name="Forecast Yield",
      line=dict(color="#2E7D32", width=3, dash="dash"), marker=dict(size=8, symbol="diamond"),
    ))
    peak_val = _safe_max(fc_yield)
    peak_idx = fc_yield.index(peak_val) if peak_val in fc_yield else -1
    if 0 <= peak_idx < len(fc_labels):
      fig.add_annotation(
        x=fc_labels[peak_idx], y=peak_val,
        text=f"▲ Peak: {peak_val:.2f} MT/ha",
        showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2, arrowcolor="#F57C00",
        ax=0, ay=-45,
        font=dict(size=10, color="#C2410C", weight="bold"),
        bgcolor="rgba(255,255,255,0.9)", bordercolor="#F57C00", borderwidth=1, borderpad=4,
      )
    # --- Benchmark / Reference line(s) — supports multi-select (Forecast View) ---
    fig = _apply_benchmarks_to_fig(fig, provincial_df, "yield", benchmark_option)

    fig.update_layout(
      height=350, margin=dict(l=10, r=10, t=10, b=10),
      xaxis_title=None, yaxis_title="MT/ha",
      legend=dict(orientation="h", yanchor="bottom", y=-0.40, xanchor="center", x=0.5,
            font=dict(size=11, family="Poppins")),
      plot_bgcolor="white", paper_bgcolor="white", hovermode="x unified",
      xaxis=dict(gridcolor="#F3F4F6", showgrid=True), yaxis=dict(gridcolor="#F3F4F6", showgrid=True),
    )
  except Exception:
    return go.Figure()
  return fig


def _yield_summary_card(yield_forecast):
  """Yield Forecast Summary card (Avg / Peak / Low)."""
  try:
    yield_fc = list(yield_forecast) if yield_forecast is not None else []
  except Exception:
    yield_fc = []
  if not yield_fc:
    st.info("No data available for yield forecast.")
    return
  avg_y = _safe_mean(yield_fc)
  max_y = _safe_max(yield_fc)
  min_y = _safe_min(yield_fc)
  st.markdown(f"""
  <div style="background: linear-gradient(135deg, #E8F5E9, #F1F8E9); padding:1.2rem;
        border-radius:16px; border-left:6px solid #2E7D32;
        box-shadow:0 6px 18px rgba(0,0,0,0.08); font-size:0.95rem; line-height:1.8;">
    <div style="font-size:1rem; font-weight:700; color:#1B5E20; margin-bottom:0.5rem;">
      <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Yield Forecast Summary
    </div>
    <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_up</i> Average: <b>{avg_y:.2f} MT/ha</b></div>
    <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">emoji_events</i> Peak: <b>{max_y:.2f} MT/ha</b></div>
    <div><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">trending_down</i> Low: <b>{min_y:.2f} MT/ha</b></div>
    <hr style="border:none; border-top:1px solid #C8E6C9; margin:0.6rem 0;">
    <div style="font-size:0.85rem; color:#2E7D32;">Based on next {len(yield_fc)} forecast quarters</div>
  </div>
  """, unsafe_allow_html=True)


def _render_municipal_crop_cycle_chart(df: pd.DataFrame, rice_type: str,
                    classification: str,
                    selected_municipalities: list):
  """
  Renders the actual 3-month municipal price forecast (Altair).

  Plots the real forecast values (Month 1-3 from ``df_municipal_forecasts``)
  for the user's Rice Type / Classification / Crop Cycle selection as a
  clustered bar chart: bars are grouped by forecast month on the X-axis,
  with each municipality offset side-by-side via the ``xOffset`` channel.
  The Y-axis uses ``alt.Scale(zero=False)`` with a tight domain (clamped
  around the min/max prices in the current selection) so small price
  changes in cents are visibly distinct. The X-axis is ordered by the
  actual forecast month labels contained in the uploaded dataset.
  """
  if df is None or df.empty:
    st.error(" Municipal forecast dataset is empty or unreadable.")
    return

  df = df.copy()
  # Standardize column headers to lowercase for safety
  df.columns = [str(col).lower() for col in df.columns]

  # 1. Municipality multi-select filter (empty selection = all municipalities)
  if selected_municipalities:
    selected_munis_lc = [str(m).lower() for m in selected_municipalities]
    df = df[df["municipality"].str.lower().isin(selected_munis_lc)]

  # 2. Interactive Crop Cycle Selector Dropdown
  selected_cycle = st.selectbox(
    "Piliin ang Agrikultural na Siklo (Crop Cycle) na Nais Tingnan:",
    [":material/wb_sunny: Dry Season Crop Cycle", ":material/water_drop: Wet Season Crop Cycle"],
    key=f"crop_cycle_picker_{rice_type}_{classification}",
  )

  st.write("---")

  # 3. Match the user's filters to the forecast row (e.g. hybridpremium_dry)
  base_key = f"{rice_type.lower()}{classification.lower()}".replace(" ", "")
  suffix = "_dry" if "Dry" in selected_cycle else "_wet"
  target_key = f"{base_key}{suffix}"

  type_col = "rice type & season"
  sub = df[df[type_col].str.lower() == target_key] if type_col in df.columns else pd.DataFrame()
  if sub.empty:
    st.warning(f"No forecast rows for '{target_key}' in the uploaded file.")
    return

  # 4. Dynamic forecast month labels + forecast year (from the uploaded file)
  label_map = {}
  for key, n in (("forecast_month_1_label", 1),
          ("forecast_month_2_label", 2),
          ("forecast_month_3_label", 3)):
    if key in sub.columns and sub[key].notna().any():
      label_map[f"month {n}"] = str(sub[key].iloc[0])
    else:
      label_map[f"month {n}"] = f"Month {n}"

  forecast_month_labels = [label_map[f"month {n}"] for n in range(1, 4)]
  forecast_year = next((int(str(label).split()[-1])
             for label in forecast_month_labels
             if str(label).split()[-1].isdigit()), 2026)

  # 5. Narrative per crop cycle
  if "Dry" in selected_cycle:
    st.subheader(
      f":material/agriculture: Dry Season Forecast: Mid to Late Harvesting Phase ({forecast_year})"
    )
    st.caption(
      f" This tracks the price trend for palay planted late {forecast_year - 1}. "
      f"Peak harvesting happens from January to March {forecast_year}, "
      f"winding down completely by May {forecast_year}."
    )
  else:
    st.subheader(
      f":material/agriculture: Wet Season Forecast: Overlapping Planting & Early Monsoon Harvest ({forecast_year})"
    )
    st.caption(
      f" This tracks fields undergoing land preparation or planting from January to May {forecast_year}, "
      f"transitioning into wet season crop growth and heavy monsoon harvests "
      f"from June to December {forecast_year}."
    )

  # 6. Long-form data: one point per (forecast month, municipality)
  plot_df = (
    sub.melt(
      id_vars=["municipality"],
      value_vars=["month 1", "month 2", "month 3"],
      var_name="month_key",
      value_name="price",
    )
    .assign(forecast_month=lambda d: d["month_key"].map(label_map))
    .groupby(["forecast_month", "municipality"], as_index=False)["price"]
    .mean()
    .dropna(subset=["price"])
  )
  if plot_df.empty:
    st.info("No data available for the selected filters.")
    return

  # 7. Altair clustered bar chart — zoomed Y-axis (zero=False) + tight
  #  domain around the min/max prices in the active selection so that
  #  changes in cents are visibly distinct.
  price_min = plot_df["price"].min()
  price_max = plot_df["price"].max()
  price_pad = max((price_max - price_min) * 0.08, 0.05)
  y_domain = [price_min - price_pad, price_max + price_pad]

  chart = (
    alt.Chart(plot_df)
    .mark_bar()
    .encode(
      x=alt.X("forecast_month:N", title="Forecast Month",
          sort=forecast_month_labels),
      xOffset="municipality:N",
      y=alt.Y("price:Q", title="Price (₱/kg)",
          scale=alt.Scale(zero=False, domain=y_domain)),
      color=alt.Color("municipality:N",
              legend=alt.Legend(title="Municipality")),
      tooltip=[
        "forecast_month:N",
        "municipality:N",
        alt.Tooltip("price:Q", title="Price (₱/kg)", format=".2f"),
      ],
    )
    .properties(height=400,
          title=f"{rice_type} {classification} — {selected_cycle}")
  )
  st.altair_chart(chart, use_container_width=True)


def _insights_narrative(prov_year_df, quarterly_data, selected_muni_name,
            fancy_forecast=None, regular_forecast=None):
  """Dynamic Insights Narrative / Storytelling Mode."""
  with st.expander(":material/edit_note: Insights Narrative — Auto-generated market summary", expanded=True):
    try:
      hist_fancy = _safe_column(prov_year_df, "fancy_palay_price")
      hist_regular = _safe_column(prov_year_df, "other_variety_price")

      next_fancy = _safe_index(fancy_forecast, 0)
      next_regular = _safe_index(regular_forecast, 0)

      yield_qoq = 0
      if quarterly_data is not None and not quarterly_data.empty and len(quarterly_data) >= 2:
        q_current = quarterly_data["quarterly_yield_mt_per_ha"].iloc[-1]
        q_previous = quarterly_data["quarterly_yield_mt_per_ha"].iloc[-2]
        if (
          pd.notna(q_current) and pd.notna(q_previous) and q_previous != 0
        ):
          yield_qoq = ((q_current - q_previous) / q_previous) * 100

      avg_fancy = hist_fancy.mean() if not hist_fancy.empty else 0
      avg_regular = hist_regular.mean() if not hist_regular.empty else 0
      fancy_fc_vs_hist = _pct_change(next_fancy, avg_fancy) or 0.0
      regular_fc_vs_hist = _pct_change(next_regular, avg_regular) or 0.0

      prod_total = prov_year_df["production_total"].sum() if "production_total" in prov_year_df.columns else 0

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
        <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">analytics</i> Quarterly Market Summary
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
          <i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">lightbulb</i> This narrative is auto-generated for <strong>{selected_muni_name}</strong>
          across the selected period. Adjust filters to update insights.
        </small>
      </div>
    </div>
    """, unsafe_allow_html=True)


def overview_page():
  """
  Renders an accessible, farmer-centric agricultural dashboard for Bataan.
  Supports multi-year selections, 'All' municipality views, and Ecosystem toggle filters.
  """
  # --- PalaySense full-screen loader (assets/logo.png) covering data fetch ---
  # Uses blocking placeholder so navigation + data load are both covered; spinner from
  # Dashboard_Ready is now disabled (show_spinner=False) to avoid duplicate tiny spinner.
  import time as _ov_time
  from components.loading_screen import get_global_loading_html, _get_logo_base64
  _ov_loader = st.empty()
  _ov_loader.markdown(
      get_global_loading_html(
          message="Loading Overview...",
          submessage="Fetching provincial & municipal data — please wait",
          logo_base64=_get_logo_base64(),
          duration_ms=3000,
      ),
      unsafe_allow_html=True,
  )
  _ov_t0 = _ov_time.time()
  # Fetch ALL datasets inside the page via the single data-layer entry point.
  # No module-level globals are read here.
  dr = reload_dashboard_data()
  # Ensure loader visible at least 0.75s for perceived feedback
  _ov_elapsed = _ov_time.time() - _ov_t0
  if _ov_elapsed < 0.75:
      _ov_time.sleep(0.75 - _ov_elapsed)
  _ov_loader.empty()
  provincial_df = dr.provincial_df.copy()
  _prod_muni = getattr(dr, "municipal_production_df", None)
  municipality_df = (
    _prod_muni.copy()
    if _prod_muni is not None and not getattr(_prod_muni, "empty", True)
    else dr.municipality_df.copy()
  )
  df_municipal_forecasts = dr.df_municipal_forecasts.copy()
  forecast_3months_fancy = list(dr.forecast_3months_fancy)
  forecast_variety_3months = list(dr.forecast_variety_3months)
  forecast_quarterly_yield = list(dr.forecast_quarterly_yield)

  # Initialize display DataFrames to prevent UnboundLocalError
  df_dry_display = pd.DataFrame()
  df_wet_display = pd.DataFrame()

  # ========================================================
  # DATA PROCESSING & TEMPORAL MAPPING
  # ========================================================
  provincial_df = provincial_df.copy()
  provincial_df["date"] = pd.to_datetime(provincial_df["date"], errors="coerce")
  provincial_df = provincial_df.dropna(subset=["date"]).copy()
  provincial_sorted = provincial_df.sort_values("date").copy()

  df = provincial_sorted.copy()
  df["year"] = df["date"].dt.year
  df["quarter"] = df["date"].dt.quarter

  latest_year = df["year"].max()
  provincial_latest = df[df["year"] == latest_year].copy().sort_values("date")
  latest = provincial_latest.iloc[-1] if not provincial_latest.empty else None

  # Quick backup conversion for municipality data
  muni = municipality_df.copy()
  if muni.empty:
    muni = pd.DataFrame(columns=["date", "year"])
  if "date" not in muni.columns:
    if "year" in muni.columns:
      muni["date"] = pd.to_datetime(muni["year"].astype(str) + "-06-15")
    else:
      muni["date"] = pd.Timestamp("2024-01-01")
  else:
    muni["date"] = pd.to_datetime(muni["date"], errors="coerce")
  muni["year"] = muni["date"].dt.year


  # =========================
  # HISTORICAL QUARTERLY DATA
  # =========================
  _yield_col = _pick_column(
    df,
    ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha", "Yield"],
  )
  if _yield_col is not None:
    quarterly_df = (
      df.groupby(["year", "quarter"])[_yield_col]
      .mean()
      .reset_index()
    )
  else:
    quarterly_df = pd.DataFrame(columns=["year", "quarter", "quarterly_yield_mt_per_ha"])

  quarterly_df["date_q"] = pd.PeriodIndex(
    quarterly_df["year"].astype(str) + "Q" + quarterly_df["quarter"].astype(str),
    freq="Q"
  ).to_timestamp()

  quarterly_df["quarter_label"] = (
      "Q" + quarterly_df["quarter"].astype(str) +
      " " + quarterly_df["year"].astype(str)
  )

  quarterly_df["Type"] = "Historical"
  quarterly_df = quarterly_df.sort_values("date_q")

  # =========================
  # FORECAST PREPARATION
  # =========================
  latest_q = quarterly_df.iloc[-1] if not quarterly_df.empty else None
  _fc_quarter_start = (
    pd.Period(latest_q["date_q"], freq="Q") + 1
    if latest_q is not None
    else pd.Period(pd.Timestamp.today(), freq="Q") + 1
  )
  forecast_quarters = pd.period_range(
    start=_fc_quarter_start,
    periods=4,
    freq="Q"
  )

  # Forecast reference year
  forecast_year1 = forecast_quarters[-1].year

  forecast_df = pd.DataFrame({
    "date_q": forecast_quarters.to_timestamp()
  })

  forecast_df["year"] = forecast_df["date_q"].dt.year
  forecast_df["quarter"] = forecast_df["date_q"].dt.quarter

  forecast_df["quarter_label"] = (
      "Q" + forecast_df["quarter"].astype(str) +
      " " + forecast_df["year"].astype(str)
  )

  _fc_yield_arr = list(forecast_quarterly_yield) if forecast_quarterly_yield is not None else []
  if len(_fc_yield_arr) == len(forecast_df):
    forecast_df["quarterly_yield_mt_per_ha"] = _fc_yield_arr
  else:
    forecast_df["quarterly_yield_mt_per_ha"] = [_fc_yield_arr[i] if i < len(_fc_yield_arr) else 0 for i in range(len(forecast_df))]
  forecast_df["Type"] = "Forecast"

  # ========================================================
  # TOP FILTER TOOLBAR
  # ========================================================
  st.markdown(
    """
    <style>
      div[data-testid="stColumn"] { margin-top: 0px !important; padding-top: 0px !important; padding-bottom: 0.2rem !important; }
      div[data-testid="stSelectbox"] { margin-top: 0px !important; padding-top: 0px !important; }
      div[data-testid="stSelectbox"] > div { border: none !important; background: transparent !important; box-shadow: none !important; }
      div[data-testid="stSelectbox"] div[role="combobox"] {
        border: 1px solid #1B5E20 !important;
        background-color: #FFFFFF !important;
        border-radius: 8px !important;
        box-shadow: none !important;
      }
    </style>
    """,
    unsafe_allow_html=True,
  )
  st.markdown('<div style="margin-top:0.55rem; margin-bottom:0.2rem;"></div>', unsafe_allow_html=True)
  available_years = sorted(list(df["year"].dropna().unique()), reverse=False)
  if not available_years:
    available_years = [2024]

  st.session_state.setdefault("overview_start_year", available_years[0])
  st.session_state.setdefault("overview_end_year", available_years[-1])
  st.session_state.setdefault("overview_period", "ANNUAL")
  # Migrate legacy PERIOD values (QUARTERLY/MONTHLY) to ANNUAL so the
  # selectbox options remain valid after the dropdown redesign.
  _valid_periods = ["ANNUAL", "SEMESTER 1", "SEMESTER 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"]
  if st.session_state.get("overview_period") not in _valid_periods:
    st.session_state["overview_period"] = "ANNUAL"
  st.session_state.setdefault("overview_selected_muni", "All Municipalities")

  filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4, gap="small")
  with filter_col1:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">YEAR RANGE</div>', unsafe_allow_html=True)
    selected_start_year = st.selectbox(
      "Start Year",
      options=available_years,
      key="overview_start_year",
      label_visibility="collapsed",
    )
  with filter_col2:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">TO</div>', unsafe_allow_html=True)
    selected_end_year = st.selectbox(
      "End Year",
      options=available_years,
      key="overview_end_year",
      label_visibility="collapsed",
    )
  with filter_col3:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">PERIOD</div>', unsafe_allow_html=True)
    selected_period = st.selectbox(
      "Period",
      options=["ANNUAL", "SEMESTER 1", "SEMESTER 2", "QUARTER 1", "QUARTER 2", "QUARTER 3", "QUARTER 4"],
      key="overview_period",
      label_visibility="collapsed",
    )
  with filter_col4:
    st.markdown('<div style="font-weight:700; color:#1B5E20; margin-bottom:0.1rem; line-height:1.1;">MUNICIPALITY</div>', unsafe_allow_html=True)
    _muni_label_col = _pick_column(muni, ["municipality", "Municipality", "Mun", "Area"])
    all_munis_options = (
      sorted(muni[_muni_label_col].dropna().unique())
      if _muni_label_col is not None
      else []
    )
    muni_options = ["All Municipalities"] + all_munis_options
    if st.session_state["overview_selected_muni"] not in muni_options:
      st.session_state["overview_selected_muni"] = "All Municipalities"
    selected_muni = st.selectbox(
      "Municipality",
      options=muni_options,
      key="overview_selected_muni",
      label_visibility="collapsed",
    )

  selected_years = list(range(selected_start_year, selected_end_year + 1))
  selected_munis = [selected_muni] if selected_muni != "All Municipalities" else all_munis_options
  selected_eco = "All Types"
  overview_muni_label = selected_muni

  # ========================================================
  # SIDEBAR: SECTION NAVIGATION — Style C Grouped, Farmer Minimal, Mobile Responsive
  # ========================================================
  section_options = [
    "Buong Dashboard",
    "Yield Forecast",
    "Price Forecast",
    "Mga Payo (Advisories)",
    "Municipal Forecast",
    "Price Insights",
    "Yield Insights",
    "Municipal Analysis",
    "Production Rankings",
    "Insights Narrative",
  ]
  # Grouped model for farmer comprehension — Tagalog where helpful, minimal
  QUICK_VIEW_GROUPS = [
    ("PANGKALAHATAN", [("Buong Dashboard", "dashboard")]),
    ("FORECAST", [("Yield Forecast", "query_stats"), ("Price Forecast", "payments"), ("Municipal Forecast", "location_on")]),
    ("ANALYTICS", [("Price Insights", "bar_chart"), ("Yield Insights", "eco"), ("Municipal Analysis", "analytics"), ("Production Rankings", "emoji_events")]),
    ("SUPORTA", [("Mga Payo (Advisories)", "lightbulb"), ("Insights Narrative", "auto_stories")]),
  ]
  st.session_state.setdefault("overview_section", "Buong Dashboard")
  with st.sidebar:
    st.markdown("""
    <style>
    /* Quick View — compact, no header, fits without scroll — left-aligned */
    .ov-qv-group { font-size:0.60rem !important; letter-spacing:0.6px !important; color:#A8C3B0 !important; margin:0.35rem 0 0.15rem 0 !important; font-weight:600 !important; text-align: left !important; }
    /* Tighten sidebar buttons to fit exactly — no scroll — left-aligned */
    section[data-testid="stSidebar"] .stButton > button {
      padding: 4px 8px 4px 10px !important; min-height: 32px !important; line-height:1.1 !important;
      font-size:0.78rem !important; gap: 6px !important; margin: 1px 0 !important;
      justify-content: flex-start !important; text-align: left !important; align-items: center !important;
    }
    section[data-testid="stSidebar"] .stButton > button > div { justify-content: flex-start !important; text-align: left !important; }
    section[data-testid="stSidebar"] .stButton > button p { text-align: left !important; width: 100% !important; }
    section[data-testid="stSidebar"] > div:first-child { padding-top: 0.4rem !important; gap: 2px !important; }
    section[data-testid="stSidebar"] hr.ps-side-divider { margin: 0.35rem 0 !important; }
    /* Mobile: hide desktop sidebar, show green pop-trigger in upper corner */
    @media (max-width: 768px) {
      section[data-testid="stSidebar"] { display: none !important; }
      .ov-mobile-nav-trigger { display: flex !important; }
    }
    @media (min-width: 769px) {
      .ov-mobile-nav-trigger { display: none !important; }
      .ov-mobile-nav-overlay-wrap { display: none !important; }
    }
    .ov-mobile-nav-trigger {
      display: none; position: fixed !important; top: 10px !important; right: 12px !important;
      z-index: 1001 !important;
    }
    .ov-mobile-nav-trigger .stButton > button {
      background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%) !important;
      color: #FFFFFF !important; border: 1px solid rgba(255,255,255,0.25) !important;
      border-radius: 12px !important; padding: 8px 14px !important;
      min-height: 42px !important; height: 42px !important;
      font-weight: 700 !important; font-size: 0.85rem !important;
      box-shadow: 0 4px 14px rgba(27,94,32,0.35) !important;
      gap: 6px !important;
    }
    .ov-mobile-nav-trigger .stButton > button p { color: #FFFFFF !important; font-weight: 700 !important; }
    .ov-mobile-nav-trigger .stButton > button:hover {
      background: linear-gradient(135deg, #145A1E 0%, #256E30 100%) !important;
      box-shadow: 0 6px 18px rgba(27,94,32,0.45) !important;
    }
    .ov-mobile-nav-overlay-wrap {
      position: fixed !important; top: 60px !important; right: 12px !important; left: 12px !important;
      z-index: 1000 !important; background: #FFFFFF !important;
      border: 1px solid #C8E6C9 !important; border-radius: 16px !important;
      box-shadow: 0 12px 32px rgba(27,94,32,0.18) !important;
      padding: 12px !important; max-height: 72vh !important; overflow-y: auto !important;
    }
    .ov-mobile-nav-overlay-wrap .ov-qv-group { color: #1B5E20 !important; font-weight: 700 !important; }
    </style>
    """, unsafe_allow_html=True)
    # Render grouped buttons — moved up (header removed), active = primary
    for grp_label, items in QUICK_VIEW_GROUPS:
      st.markdown(f'<p class="ov-qv-group">{grp_label}</p>', unsafe_allow_html=True)
      for label, icon in items:
        is_active = (st.session_state.get("overview_section") == label)
        if st.button(
          label,
          icon=f":material/{icon}:" if icon else None,
          use_container_width=True,
          type="primary" if is_active else "secondary",
          key=f"ov_qv_{label}",
        ):
          st.session_state["overview_section"] = label
          st.rerun()
    section_choice = st.session_state.get("overview_section", "Buong Dashboard")
  # --- Mobile: green pop-trigger (upper right, Material icon, highly visible) ---
  st.session_state.setdefault("ov_mobile_nav_open", False)
  # Fixed floating button — visible only on mobile via CSS (.ov-mobile-nav-trigger)
  st.markdown('<div class="ov-mobile-nav-trigger">', unsafe_allow_html=True)
  _is_open = st.session_state.get("ov_mobile_nav_open", False)
  _toggle_label = "Isara" if _is_open else "Menu"
  _toggle_icon = "close" if _is_open else "menu"
  if st.button(_toggle_label, icon=f":material/{_toggle_icon}:", key="ov_mobile_toggle", type="primary"):
    st.session_state["ov_mobile_nav_open"] = not _is_open
    st.rerun()
  st.markdown('</div>', unsafe_allow_html=True)
  # Pop overlay — same QUICK_VIEW_GROUPS, green-themed, noticeable card
  if st.session_state.get("ov_mobile_nav_open", False):
    st.markdown('<div class="ov-mobile-nav-overlay-wrap">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; gap:8px; font-weight:800; color:#1B5E20; margin-bottom:8px;"><i class="material-symbols-outlined" style="font-size:20px; color:#1B5E20;">dashboard</i> Navigation</div>', unsafe_allow_html=True)
    for grp_label, items in QUICK_VIEW_GROUPS:
      st.markdown(f'<p class="ov-qv-group" style="color:#1B5E20 !important; margin-top:8px !important;">{grp_label}</p>', unsafe_allow_html=True)
      for label, icon in items:
        is_active = (st.session_state.get("overview_section") == label)
        if st.button(label, icon=f":material/{icon}:" if icon else None, use_container_width=True, type="primary" if is_active else "secondary", key=f"ov_mobile_{label}"):
          st.session_state["overview_section"] = label
          st.session_state["ov_mobile_nav_open"] = False
          st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
  show_all = section_choice == "Buong Dashboard"

  # ========================================================
  # DYNAMIC DATA FILTERING LOGIC
  # ========================================================
  # Filter by Year
  if selected_years:
    provincial_year = (
      df[df["year"].isin(selected_years)]
      .copy()
      .sort_values("date")
    )

    muni_filtered = muni[
      muni["year"].isin(selected_years)
    ]

  else:
    provincial_year = (
      df[df["year"] == available_years[0]]
      .copy()
      .sort_values("date")
    )

    muni_filtered = muni[
      muni["year"] == available_years[0]
      ]

  # Filter by Municipality
  if selected_munis and _muni_label_col is not None:
    muni_filtered = muni_filtered[
      muni_filtered[_muni_label_col].isin(selected_munis)
    ]
  else:
    muni_filtered = muni_filtered.iloc[0:0]

  # Filter quarterly_df to selected years for synchronized historical/forecast view
  if selected_years and not quarterly_df.empty:
    quarterly_df = quarterly_df[quarterly_df["year"].isin(selected_years)].copy()

  # ========================================================
  # METRIC GENERATION & VARIANCE CALCULATIONS
  # ========================================================
  # Align Fancy (6 months) vs Regular (3 months) ONCE, before any
  # DataFrame/chart is built. Months 4-6 of Regular become NaN.
  fc_fancy_s, fc_regular_s = _align_forecast_arrays(
    forecast_3months_fancy, forecast_variety_3months
  )

  # --- Unified metric generation with baseline-aligned forecast index ---
  # Baseline Alignment: forecast DatetimeIndex MUST start 1 month after the
  # latest historical date (e.g. Jan 2026 -> Feb 2026: Feb, Mar, Apr, May, Jun, Jul).
  # Do NOT force start to _today_month — that shifts Feb's value to August.
  _hist_last = pd.to_datetime(provincial_df["date"], errors="coerce").max()
  _today_month = pd.Timestamp.today().to_period("M").to_timestamp()

  if not provincial_year.empty:
    latest_selected = provincial_year.iloc[-1]
    avg_fancy_price = _safe_column(provincial_year, "fancy_palay_price").mean()
    avg_regular_price = _safe_column(provincial_year, "other_variety_price").mean()
    _prov_prod_col = _pick_column(
      provincial_year,
      ["production_total", "palay_production", "production", "volume", "production_mt"],
    )
    latest_production = (
      provincial_year.groupby("year")[_prov_prod_col].sum().mean()
      if _prov_prod_col is not None
      else 0
    )
    # Strictly 1 month after latest historical record — baseline
    _data_start = (pd.to_datetime(latest_selected["date"]) + pd.DateOffset(months=1)).to_period("M").to_timestamp()
    if pd.isna(_data_start):
      _data_start = (_hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp() if not pd.isna(_hist_last) else _today_month
  else:
    # Fallback when filtered frame empty — use full history anchor, not today
    avg_fancy_price = _safe_column(df, "fancy_palay_price").mean() if not df.empty else np.nan
    avg_regular_price = _safe_column(df, "other_variety_price").mean() if not df.empty else np.nan
    _prov_prod_col = _pick_column(df, ["production_total", "palay_production", "production", "volume", "production_mt"])
    if _prov_prod_col is not None and not df.empty and "year" in df.columns:
      try:
        latest_production = df.groupby("year")[_prov_prod_col].sum().mean()
      except Exception:
        latest_production = 0
    else:
      latest_production = 0
    # No latest_selected — anchor to _hist_last +1M, fallback to today only if no history
    if not pd.isna(_hist_last):
      _data_start = (_hist_last + pd.DateOffset(months=1)).to_period("M").to_timestamp()
    else:
      _data_start = _today_month

  # Single forecast axis — strictly baseline-aligned, never forced to today
  _forecast_start = _data_start
  _fc_len = len(fc_fancy_s) if len(fc_fancy_s) > 0 else 6
  forecast_months = pd.date_range(start=_forecast_start, periods=_fc_len, freq="MS")
  # Range label reflects true forecast horizon (e.g. Feb 2026 – Jul 2026)
  if len(forecast_months) > 1:
    forecast_range_label = f"{forecast_months[0].strftime('%B %Y')} \u2013 {forecast_months[-1].strftime('%B %Y')}"
  elif len(forecast_months) > 0:
    forecast_range_label = forecast_months[0].strftime("%B %Y")
  else:
    forecast_range_label = "N/A"
  # Display month is the current month's label if within horizon, else nearest fallback (last)
  _today_m = _today_month
  if len(forecast_months) > 0 and _today_m in forecast_months:
    next_month_name = _today_m.strftime("%B %Y")
  elif len(forecast_months) > 0:
    # Outside/beyond horizon (e.g., today Aug but window Feb-Jul) -> show last/closest month (July)
    next_month_name = forecast_months[-1].strftime("%B %Y")
  else:
    next_month_name = "N/A"
  # Dynamic LGU update warning — if today beyond max forecasted month
  # Dynamically extracts last available month so it updates with horizon length (June/July/Sept etc.)
  last_avail_month = forecast_months[-1].strftime("%B %Y") if len(forecast_months) > 0 else "N/A"
  is_awaiting_lgu = False
  if len(forecast_months) > 0 and _today_m > forecast_months[-1]:
    is_awaiting_lgu = True
  _hist_last_q = pd.Period(_hist_last, freq="Q") + 1 if not pd.isna(_hist_last) else pd.Period(_today_month, freq="Q") + 1
  # Baseline: strictly next quarter after last hist — not forced to today
  _yield_forecast_start_q = _hist_last_q

  # Index-based lookup: map values to actual months, then .loc[_today_month]
  fancy_indexed = pd.Series(fc_fancy_s.values, index=forecast_months) if len(forecast_months) == len(fc_fancy_s) else pd.Series(list(forecast_3months_fancy), index=forecast_months[:len(forecast_3months_fancy)] if len(forecast_3months_fancy) else forecast_months)
  regular_indexed = pd.Series(fc_regular_s.values, index=forecast_months) if len(forecast_months) == len(fc_regular_s) else pd.Series(list(forecast_variety_3months), index=forecast_months[:len(forecast_variety_3months)] if len(forecast_variety_3months) else forecast_months)

  # Terminal Debugging: log Month vs Value mapping and selected .loc value
  print("[DEBUG] Fancy Forecast Series (Month -> Value):")
  try:
    print(fancy_indexed.to_string())
  except Exception as e:
    print(f" (could not print fancy_indexed: {e})")
  print("[DEBUG] Regular Forecast Series (Month -> Value):")
  try:
    print(regular_indexed.to_string())
  except Exception as e:
    print(f" (could not print regular_indexed: {e})")
  print(f"[DEBUG] _today_month for lookup: {_today_m.strftime('%Y-%m-%d')} | forecast_months[0]={forecast_months[0] if len(forecast_months)>0 else 'N/A'} | forecast_range={forecast_range_label}")

  def _forecast_value_for_month(indexed: pd.Series, fallback_list: list):
    # Keep checking if _today_month exists in fancy_indexed / regular_indexed
    if not indexed.empty and _today_m in indexed.index:
      v = indexed.loc[_today_m]
      print(f"[DEBUG] .loc[{_today_m.strftime('%Y-%m-%d')}] hit -> {v} (exact current month)")
      if not pd.isna(v):
        return float(v)
    # Fallback Adjustment: if _today_month outside/beyond horizon -> .iloc[-1] (last/closest, e.g., July)
    s = indexed.dropna()
    if not s.empty:
      # Beyond horizon (Aug > Jul) -> last; before horizon would also be last per spec (closest forecasted month)
      print(f"[DEBUG] .loc miss for {_today_m.strftime('%Y-%m-%d')} (outside/beyond forecast horizon {forecast_months[0].strftime('%Y-%m-%d') if len(forecast_months)>0 else 'N/A'} – {forecast_months[-1].strftime('%Y-%m-%d') if len(forecast_months)>0 else 'N/A'}) — fallback to .iloc[-1] latest available {s.index[-1].strftime('%Y-%m-%d')} -> {s.iloc[-1]}")
      return float(s.iloc[-1])
    print(f"[DEBUG] .loc miss & empty indexed — fallback to _safe_index list[0] -> {_safe_index(fallback_list, 0)}")
    return _safe_index(fallback_list, 0)

  _fancy_current = _forecast_value_for_month(fancy_indexed, forecast_3months_fancy)
  _regular_current = _forecast_value_for_month(regular_indexed, forecast_variety_3months)
  print(f"[DEBUG] Selected _fancy_current for {_today_m.strftime('%B %Y')}: {_fancy_current}")
  print(f"[DEBUG] Selected _regular_current for {_today_m.strftime('%B %Y')}: {_regular_current}")
  # Single source for both display and variance
  next_fancy_pred = _fancy_current
  next_regular_pred = _regular_current
  _fancy_0 = _fancy_current
  _regular_0 = _regular_current
  percent_change_fancy = _pct_change(_fancy_0, avg_fancy_price) or 0.0
  percent_change_regular = _pct_change(_regular_0, avg_regular_price) or 0.0
  avg_yield_forecast = _safe_mean(forecast_quarterly_yield)

  # ========================================================
  # CHART GENERATION SETUP
  # ========================================================
  _hy_col = _pick_column(
    provincial_year,
    ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha", "Yield"],
  )
  if _hy_col is not None and "quarter" in provincial_year.columns:
    historical_yield = (
      provincial_year
      .groupby("quarter")[_hy_col]
      .mean()
      .reset_index()
    )
    historical_yield["Quarter"] = "Q" + historical_yield["quarter"].astype(str)
    historical_yield["Yield"] = historical_yield[_hy_col]
    historical_yield["Type"] = "Past Records"
  else:
    historical_yield = pd.DataFrame(columns=["Quarter", "Yield", "Type"])

  _fc_yield_list = list(forecast_quarterly_yield) if forecast_quarterly_yield is not None else []
  forecast_yield = pd.DataFrame({
    "Quarter": [f"Q{i}" for i in range(1, len(_fc_yield_list) + 1)],
    "Yield": _fc_yield_list,
    "Type": "Forecast"
  })
  yield_chart_df = pd.concat([historical_yield[["Quarter", "Yield", "Type"]], forecast_yield])

  # FORECAST DATAFRAMES (SHARED)
  # Use the already-aligned series (months 4-6 of Regular are NaN),
  # so pd.DataFrame never receives mismatched lengths.
  forecast_df_fancy = pd.DataFrame({
    "date": forecast_months,
    "fancy_palay_price": fc_fancy_s.values,
    "Type": "Forecast"
  })

  forecast_df_regular = pd.DataFrame({
    "date": forecast_months,
    "other_variety_price": fc_regular_s.values,
    "Type": "Forecast"
  })

  # ========================================================
  # PRICE DATA (Historical + Forecast)
  # ========================================================

  if len(selected_years) == 1:

    hist_df = provincial_year.copy()

    # Fancy Historical
    hist_fancy = hist_df[["date", "fancy_palay_price"]].rename(columns={
      "fancy_palay_price": "Price"
    })
    hist_fancy["Variety"] = "Fancy Palay"
    hist_fancy["Type"] = "Historical"

    # Fancy Forecast
    forecast_fancy = forecast_df_fancy.rename(columns={
      "fancy_palay_price": "Price"
    }).copy()
    forecast_fancy["Variety"] = "Fancy Palay"

    # Regular Historical
    hist_regular = hist_df[["date", "other_variety_price"]].rename(columns={
      "other_variety_price": "Price"
    })
    hist_regular["Variety"] = "Regular Palay"
    hist_regular["Type"] = "Historical"

    # Regular Forecast
    forecast_regular = forecast_df_regular.rename(columns={
      "other_variety_price": "Price"
    }).copy()
    forecast_regular["Variety"] = "Regular Palay"

    combined_price = pd.concat([
      hist_fancy,
      forecast_fancy,
      hist_regular,
      forecast_regular
    ])

    combined_price["Category"] = (
        combined_price["Variety"] + " - " + combined_price["Type"]
    )

  else:

    _yearly_fancy = _pick_column(provincial_year, ["fancy_palay_price"])
    _yearly_regular = _pick_column(provincial_year, ["other_variety_price"])
    _yearly_cols = [c for c in [_yearly_fancy, _yearly_regular] if c is not None]
    if "year" in provincial_year.columns and _yearly_cols:
      yearly = (
        provincial_year
        .groupby("year")[_yearly_cols]
        .mean()
        .reset_index()
      )
    else:
      yearly = pd.DataFrame(columns=["year", "fancy_palay_price", "other_variety_price"])

    hist_fancy = yearly[["year", "fancy_palay_price"]].rename(columns={
      "year": "date",
      "fancy_palay_price": "Price"
    })
    hist_fancy["Variety"] = "Fancy Palay"
    hist_fancy["Type"] = "Historical"

    hist_regular = yearly[["year", "other_variety_price"]].rename(columns={
      "year": "date",
      "other_variety_price": "Price"
    })
    hist_regular["Variety"] = "Regular Palay"
    hist_regular["Type"] = "Historical"

    forecast_fancy = pd.DataFrame({
      "date": [forecast_year1],
      "Price": [np.mean(forecast_3months_fancy)],
      "Variety": ["Fancy Palay"],
      "Type": ["Forecast"]
    })

    forecast_regular = pd.DataFrame({
      "date": [forecast_year1],
      "Price": [np.mean(forecast_variety_3months)],
      "Variety": ["Regular Palay"],
      "Type": ["Forecast"]
    })

    combined_price = pd.concat([
      hist_fancy,
      hist_regular,
      forecast_fancy,
      forecast_regular
    ])

    combined_price["Category"] = (
        combined_price["Variety"] + " - " + combined_price["Type"]
    )

  # Top 5 Municipalities Ranking (Historical Production) via the data layer.
  top5_municipalities = dl.get_top_5_producing_municipalities(muni_filtered, selected_years)

  # Total Production summed across the selected years. Prefer the provincial
  # annual records (authoritative scale); fall back to municipality data when
  # the provincial frame has no rows.
  total_production = dl.get_total_production(provincial_year, selected_years)
  if total_production is None:
    total_production = dl.get_total_production(muni_filtered, selected_years)
  prod_val = total_production if total_production is not None else 0

  # ----------------------------------------------------------------
  # DYNAMIC KPI SUBTEXT — Total Production / Avg Yield / Harvested Area
  # ----------------------------------------------------------------
  # Production subtext: single vs multi-year + muni + period
  # (reactive to Year Range, Period, Municipality)
  prod_has_data = total_production is not None
  if prod_has_data:
    prod_subtext = _kpi_subtext_total_production(
      selected_start_year, selected_end_year, selected_period, selected_muni
    )
  else:
    prod_subtext = "Historical/current production"

  # Harvested Area source per clarification:
  #  specific municipality -> muni_filtered (dynamic per bayan)
  #  All Municipalities  -> provincial_year (fallback)
  _is_specific_muni = (selected_muni != "All Municipalities")
  harv_source_for_display = muni_filtered if _is_specific_muni else provincial_year
  # For previous-year lookup we need the unfiltered-full frames:
  # provincial full + muni full (pre-year-filter) so prev year can be found
  # even when selected range is single-year.
  _harv_candidates = [
    "harvested_total", "harvested_annual", "harvested_area",
    "area_harvested", "Harvested_Area", "harvested", "area", "Area",
    "harvested_ha",
  ]
  _yield_candidates = ["quarterly_yield_mt_per_ha", "yield", "yield_mt_per_ha", "Yield"]

  # --- Average Yield (historical, not forecast) + delta ---
  _yield_col = _pick_column(provincial_year, _yield_candidates)
  if _yield_col is None:
    _yield_col = _pick_column(df, _yield_candidates)
  _y_has_prev = False
  _y_delta: float | None = None
  _y_prev_year: int | None = None
  _yield_display_val: float | None = None
  try:
    # current average filtered to selected years + period slice
    _y_cur_df = _filter_df_by_period(provincial_year, selected_period)
    if _yield_col and not _y_cur_df.empty and _yield_col in _y_cur_df.columns:
      _y_cur_series = pd.to_numeric(_y_cur_df[_yield_col], errors="coerce").dropna()
      _yield_display_val = float(_y_cur_series.mean()) if not _y_cur_series.empty else None
    else:
      _yield_display_val = None

    # previous year lookup (from full provincial history)
    if selected_start_year == selected_end_year:
      _y_prev_year = selected_end_year - 1
      _prev_df_raw = df[df["year"] == _y_prev_year].copy() if "year" in df.columns else pd.DataFrame()
      _prev_df = _filter_df_by_period(_prev_df_raw, selected_period)
      if _yield_col and not _prev_df.empty and _yield_col in _prev_df.columns:
        _prev_series = pd.to_numeric(_prev_df[_yield_col], errors="coerce").dropna()
        _y_prev = float(_prev_series.mean()) if not _prev_series.empty else None
      else:
        _y_prev = None
      if _yield_display_val is not None and _y_prev is not None and not pd.isna(_y_prev) and _y_prev != 0:
        _y_delta = float(_yield_display_val - _y_prev)
        _y_has_prev = True
  except Exception:
    _y_has_prev = False
    _y_delta = None

  if selected_start_year == selected_end_year and _yield_display_val is None:
    _yield_subtext = f"Data as of {selected_end_year}{_period_suffix(selected_period)}"
    if _is_specific_muni:
      _yield_subtext += f" \u2022 {selected_muni}"
  else:
    _yield_subtext = _kpi_subtext_yield_or_area(
      start_year=selected_start_year,
      end_year=selected_end_year,
      period=selected_period,
      muni_name=selected_muni,
      delta=_y_delta,
      prev_year=_y_prev_year,
      has_prev=_y_has_prev,
      unit=" MT/ha",
      decimals=2,
    )

  # --- Harvested Area (ha) + delta ---
  _harv_col = _pick_column(harv_source_for_display, _harv_candidates)
  # fallback: try the other frame if not found in display source
  if _harv_col is None:
    _alt = provincial_year if _is_specific_muni else muni_filtered
    _harv_col = _pick_column(_alt, _harv_candidates)
    if _harv_col is not None:
      harv_source_for_display = _alt
  _h_has_prev = False
  _h_delta: float | None = None
  _h_prev_year: int | None = None
  _harv_display_val: float | None = None
  try:
    # helper to compute harvested total for a frame: per-year mean then sum
    def _harv_total_for_frame(frame: pd.DataFrame, col: str, period: str):
      if frame is None or frame.empty or col not in frame.columns:
        return None
      f = _filter_df_by_period(frame, period)
      if f.empty:
        return None
      if "year" in f.columns:
        per_year = pd.to_numeric(f[col], errors="coerce").groupby(f["year"]).mean().dropna()
        # keep only positive
        per_year = per_year[per_year > 0]
        if per_year.empty:
          return None
        return float(per_year.sum())
      vals = pd.to_numeric(f[col], errors="coerce").dropna()
      return float(vals.sum()) if not vals.empty else None

    # For display value: sum/mean across selected range
    _harv_display_val = _harv_total_for_frame(harv_source_for_display, _harv_col, selected_period) if _harv_col else None
    # For single-year delta we compare to previous year total
    if selected_start_year == selected_end_year and _harv_col:
      _h_prev_year = selected_end_year - 1
      # prev frame depends on source choice (municipality vs province)
      if _is_specific_muni:
        # prev municipality slice for that muni + prev year
        _prev_raw = muni[muni["year"] == _h_prev_year].copy() if "year" in muni.columns else pd.DataFrame()
        if _muni_label_col is not None and not _prev_raw.empty:
          _prev_raw = _prev_raw[_prev_raw[_muni_label_col].isin(selected_munis)]
        _h_prev = _harv_total_for_frame(_prev_raw, _harv_col, selected_period)
        # fallback to provincial if municipal prev empty
        if _h_prev is None:
          _prev_prov = df[df["year"] == _h_prev_year].copy() if "year" in df.columns else pd.DataFrame()
          _alt_col = _pick_column(_prev_prov, _harv_candidates) or _harv_col
          _h_prev = _harv_total_for_frame(_prev_prov, _alt_col, selected_period) if _alt_col else None
          _harv_col = _alt_col or _harv_col
      else:
        _prev_prov = df[df["year"] == _h_prev_year].copy() if "year" in df.columns else pd.DataFrame()
        _prev_col = _pick_column(_prev_prov, _harv_candidates) or _harv_col
        _h_prev = _harv_total_for_frame(_prev_prov, _prev_col, selected_period) if _prev_col else None
        _harv_col = _prev_col or _harv_col

      if _harv_display_val is not None and _h_prev is not None and not pd.isna(_h_prev):
        _h_delta = float(_harv_display_val - _h_prev)
        # prev exists even if zero delta; require non-null for has_prev
        _h_has_prev = True
        # if both are 0/None treat as no prev
        if _harv_display_val == 0 and _h_prev == 0:
          _h_has_prev = False
  except Exception:
    _h_has_prev = False
    _h_delta = None

  if selected_start_year == selected_end_year and _harv_display_val is None:
    _harv_subtext = f"Data as of {selected_end_year}{_period_suffix(selected_period)}"
    if _is_specific_muni:
      _harv_subtext += f" \u2022 {selected_muni}"
    _h_has_prev = False
  else:
    _harv_subtext = _kpi_subtext_yield_or_area(
      start_year=selected_start_year,
      end_year=selected_end_year,
      period=selected_period,
      muni_name=selected_muni,
      delta=_h_delta,
      prev_year=_h_prev_year,
      has_prev=_h_has_prev,
      unit=" ha",
      decimals=0,
    )

  # Fallback display values when computation yields None
  _harv_display_str = f"{_harv_display_val:,.0f} ha" if _harv_display_val is not None and not pd.isna(_harv_display_val) else "No Data Available"
  _yield_display_str = f"{_yield_display_val:.2f} MT/ha" if _yield_display_val is not None and not pd.isna(_yield_display_val) else ("No Data Available" if yield_has_data else "No Data Available")
  # If no yield column at all, fall back to forecast average for value but keep dynamic subtext
  if _yield_display_val is None and yield_has_data:
    _yield_display_str = f"{avg_yield_forecast:.2f} MT/ha"
    # subtext remains the dynamic one computed above (delta/fallback)
  _harv_has_data = _harv_display_val is not None and not pd.isna(_harv_display_val)

  # ========================================================
  # FRONT-END CSS
  # ========================================================
  st.markdown("""
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800;900&display=swap');

    /* Main Container */
    .main-container { 
      font-family: 'Poppins', sans-serif; 
      padding: 0 1% 20px 1%; 
      background: #F8FAF9;
    }

    .block-container {
      padding-left: 1rem !important;
      padding-right: 1rem !important;
      padding-top: 2rem !important;
      padding-bottom: 0rem !important;
    }

    /* Hero Banner - Modern Gradient */
    .hero-banner {
      background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 40%, #388E3C 100%);
      padding: 35px 40px;
      border-radius: 20px;
      color: white;
      margin-bottom: 28px;
      box-shadow: 0 12px 35px rgba(27, 94, 32, 0.2);
      position: relative;
      overflow: hidden;
      margin-top: -2.08rem;
    }
    .hero-banner::before {
      content: '';
      position: absolute;
      top: -50%;
      right: -10%;
      width: 400px;
      height: 400px;
      background: rgba(255, 255, 255, 0.05);
      border-radius: 50%;
    }
    .hero-banner::after {
      content: '';
      position: absolute;
      bottom: 10px;
      right: 30px;
      font-size: 80px;
      opacity: 0.1;
    }
    .hero-title { 
      font-size: clamp(1.8rem, 2.8vw, 2.5rem); 
      font-weight: 900; 
      margin-bottom: 8px;
      letter-spacing: -0.5px;
    }
    .hero-subtitle { 
      font-size: 1rem; 
      opacity: 0.92; 
      line-height: 1.6;
      font-weight: 400;
    }
    .hero-badge {
      display: inline-block;
      background: rgba(255, 255, 255, 0.15);
      padding: 4px 16px;
      border-radius: 20px;
      font-size: 0.75rem;
      font-weight: 600;
      margin-top: 8px;
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Forecasted banner — single bar above forecasted KPIs */
    .forecast-bar {
      background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
      color: #FFFFFF;
      padding: 10px 18px;
      border-radius: 12px;
      font-weight: 700;
      font-size: 0.85rem;
      letter-spacing: 0.3px;
      margin-bottom: 12px;
      box-shadow: 0 4px 12px rgba(27,94,32,0.15);
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .forecast-bar small {
      font-weight: 500;
      opacity: 0.9;
      font-size: 0.75rem;
    }
    /* Forecast banner — strict 2-column inside single container, no wrap, no hidden text */
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] {
      background: #FFFFFF;
      border: 1px solid #C8E6C9;
      border-radius: 12px;
      padding: 10px 16px;
      margin-bottom: 12px;
      box-shadow: 0 2px 8px rgba(27,94,32,0.08);
      gap: 12px;
    }
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"] {
      display: flex;
      align-items: center;
    }
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"]:first-child > div {
      flex: 1;
      min-width: 0;
    }
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stColumn"]:last-child {
      justify-content: flex-end;
      flex-shrink: 0;
    }
    .forecast-bar-text {
      color: #1B5E20 !important;
      font-weight: 700 !important;
      font-size: 0.85rem !important;
      letter-spacing: 0.3px;
      white-space: nowrap;
      overflow: visible;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .forecast-bar-text small {
      font-weight: 500 !important;
      opacity: 0.9;
      font-size: 0.75rem !important;
      color: #2E7D32 !important;
    }
    .forecast-bar-text .material-symbols-outlined {
      color: #1B5E20 !important;
      font-size: 18px !important;
    }
    /* Popover inside banner — light green on white, dark green text, green line info icon */
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stPopover"] > button {
      background: #E8F5E9 !important;
      border: 1px solid #C8E6C9 !important;
      color: #1B5E20 !important;
      font-weight: 600 !important;
      font-size: 0.75rem !important;
      border-radius: 8px !important;
      padding: 6px 12px !important;
      box-shadow: none !important;
      height: 32px;
      white-space: nowrap;
      flex-shrink: 0;
    }
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stPopover"] > button:hover {
      background: #C8E6C9 !important;
      border-color: #A5D6A7 !important;
    }
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] div[data-testid="stPopover"] > button p {
      color: #1B5E20 !important;
      font-size: 0.75rem !important;
      white-space: nowrap;
    }
    .forecast-banner-anchor + div[data-testid="stHorizontalBlock"] .material-symbols-outlined {
      color: #1B5E20 !important;
      vertical-align: middle;
      margin-right: 4px;
      font-size: 16px !important;
    }
    /* KPI Cards - Glassmorphism */
    .kpi-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 16px;
      margin-bottom: 28px;
    }
    .metric-card {
      background: #FFFFFF;
      padding: 20px 22px;
      border-radius: 16px;
      border: 1px solid rgba(46, 125, 50, 0.08);
      position: relative;
      overflow: hidden;
    }
    .metric-card:hover {
      border-color: rgba(46, 125, 50, 0.2);
    }
    .metric-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: linear-gradient(90deg, #2E7D32, #66BB6A);
    }
    .metric-card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }
    .metric-title { 
      font-size: 0.8rem; 
      font-weight: 600; 
      color: #6B7280;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .metric-icon {
      font-size: 1.2rem;
      opacity: 0.7;
    }
    .metric-data { 
      font-size: 1.8rem; 
      font-weight: 800; 
      color: #1B5E20;
      margin: 4px 0 2px 0;
      letter-spacing: -0.5px;
    }
    .metric-footer { 
      font-size: 0.7rem; 
      color: #9CA3AF;
      font-weight: 500;
    }
    .metric-change-positive {
      color: #16A34A;
      font-weight: 700;
    }
    .metric-change-negative {
      color: #DC2626;
      font-weight: 700;
    }

    /* Component Cards - Clean Design */
    .component-card {
      background: #FFFFFF;
      border-radius: 16px;
      border: 1px solid rgba(0, 0, 0, 0.05);
      padding: 22px 24px 24px 24px;
      margin-bottom: 20px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.03);
    }
    .component-card:hover {
      box-shadow: 0 6px 20px rgba(0, 0, 0, 0.06);
    }
    .component-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;
    }
    .component-header {
      font-size: 1.05rem;
      font-weight: 700;
      color: #111827;
    }
    .component-header-icon {
      font-size: 1.1rem;
      margin-right: 8px;
    }
    .component-desc {
      font-size: 0.8rem;
      color: #6B7280;
      margin-bottom: 16px;
      font-weight: 400;
    }

    /* Advisory Cards - Enhanced */
    .advisory-container {
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
      margin-top: 4px;
    }
    .advisory-card {
      display: flex;
      align-items: flex-start;
      padding: 16px 20px;
      border-radius: 12px;
      background-color: #FFFFFF;
      border: 1px solid #E5E7EB;
    }
    .advisory-card:hover {
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }
    .card-status {
      border-left: 4px solid #0284C7;
      background: linear-gradient(135deg, #F0F9FF 0%, #FFFFFF 100%);
    }
    .card-marketing {
      border-left: 4px solid #16A34A;
      background: linear-gradient(135deg, #F0FDF4 0%, #FFFFFF 100%);
    }
    .card-notice {
      border-left: 4px solid #EA580C;
      background: linear-gradient(135deg, #FFF7ED 0%, #FFFFFF 100%);
    }
    .card-optimization {
      border-left: 4px solid #7C3AED;
      background: linear-gradient(135deg, #F5F3FF 0%, #FFFFFF 100%);
    }
    .card-icon {
      font-size: 1.2rem;
      margin-right: 14px;
      margin-top: 2px;
    }
    .card-body {
      flex: 1;
      font-size: 0.88rem;
      line-height: 1.6;
      color: #374151;
    }
    .card-label {
      font-weight: 700;
      margin-right: 4px;
    }
    .label-status { color: #0369A1; }
    .label-marketing { color: #15803D; }
    .label-notice { color: #C2410C; }
    .label-optimization { color: #6D28D9; }
    .highlight-text {
      font-weight: 700;
      color: #1B5E20;
      background: rgba(27, 94, 32, 0.06);
      padding: 1px 6px;
      border-radius: 4px;
    }

    /* Custom Streamlit Overrides */
    .stSelectbox, .stMultiSelect {
      font-family: 'Poppins', sans-serif;
    }
    .stRadio > div {
      gap: 8px;
    }
    .stRadio label {
      font-family: 'Poppins', sans-serif;
      font-size: 0.85rem;
      padding: 6px 12px;
      border-radius: 8px;
      background: #F3F4F6;
    }
    .stRadio label:hover {
      background: #E8F5E9;
    }
    .stRadio [data-baseweb="radio"] {
      margin-right: 6px;
    }

    /* Sidebar enhancements */
    .css-1d391kg {
      background: #F8FAF9;
    }

    /* Responsive adjustments */
    @media (max-width: 768px) {
      .hero-banner {
        padding: 24px 20px;
      }
      .metric-card {
        padding: 16px 18px;
      }
      .component-card {
        padding: 16px 18px;
      }
    }
  </style>
  """, unsafe_allow_html=True)

  # ========================================================
  # LAYOUT RENDERING INTERFACE
  # ========================================================
  st.markdown('<div class="main-container">', unsafe_allow_html=True)

  # Hero Banner
  eco_display = "All Types" if selected_eco == "All Types" else selected_eco
  year_display = ", ".join(map(str, selected_years)) if selected_years else "All Years"

  st.markdown(f"""
  <div class="hero-banner">
    <div class="hero-title"> Bataan Rice Monitoring & Prediction</div>
    <div class="hero-subtitle">
      Data-driven insights for smarter farming decisions • 
      <strong>{eco_display}</strong> ecosystem 
    </div>
    <span class="hero-badge"><i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#FFFFFF;">analytics</i> Live Dashboard • {len(selected_munis) if selected_munis else 0} municipalities selected</span>
  </div>
  """, unsafe_allow_html=True)

  # KPI Row — each card checks `has_data` so empty selections show a clear
  # "No Data Available" fallback instead of ₱0.00 / -100.0% placeholders.
  # Dynamic subtexts (prod_subtext / _yield_subtext / _harv_subtext) are
  # computed above and react to Year Range / Period / Municipality changes.
  if total_production is not None:
    prod_display = f"{total_production:,.0f} MT"
    prod_footer = prod_subtext
  else:
    prod_display = "No Data Available"
    prod_footer = "Historical/current production"

  yield_has_data = (_yield_display_val is not None and not pd.isna(_yield_display_val)) or (bool(forecast_quarterly_yield) and not pd.isna(avg_yield_forecast))
  fancy_has_data = (
    bool(forecast_3months_fancy)
    and not provincial_year.empty
    and not pd.isna(avg_fancy_price)
    and avg_fancy_price != 0
  )
  regular_has_data = (
    bool(forecast_variety_3months)
    and not provincial_year.empty
    and not pd.isna(avg_regular_price)
    and avg_regular_price != 0
  )

  fancy_color = "metric-change-positive" if percent_change_fancy >= 0 else "metric-change-negative"
  regular_color = "metric-change-positive" if percent_change_regular >= 0 else "metric-change-negative"
  fancy_arrow = "↑" if percent_change_fancy >= 0 else "↓"
  regular_arrow = "↑" if percent_change_regular >= 0 else "↓"

  # Average Yield value prefers historical mean (_yield_display_str) with
  # dynamic subtext; fallback to forecast if historical missing.
  yield_display = _yield_display_str
  yield_footer = _yield_subtext

  # Expected Yield (existing 3.74 MT/ha card) — forecast cycle target, now
  # with year in subtext per request: "Target weight per hectare this cycle • 2026"
  expected_has_data = bool(forecast_quarterly_yield) and not pd.isna(avg_yield_forecast)
  expected_display = f"{avg_yield_forecast:.2f} MT/ha" if expected_has_data else "No Data Available"
  # forecast year anchor (dynamic, from forecast_quarters or selected year)
  try:
    _exp_year = int(forecast_year1) if forecast_year1 else int(selected_end_year) + 1
  except Exception:
    _exp_year = int(selected_end_year) if selected_end_year else 2026
  # 4th KPI — forecasted-only, simplified subtext per farmer UX requirements
  forecasted_has_data = bool(forecast_quarterly_yield) and not pd.isna(avg_yield_forecast)
  forecasted_display = f"{avg_yield_forecast:.2f} MT/ha" if forecasted_has_data else "No Data Available"
  try:
    _fc_year = int(forecast_year1) if forecast_year1 else int(selected_end_year) + 1
  except Exception:
    _fc_year = int(selected_end_year) if selected_end_year else 2026
  _fc_vs_hist = _pct_change(avg_yield_forecast, _yield_display_val) if forecasted_has_data and _yield_display_val is not None else None
  if forecasted_has_data:
    forecast_peak = _safe_max(forecast_quarterly_yield) if forecast_quarterly_yield else None
    forecast_low = _safe_min(forecast_quarterly_yield) if forecast_quarterly_yield else None
    # Simplify: single concise line — Expected Range: {low} - {peak} MT/ha ({pct}% vs hist avg)
    # Maintains MT/ha unit and pct_change formatting, removes crowded Next Q / multi-bullet lines
    if forecast_low is not None and forecast_peak is not None and not pd.isna(forecast_low) and not pd.isna(forecast_peak):
      if _fc_vs_hist is not None and not pd.isna(_fc_vs_hist):
        _sign = "+" if _fc_vs_hist >= 0 else ""
        forecasted_sub = f"Expected Range: {forecast_low:.2f} - {forecast_peak:.2f} MT/ha ({_sign}{_fc_vs_hist:.1f}% vs hist avg)"
      else:
        forecasted_sub = f"Expected Range: {forecast_low:.2f} - {forecast_peak:.2f} MT/ha"
    else:
      # Fallback if peak/low unavailable
      if _fc_vs_hist is not None and not pd.isna(_fc_vs_hist):
        _sign = "+" if _fc_vs_hist >= 0 else ""
        forecasted_sub = f"Forecasted \u2022 {forecast_range_label} ({_sign}{_fc_vs_hist:.1f}% vs hist avg)"
      else:
        forecasted_sub = f"Forecasted \u2022 {forecast_range_label}"
    forecasted_inner = "" # Remove extra crowded line — single subtext only
    forecasted_title = "Forecasted Yield"
  else:
    forecasted_sub = "No forecast available"
    forecasted_inner = ""
    forecasted_title = "Forecasted Yield"
    forecasted_display = "No Data Available"

  # Fancy / Regular — invert: real ₱ price is highlight, % is footer badge
  fancy_price_has = next_fancy_pred is not None and not pd.isna(next_fancy_pred)
  regular_price_has = next_regular_pred is not None and not pd.isna(next_regular_pred)
  fancy_price_display = f"\u20B1{next_fancy_pred:.2f}/kg" if fancy_price_has else "No Data Available"
  regular_price_display = f"\u20B1{next_regular_pred:.2f}/kg" if regular_price_has else "No Data Available"
  fancy_delta_html = f'<span class="{fancy_color}">{fancy_arrow} {abs(percent_change_fancy):.1f}%</span> vs hist avg' if fancy_has_data else '<span class="metric-footer">No change data</span>'
  regular_delta_html = f'<span class="{regular_color}">{regular_arrow} {abs(percent_change_regular):.1f}%</span> vs hist avg' if regular_has_data else '<span class="metric-footer">No change data</span>'
  _price_period_suf = _period_suffix(selected_period)
  fancy_footer_html = f"{fancy_delta_html} \u2022 Forecast for: {next_month_name}{_price_period_suf}"
  regular_footer_html = f"{regular_delta_html} \u2022 Forecast for: {next_month_name}{_price_period_suf}"

  harv_display = _harv_display_str
  harv_footer = _harv_subtext

  if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Price Forecast",
                   "Yield Insights", "Price Insights"):
    # Strict 2-column inside banner container — ensures Forecasted text and Metadata stay side-by-side, no hidden text
    st.markdown('<div class="forecast-banner-anchor" style="display:none;"></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([0.8, 0.2], vertical_alignment="center", gap="small")
    with col1:
      st.markdown(f'<div class="forecast-bar-text"><i class="material-symbols-outlined">trending_up</i> Forecasted for {next_month_name} <small>({forecast_range_label})</small></div>', unsafe_allow_html=True)
    with col2:
      with st.popover(":material/info: Metadata", use_container_width=True):
        st.markdown("### **METADATA**\n**Source of Data & Metrics**")
        st.divider()
        st.markdown("""
        **KPI Definitions:**
        * **Special / Fancy Palay:** Farmgate price (presyo sa bukid) ng mga tanging uri tulad ng Dinorado o Jasmine.
        * **Regular Palay:** Farmgate price ng mga karaniwang inbred/hybrid dry at fresh palay.
        * **Yield (MT/ha):** Metric tons ng ani bawat ektarya.

        ---
        **Source:** Municipal & Provincial Agriculture Office Data (PhilRice / PSA Aligned)
        * **Frequency & Schedule:** Periodic / Quarterly LGU Encoding
        * **Status:** Dynamic validation with fallback for pending updates.
        """)
    # Row 1 — Forecasted KPIs on top (Material Symbols Outlined, no emojis)
    st.markdown(f'<div class="kpi-row">'
          f'<div class="metric-card"><div class="metric-card-header"><div class="metric-title"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">query_stats</i> {forecasted_title}</div></div><div class="metric-data">{forecasted_display}</div>{forecasted_inner}<div class="metric-footer">{forecasted_sub}</div></div>'
          f'<div class="metric-card"><div class="metric-card-header"><div class="metric-title"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">grade</i> Special / Fancy Palay</div></div><div class="metric-data">{fancy_price_display}</div><div class="metric-footer">{fancy_footer_html}</div></div>'
          f'<div class="metric-card"><div class="metric-card-header"><div class="metric-title"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">inventory_2</i> Regular Palay Price</div></div><div class="metric-data">{regular_price_display}</div><div class="metric-footer">{regular_footer_html}</div></div>'
          f'</div>', unsafe_allow_html=True)
    # Dynamic LGU update warning — shown when today beyond forecast horizon
    if is_awaiting_lgu:
      st.caption(f" Showing latest available forecast ({last_avail_month}). Status: Pending Next Cycle Data Input.")
    # Row 2 — Historical KPIs below (Material Symbols Outlined)
    st.markdown(f'<div class="kpi-row">'
          f'<div class="metric-card"><div class="metric-card-header"><div class="metric-title"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">inventory_2</i> Total Production</div></div><div class="metric-data">{prod_display}</div><div class="metric-footer">{prod_footer}</div></div>'
          f'<div class="metric-card"><div class="metric-card-header"><div class="metric-title"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">eco</i> Average Yield</div></div><div class="metric-data">{yield_display}</div><div class="metric-footer">{yield_footer}</div></div>'
          f'<div class="metric-card"><div class="metric-card-header"><div class="metric-title"><i class="material-symbols-outlined" style="font-size:16px; vertical-align:middle; margin-right:6px; color:#1B5E20;">agriculture</i> Harvested Area</div></div><div class="metric-data">{harv_display}</div><div class="metric-footer">{harv_footer}</div></div>'
          f'</div>', unsafe_allow_html=True)

  # --- Section Divider: Provincial Yield & Price Forecast Graphs ---
  if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Price Forecast", "Yield Insights", "Price Insights"):
    st.markdown("""
    <div style="margin: 1.4rem 0 0.6rem 0; border-top: 2px solid #C8E6C9; padding-top: 0.9rem; display:flex; align-items:center; gap:10px;">
      <span style="display:flex; align-items:left; gap:6px; font-weight:700; color:#1B5E20; font-size:1.02rem; white-space:nowrap;">
        <i class="material-symbols-outlined" style="font-size:19px; color:#1B5E20; vertical-align:middle;">show_chart</i>
        Provincial Yield & Price Forecast
      </span>
      <span style="flex:1; height:1px; background:#E8F5E9; margin-left:4px;"></span>
    </div>
    """, unsafe_allow_html=True)

  # --- Embedded Header Controls & Farmer-Friendly Popover (Tagalog refactor, Forecast default) ---
  _show_benchmark = show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Price Forecast", "Yield Insights", "Price Insights")
  if _show_benchmark:
    hdr_col1, hdr_col2 = st.columns([0.78, 0.22], vertical_alignment="center")
    with hdr_col1:
      # Use segmented_control for intuitive pill UI; fallback to radio if unavailable
      try:
        benchmark_option = st.segmented_control(
          "Ipakita ang Benchmark / Reference Line:",
          options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"],
          key="benchmark_toggle",
        )
        # segmented_control returns None when no selection; default to "Wala"
        if benchmark_option is None:
          benchmark_option = "Wala"
      except Exception:
        benchmark_option = st.radio(
          "Ipakita ang Benchmark / Reference Line:",
          options=["Presyo sa Merkado", "Target ng Gobyerno", "Wala"],
          horizontal=True,
          key="benchmark_toggle",
        )
      # Backwards-compat: map legacy English options if session holds old value
      if benchmark_option in ("3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
        benchmark_option = "Presyo sa Merkado"
      elif benchmark_option in ("NFA / DA Policy Baseline",):
        benchmark_option = "Target ng Gobyerno"
      elif benchmark_option in ("Itago (None)",):
        benchmark_option = "Wala"
    with hdr_col2:
      with st.popover(":material/info: Gabay sa Benchmark"):
        st.markdown("""
### **Ano ang ibig sabihin ng mga guhit (Benchmark Lines)?**

Nagsisilbi itong **pamantayan** para malaman mo kung mataas o mababa ang benta at ani mo.

* **:material/shopping_cart: Presyo sa Merkado (3-Yr Average):**
  Ito ang karaniwang presyo ng palay sa Bataan sa nakalipas na 3 taon. Ginagamit ito para maiwasan ang epekto ng nagbabagong presyo ng bilihin (inflation).

* **:material/account_balance: Target ng Gobyerno (NFA / DA):**
  * **Regular Palay:** **\u20B119.00/kg** *(minimum na bilhihan ng NFA)*. Kapag mas mababa dito ang alok sa bukid, lugi ka sa biyahero.
  * **Fancy Palay:** **\u20B123.75/kg** *(target na presyo para sa Dinorado/Jasmine)*.
  * **Ani (Yield):** **4.50 MT/ha** *(target na ani ng Department of Agriculture bawat ektarya)*.

* **:material/block: Wala:**
  Inaalis ang mga guhit para linya lang ng forecast o nakaraang taon ang makita mo.
""")
  else:
    benchmark_option = st.session_state.get("benchmark_toggle", "Wala")
    # normalize legacy values
    if benchmark_option in ("3-Year/Quarter Rolling Market Average", "10-Year Historical Average"):
      benchmark_option = "Presyo sa Merkado"
    elif benchmark_option == "NFA / DA Policy Baseline":
      benchmark_option = "Target ng Gobyerno"
    elif benchmark_option == "Itago (None)":
      benchmark_option = "Wala"

  # Plots Row 1
  chart_row1_col1, chart_row1_col2 = st.columns(2, gap="medium")

  with chart_row1_col1:
    if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Yield Insights"):
      st.markdown(
        '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:0px; color:#1B5E20;">trending_up</i></span>Provincial Yield Forecast</span></div><div class="component-desc">Historical harvest performance vs. AI-powered quarterly forecasts</div>',
        unsafe_allow_html=True)

      try:
        tab_yield_forecast, tab_yield_historical = st.tabs([":material/query_stats: Yield Forecast", ":material/show_chart: Historical Yield Trend"])
        with tab_yield_forecast:
          st.plotly_chart(
            _yield_forecast_chart(provincial_df, forecast_quarterly_yield, benchmark_option=benchmark_option),
            use_container_width=True,
            key=f"overview_yield_fc_{selected_start_year}_{selected_end_year}_{benchmark_option}",
          )
        with tab_yield_historical:
          st.plotly_chart(
            _yield_historical_chart(provincial_year, selected_period, benchmark_option=benchmark_option),
            use_container_width=True,
            key=f"overview_yield_hist_{selected_start_year}_{selected_end_year}_{selected_period}_{benchmark_option}",
          )
      except Exception as e:
        st.warning(f" Yield forecast chart could not render: {str(e)}")

      st.markdown("</div>", unsafe_allow_html=True)

  with chart_row1_col2:
    if show_all or section_choice in ("Buong Dashboard", "Price Forecast", "Price Insights"):
      st.markdown(
        '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:0px; color:#1B5E20;">analytics</i></span>Provincial Price Forecast (6 Months)</span></div><div class="component-desc">Strategic buying & selling windows for optimal returns</div>',
        unsafe_allow_html=True)

      try:
        tab_price_forecast, tab_price_historical = st.tabs([":material/query_stats: Price Forecast", ":material/show_chart: Historical Price Trend"])
        with tab_price_forecast:
          st.plotly_chart(
            _price_forecast_chart(provincial_df, forecast_3months_fancy, forecast_variety_3months, benchmark_option=benchmark_option),
            use_container_width=True,
            key=f"overview_price_fc_{selected_start_year}_{selected_end_year}_{benchmark_option}",
          )
        with tab_price_historical:
          st.plotly_chart(
            _price_historical_chart(provincial_year, selected_period, benchmark_option=benchmark_option),
            use_container_width=True,
            key=f"overview_price_hist_{selected_start_year}_{selected_end_year}_{selected_period}_{benchmark_option}",
          )
      except Exception as e:
        st.warning(f" Price forecast chart could not render: {str(e)}")
      st.markdown("</div>", unsafe_allow_html=True)

  # --- End Section Divider: Forecast Graphs (visual close) ---
  if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Price Forecast", "Yield Insights", "Price Insights"):
    st.markdown("""<hr style="border: none; border-top: 1px solid #E8F5E9; margin: 1.0rem 0 0.2rem 0;">""", unsafe_allow_html=True)

  # ========================================================
  # MUNICIPAL 3-MONTH PRICE FORECAST WITH SEASONAL TABS
  # ========================================================
  if show_all or section_choice in ("Buong Dashboard", "Municipal Forecast", "Municipal Analysis"):
    st.markdown("""<hr style="border:1px solid #ddd; margin-top: 1rem; margin-bottom: 1rem;">""",
          unsafe_allow_html=True)

    st.subheader(":material/agriculture: Municipal Price Forecast")
    st.write(
      "Projected palay price trends by crop cycle across Bataan municipalities. "
      "Use the filters below to explore rice types, classifications, and municipalities."
    )

    try:
      df_municipal_forecast = df_municipal_forecasts.copy()
      if df_municipal_forecast.empty:
        st.info("Municipal forecast dataset not available yet. "
            "Run the background pipeline to generate 3-month municipal forecasts.")
      else:
        # Municipalities from the forecast file feed the chart's multi-select.
        muni_label_col = _pick_column(df_municipal_forecast, ["Municipality"])
        muni_list = (
          list(df_municipal_forecast[muni_label_col].dropna().unique())
          if muni_label_col is not None
          else []
        )
        selected_muni = st.multiselect("Filter Municipalities:", options=muni_list, default=[])

        col_rt, col_cls = st.columns(2)
        with col_rt:
          ov_rice_type = st.selectbox("Rice Type",
                        options=["Hybrid", "Inbred"],
                        key="ov_muni_rt")
        with col_cls:
          ov_classification = st.selectbox("Rice Classification",
                           options=["Premium", "Ordinary"],
                           key="ov_muni_cls")

        # Actual 3-month forecast line chart (Altair, zoomed Y-axis).
        _render_municipal_crop_cycle_chart(
          df_municipal_forecast,
          rice_type=ov_rice_type,
          classification=ov_classification,
          selected_municipalities=selected_muni,
        )
    except FileNotFoundError:
      st.warning(" Forecast dataset report not found. Please verify the background pipeline ran completely.")
    except Exception as e:
      st.error(f" Unable to render the municipal price forecast chart: {str(e)}")

    st.markdown("""<hr style="border:1px solid #ddd; margin-top: 1rem; margin-bottom: 2rem;">""",
          unsafe_allow_html=True)

  # Data Row 2 (Ranking & Smart Cards)
  chart_row2_col1, chart_row2_col2 = st.columns([2.90, 2])

  with chart_row2_col1:
    if show_all or section_choice in ("Buong Dashboard", "Production Rankings", "Municipal Analysis"):
      st.markdown(
        '<div class="component-card"><div class="component-title-row"><span class="component-header"><span class="component-header-icon"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:0px; color:#1B5E20;">emoji_events</i></span>Top 5 Municipalities Ranking — Historical Production</span></div><div class="component-desc">Capacity comparison across the top-producing municipalities</div>',
        unsafe_allow_html=True)

      try:
        if not top5_municipalities.empty:
          # Enhanced horizontal bar chart
          fig_muni = px.bar(
            top5_municipalities.sort_values("palay_production"),
            x="palay_production",
            y="municipality",
            orientation="h",
            color="palay_production",
            color_continuous_scale=["#A5D6A7", "#2E7D32"],
            text="palay_production"
          )

          fig_muni.update_traces(
            texttemplate="%{text:,.0f} MT",
            textposition="outside",
            marker=dict(
              line=dict(width=2, color='white'),
              cornerradius=4
            ),
            hovertemplate="<b>%{y}</b><br>Production: %{x:,.0f} MT<extra></extra>"
          )

          fig_muni.update_layout(
            height=380,
            margin=dict(l=10, r=80, t=10, b=10),
            xaxis_title="Metric Tons",
            yaxis_title=None,
            showlegend=False,
            plot_bgcolor="white",
            paper_bgcolor="white",
            coloraxis_showscale=False,
            hovermode="y unified",
            yaxis={"categoryorder": "total ascending"}
          )
          fig_muni.update_xaxes(gridcolor="#F3F4F6", showgrid=True)
          fig_muni.update_yaxes(gridcolor="#F3F4F6", showgrid=True)

          st.plotly_chart(
            fig_muni,
            use_container_width=True,
            key=f"municipality_production_fig_{selected_start_year}_{selected_end_year}"
          )
        else:
          st.info("No matching data found for your current filters.")
      except Exception as e:
        st.warning(f" Production rankings chart could not render: {str(e)}")

      st.markdown("</div>", unsafe_allow_html=True)

    # SMART FARMER CARDS INTERACTION VIEW
    with chart_row2_col2:
      if show_all or section_choice in ("Buong Dashboard", "Mga Payo (Advisories)"):
        st.markdown(f"""
        <div class="component-card">
          <div class="component-header">Smart Agricultural Advisories</div>
          <div class="component-desc">Live operational recommendations for <b>{selected_munis}</b>.</div>
        """, unsafe_allow_html=True)

        display_muni_name = "All Bataan Municipalities" if selected_munis == "All Municipalities" else selected_munis
        display_year_string = ", ".join(map(str, selected_years)) if selected_years else "Selected Years"

        if not muni_filtered.empty:
          eco_msg = "Rainfed setups should maximize water-retention fields and sync planting timelines with historical rainy quarters." if selected_eco == "Rainfed / Seasonal" else "Water-Irrigated setups can securely aim for high-input Fancy Varieties due to reliable water schedules."

          html_cards = f"""
          <div class="advisory-container">
          <div class="advisory-card card-status">
          <div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:6px; color:#1B5E20;">location_on</i></div>
          <div class="card-body">
          <span class="card-label label-status">Ecosystem Scope ({selected_eco}):</span>
          Total output volume records captured for <span class="highlight-text">{display_muni_name}</span> across <span class="highlight-text">{display_year_string}</span> equals <span class="highlight-text">{prod_val:,.1f} MT</span>.
          </div>
          </div>
          <div class="advisory-card card-marketing">
          <div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:6px; color:#1B5E20;">lightbulb</i></div>
          <div class="card-body">
          <span class="card-label label-marketing">Trading Target Advisory:</span>
          Predictions indicate Premium Fancy varieties are heading toward <span class="highlight-text">₱{next_fancy_pred:.2f}/kg</span> next month, while regular commercial grades stabilize near <span class="highlight-text">₱{next_regular_pred:.2f}/kg</span>.
          </div>
          </div>
          <div class="advisory-card card-optimization">
          <div class="card-icon"><i class="material-symbols-outlined" style="font-size:20px; vertical-align:middle; margin-right:6px; color:#1B5E20;">water_drop</i></div>
          <div class="card-body">
          <span class="card-label label-optimization">Ecosystem Recommendation:</span>
          {eco_msg}
          </div>
          </div>
          </div>
          """
          st.markdown(html_cards, unsafe_allow_html=True)
        else:
          st.warning(f"No active metrics found matching your current dashboard filter selections.")

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

  # ---- Yield Forecast Summary ----
  if show_all or section_choice in ("Buong Dashboard", "Yield Forecast", "Yield Insights"):
    _yield_summary_card(forecast_quarterly_yield)

  # ---- Insights Narrative ----
  if show_all or section_choice in ("Buong Dashboard", "Insights Narrative"):
    _insights_narrative(
      provincial_year, quarterly_df, overview_muni_label,
      fancy_forecast=forecast_3months_fancy,
      regular_forecast=forecast_variety_3months,
    )

  # Footer
  st.markdown("""
  <div style="text-align: center; padding: 10px 0 5px 0; font-size: 0.75rem; color: #9CA3AF; border-top: 1px solid #E5E7EB; margin-top: 10px;">
    <i class="material-symbols-outlined" style="font-size:14px; vertical-align:middle; margin-right:6px; color:#9CA3AF;">agriculture</i> Bataan Rice Monitoring System • Data-driven insights for sustainable agriculture • v2.0
  </div>
  """, unsafe_allow_html=True)
