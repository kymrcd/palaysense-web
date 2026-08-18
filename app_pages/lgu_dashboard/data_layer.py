"""
PalaySense LGU Dashboard — Data Layer
=====================================
Thin wrapper around `reload_dashboard_data()` that computes all derived
metrics (totals, comparisons, year filtering) so the UI stays clean.
Reuses the existing backend — no changes to forecasting/models.

All helpers are defensive: they return safe fallbacks instead of raising
when DataFrames are empty, columns are missing, or values are NaN.
"""
import numpy as np
import pandas as pd
from data.Dashboard_Ready import reload_dashboard_data

# ------------------------------------------------------------------
# DATA ACCESS
# ------------------------------------------------------------------
def load_dashboard():
    """Return the raw backend dashboard bundle (cached by Dashboard_Ready)."""
    return reload_dashboard_data()


def get_provincial_df(dr):
    if dr is None or dr.provincial_df is None:
        return pd.DataFrame()
    df = dr.provincial_df.copy()
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values("date").reset_index(drop=True)
    df["year"] = df["date"].dt.year
    df["quarter"] = df["date"].dt.quarter
    return df


def get_available_years(df):
    if df is None or df.empty or "year" not in df.columns:
        return []
    return sorted(df["year"].dropna().astype(int).unique().tolist())


def get_latest_date(df):
    if df is None or df.empty or "date" not in df.columns:
        return None
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    return dates.max() if not dates.empty else None


def get_latest_month_label(df):
    latest = get_latest_date(df)
    if latest is None or pd.isna(latest):
        return "N/A"
    return latest.strftime("%b %Y")


# ------------------------------------------------------------------
# YEAR FILTERING
# ------------------------------------------------------------------
def filter_by_year(df, year):
    """Return rows for a single selected year."""
    if year is None:
        return df
    if df is None or df.empty or "year" not in df.columns:
        return pd.DataFrame()
    return df[df["year"] == year].copy()


def _safe_sum_or_mean(df, annual_col, total_col):
    """Return the appropriate production/harvest aggregate, guarding NaN."""
    if df is None or df.empty:
        return 0.0
    if annual_col in df.columns:
        val = df[annual_col].mean()
    elif total_col in df.columns:
        val = df[total_col].sum()
    else:
        return 0.0
    return 0.0 if pd.isna(val) else float(val)


def _delta(cur, prev):
    """Return (absolute_delta, pct_delta), guarding zero/NaN baselines."""
    cur = 0.0 if pd.isna(cur) else float(cur)
    prev = 0.0 if pd.isna(prev) else float(prev)
    if prev == 0:
        return cur, 0.0
    return (cur - prev), ((cur - prev) / prev) * 100


def get_year_metrics(df, year, dr):
    """Compute KPI values + year-over-year comparisons for a given year."""
    subset = filter_by_year(df, year)
    if subset.empty:
        return {
            "production": 0, "production_prev": 0,
            "harvested": 0, "harvested_prev": 0,
            "yield": 0, "yield_prev": 0,
            "prod_delta": 0, "prod_pct": 0,
            "harv_delta": 0, "harv_pct": 0,
            "yield_delta": 0, "yield_pct": 0,
        }

    # Production: annual total (scale monthly to annual via production_annual if present)
    prod = _safe_sum_or_mean(subset, "production_annual", "production_total")
    # Harvested area
    harv = _safe_sum_or_mean(subset, "harvested_annual", "harvested_total")
    # Average yield
    if "quarterly_yield_mt_per_ha" in subset.columns:
        yield_val = subset["quarterly_yield_mt_per_ha"].mean()
    else:
        yield_val = 0.0
    yield_val = 0.0 if pd.isna(yield_val) else float(yield_val)

    # Previous year comparison
    prev_year = year - 1
    prev_subset = filter_by_year(df, prev_year)
    if not prev_subset.empty:
        prod_prev = _safe_sum_or_mean(prev_subset, "production_annual", "production_total")
        harv_prev = _safe_sum_or_mean(prev_subset, "harvested_annual", "harvested_total")
        if "quarterly_yield_mt_per_ha" in prev_subset.columns:
            yield_prev = prev_subset["quarterly_yield_mt_per_ha"].mean()
        else:
            yield_prev = 0.0
        yield_prev = 0.0 if pd.isna(yield_prev) else float(yield_prev)
    else:
        prod_prev = harv_prev = yield_prev = 0

    prod_delta, prod_pct = _delta(prod, prod_prev)
    harv_delta, harv_pct = _delta(harv, harv_prev)
    yield_delta, yield_pct = _delta(yield_val, yield_prev)

    return {
        "production": prod, "production_prev": prod_prev,
        "harvested": harv, "harvested_prev": harv_prev,
        "yield": yield_val, "yield_prev": yield_prev,
        "prod_delta": prod_delta, "prod_pct": prod_pct,
        "harv_delta": harv_delta, "harv_pct": harv_pct,
        "yield_delta": yield_delta, "yield_pct": yield_pct,
    }


# ------------------------------------------------------------------
# FORECAST PERIOD (3-month municipal-level rolling window)
# ------------------------------------------------------------------
def get_forecast_period(dr):
    """Return (start_label, end_label, months) for the rolling forecast window.

    Municipal/LGU forecasts are strictly 3 months. Anchored to the latest
    historical provincial date (dynamic), never the system clock.
    """
    months = 3
    latest = None
    if dr is not None and getattr(dr, "provincial_df", None) is not None:
        latest = get_latest_date(dr.provincial_df)
    if latest is None or pd.isna(latest):
        return "N/A", "N/A", months
    start = latest + pd.DateOffset(months=1)
    end = start + pd.DateOffset(months=months - 1)
    return start.strftime("%b %Y"), end.strftime("%b %Y"), months


# ------------------------------------------------------------------
# PRODUCTION TOTALS & MUNICIPAL RANKINGS
# ------------------------------------------------------------------
_MUNI_NAME_COLS = ("municipality", "Municipality", "Mun", "Area")
_MUNI_SIMPLE_PROD_COLS = (
    "palay_production", "production_total", "production",
    "volume", "production_mt", "Palay Production",
)
_MUNI_VARIETY_COLS = (
    "hybridpremium_dry", "hybridpremium_wet",
    "hybridordinary_dry", "hybridordinary_wet",
    "inbredpremium_dry", "inbredpremium_wet",
    "inbredordinary_dry", "inbredordinary_wet",
)


def _filter_by_range(df, year_range):
    """Filter df to the given (min,max) year range using 'year' or 'date'."""
    if df is None or df.empty or not year_range:
        return pd.DataFrame()
    lo, hi = int(min(year_range)), int(max(year_range))
    loc = df.copy()
    if "year" in loc.columns:
        years = pd.to_numeric(loc["year"], errors="coerce")
        return loc[years.between(lo, hi)]
    if "date" in loc.columns:
        yrs = pd.to_datetime(loc["date"], errors="coerce").dt.year
        return loc[yrs.between(lo, hi)]
    return loc


def _municipal_production_series(df):
    """Total palay production (MT) per municipality as a Series."""
    muni_col = next((c for c in _MUNI_NAME_COLS if c in df.columns), None)
    if muni_col is None:
        return pd.Series(dtype="float64", name="palay_production")
    simple = next((c for c in _MUNI_SIMPLE_PROD_COLS if c in df.columns), None)
    if simple is not None:
        return (
            df.groupby(muni_col)[simple].sum(numeric_only=True)
            .astype(float)
            .rename("palay_production")
        )
    cols = [c for c in _MUNI_VARIETY_COLS if c in df.columns]
    if not cols:
        return pd.Series(dtype="float64", name="palay_production")
    return (
        df.groupby(muni_col)[cols].sum(numeric_only=True)
        .sum(axis=1).astype(float)
        .rename("palay_production")
    )


def get_total_production(df, year_range):
    """Total historical/current palay production (MT) summed across the year range.

    Provincial frames use the per-year annual total (``production_annual``) so the
    repeated monthly rows are NOT double counted; municipal/variety-season frames
    are summed across all matching rows. Returns ``None`` when no usable data
    exists so callers can show "No Data Available" instead of ``0 MT``.
    """
    if df is None or df.empty or not year_range:
        return None

    sub = _filter_by_range(df, year_range)
    if sub.empty:
        return None

    # 1) Provincial-style annual / total columns -> mean per year
    for col in ("production_annual", "production_total"):
        if col in sub.columns:
            if "year" in sub.columns:
                per_year = sub.groupby("year")[col].mean(numeric_only=True).dropna()
            else:
                per_year = pd.Series([pd.to_numeric(sub[col], errors="coerce").sum()])
            per_year = per_year[per_year > 0]
            return float(per_year.sum()) if not per_year.empty else None

    # 2) Municipal variety/season columns -> direct sum of all rows
    prod = _municipal_production_series(sub)
    if prod.empty:
        return None
    total = float(prod.sum())
    return total if total > 0 else None


def get_top_5_producing_municipalities(df, year_range):
    """Top-5 municipalities by total historical palay production (MT).

    Groups production by municipality, sums it across the selected years and
    returns an empty DataFrame (with :code:`municipality`, ``palay_production``,
    ``rank``) when there is no data instead of raising.
    """
    empty = pd.DataFrame(columns=["municipality", "palay_production", "rank"])
    if df is None or df.empty or not year_range:
        return empty

    loc = _filter_by_range(df, year_range)
    if loc.empty:
        return empty

    s = _municipal_production_series(loc)
    if s.empty:
        return empty
    s = s[s > 0].sort_values(ascending=False)
    if s.empty:
        return empty

    top = s.head(5)
    out = pd.DataFrame({
        "municipality": top.index.astype(str),
        "palay_production": np.round(top.to_numpy(dtype=float), 2),
    })
    out["rank"] = range(1, len(out) + 1)
    return out


def get_municipal_seasonal_production(df, year_range, season="dry", top_n=5):
    """Top-N municipalities by dry/wet seasonal production within a year range."""
    empty = pd.DataFrame(columns=["municipality", "production"])
    if df is None or df.empty or not year_range:
        return empty

    loc = _filter_by_range(df, year_range)
    if loc.empty:
        return empty

    muni_col = next((c for c in _MUNI_NAME_COLS if c in loc.columns), None)
    if muni_col is None:
        return empty
    suffix = "_wet" if str(season).lower().startswith("wet") else "_dry"
    season_col = "wet_season" if suffix == "_wet" else "dry_season"
    if season_col in loc.columns:
        s = loc.groupby(muni_col)[season_col].sum(numeric_only=True)
    else:
        cols = [c for c in _MUNI_VARIETY_COLS if c.endswith(suffix) and c in loc.columns]
        if not cols:
            return empty
        s = loc.groupby(muni_col)[cols].sum(numeric_only=True).sum(axis=1)
    s = s[s > 0].sort_values(ascending=False)
    if s.empty:
        return empty

    top = s.head(top_n)
    return pd.DataFrame({
        "municipality": top.index.astype(str),
        "production": np.round(top.to_numpy(dtype=float), 2),
    })


# ------------------------------------------------------------------
# QUARTERLY SERIES (for charts)
# ------------------------------------------------------------------
def get_quarterly_yield(df):
    if df is None or df.empty or "quarterly_yield_mt_per_ha" not in df.columns:
        return pd.DataFrame(columns=[
            "year", "quarter", "quarterly_yield_mt_per_ha", "date_q", "quarter_label"
        ])
    q = df.groupby(["year", "quarter"])["quarterly_yield_mt_per_ha"].mean().reset_index()
    if q.empty:
        return q
    q["date_q"] = pd.PeriodIndex(
        q["year"].astype(str) + "Q" + q["quarter"].astype(str), freq="Q"
    ).to_timestamp()
    q["quarter_label"] = "Q" + q["quarter"].astype(str) + " " + q["year"].astype(str)
    q = q.sort_values("date_q")
    return q


def get_monthly_price(df):
    """Monthly price history as a DataFrame."""
    if df is None or df.empty:
        return pd.DataFrame(columns=["date", "fancy_palay_price", "other_variety_price"])
    return df[["date", "fancy_palay_price", "other_variety_price"]].dropna().copy()


def get_supply_status(dr, year):
    supply = getattr(dr, "supply_df", None)
    if supply is None or getattr(supply, "empty", True):
        return "No data", "N/A"
    if "net_production_clean_rice" not in supply.columns or "actual_consumption" not in supply.columns:
        return "No data", "N/A"
    s = supply.copy()
    s["date"] = pd.to_datetime(s["date"], errors="coerce")
    s = s[s["date"].dt.year == year]
    if s.empty:
        return "No data", "N/A"
    # Guard against zero/NaN consumption denominators (prevent inf / NaN ratios)
    denom = pd.to_numeric(s["actual_consumption"], errors="coerce").replace(0, np.nan)
    ratios = (pd.to_numeric(s["net_production_clean_rice"], errors="coerce") / denom * 100).dropna()
    if ratios.empty:
        return "No data", "N/A"
    ratio = float(ratios.mean())
    if ratio > 105:
        return "Surplus", ratio
    if ratio < 95:
        return "Deficit", ratio
    return "Balanced", ratio
