#!/usr/bin/env python3
"""
PalaySense — Background Training & Inference Pipeline
======================================================
Run this script separately (e.g., via cron, CI/CD, or manual trigger)
to train models, generate forecasts, and write lightweight Parquet outputs.

Usage:
    python scripts/run_pipeline.py [--provincial PATH] [--municipal PATH] [--output-dir PATH]

Outputs (written to data/forecasts/):
    - provincial_history.parquet      # Historical provincial data (cleaned)
    - municipal_history.parquet       # Historical municipal data (cleaned)
    - supply_data.parquet             # Supply/demand data
    - provincial_forecasts.parquet    # 6-month fancy + 6-month regular + 4-quarter yield
    - municipal_forecasts.parquet     # 3-month forecasts per municipality/rice-type/season (with month labels)
    - municipal_forecasts_test.parquet    # 3-month test-period predictions
    - municipal_forecasts_forward.parquet # 3-month forward predictions (with month labels)
    - metrics.json                    # Model performance metrics (MAE, RMSE, R²)
    - forecast_metadata.json          # Forecast horizon, last_date, generated_at
"""
import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import numpy as np
import joblib

# Force UTF-8 stdout/stderr so non-ASCII prints (₱, ², subscripts, etc.) never
# crash on Windows cp1252 consoles or in the upload-page subprocess.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---- ML Pipeline Imports ----
from Exploratory_Data_Analysis.EDA_Capstone import run_eda
from Exploratory_Data_Analysis.EDA_Municipality import run_eda_municipality

from Feature_Engineering.Feature_Engineering_Fancy import feature_engineering_fancy
from Feature_Engineering.Feature_Engineering_Variety import feature_engineering_variety
from Feature_Engineering.Feature_Engineering_Yield import feature_engineering_yield
from Feature_Engineering.Feature_Engineering_Municipality import feature_engineering_municipal

from ml_Price_Forecast.train_test_split_fancy import train_price_fancy
from ml_Price_Forecast.train_test_split_variety import train_variety_price
from ml_Yield_Forecast.train_test_split_yield import train_yield
from ml_Municipal_Forecast.train_test_split_Municipal import train_price_Municipal

from ml_Price_Forecast.Forecast_Price_Fancy import forecast_next_3_months
from ml_Price_Forecast.Forecast_Price_OtherVariety import forecast_next_3_months_variety
from ml_Yield_Forecast.forecast_yield import forecast_4quarters_yield
from ml_Municipal_Forecast.Forecast_Price_Municipal import forecast_3_months_M


# =========================
# CONFIGURATION
# =========================
DEFAULT_PROVINCIAL = PROJECT_ROOT / "data" / "cleaned" / "provincial_cleaned.xlsx"
DEFAULT_MUNICIPAL = PROJECT_ROOT / "data" / "cleaned" / "municipality_cleaned.xlsx"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "forecasts"

FORECAST_HORIZON_MONTHS = 6   # Fancy & Regular price forecasts
FORECAST_HORIZON_QUARTERS = 4 # Yield forecasts
MUNICIPAL_FORECAST_MONTHS = 3 # Municipal forecasts


# =========================
# HELPERS
# =========================
def _ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def _get_last_date(df: pd.DataFrame, date_col: str = "date") -> pd.Timestamp:
    """Get the last valid date from a dataframe."""
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
    return dates.max() if not dates.empty else pd.Timestamp.now()


def _generate_forecast_months(last_date: pd.Timestamp, periods: int) -> list[str]:
    """Generate forecast month labels (e.g., 'January 2025')."""
    import calendar
    months = []
    month = last_date.month
    year = last_date.year
    for _ in range(periods):
        month = (month % 12) + 1
        if month == 1:
            year += 1
        months.append(f"{calendar.month_name[month]} {year}")
    return months


def _generate_forecast_quarters(last_date: pd.Timestamp, periods: int) -> list[str]:
    """Generate forecast quarter labels (e.g., 'Q1 2025')."""
    quarters = []
    q = (last_date.month - 1) // 3 + 1
    year = last_date.year
    for _ in range(periods):
        q = (q % 4) + 1
        if q == 1:
            year += 1
        quarters.append(f"Q{q} {year}")
    return quarters


def _fit_horizon(values, n: int) -> list:
    """Pad or truncate a forecast sequence to exactly ``n`` entries.

    Guarantees the unified provincial parquet never has a shape mismatch:
    a too-short forecast is NaN-padded, a too-long one is truncated.
    """
    vals = list(values) if values is not None else []
    if len(vals) > n:
        return vals[:n]
    return vals + [np.nan] * (n - len(vals))


def _validate_outputs(output_dir: Path) -> None:
    """Sanity-check horizons/shapes of the parquet outputs."""
    prov_path = output_dir / "provincial_forecasts.parquet"
    muni_path = output_dir / "municipal_forecasts.parquet"
    issues = []

    if prov_path.exists():
        prov = pd.read_parquet(prov_path)
        n_fancy = int((prov["forecast_type"] == "fancy").sum())
        n_regular = int((prov["forecast_type"] == "regular").sum())
        n_yield = int((prov["forecast_type"] == "yield").sum())
        if n_fancy != FORECAST_HORIZON_MONTHS:
            issues.append(f"provincial fancy horizon mismatch: {n_fancy} (expected {FORECAST_HORIZON_MONTHS})")
        if n_regular != FORECAST_HORIZON_MONTHS:
            issues.append(f"provincial regular horizon mismatch: {n_regular} (expected {FORECAST_HORIZON_MONTHS})")
        if n_yield != FORECAST_HORIZON_QUARTERS:
            issues.append(f"provincial yield horizon mismatch: {n_yield} (expected {FORECAST_HORIZON_QUARTERS})")
        print(f"[Pipeline] Validation: provincial rows={len(prov)} "
              f"(fancy={n_fancy}, regular={n_regular}, yield={n_yield})")
    else:
        issues.append("provincial_forecasts.parquet missing")

    if muni_path.exists():
        muni = pd.read_parquet(muni_path)
        for col in ["Municipality", "Rice Type & Season", "Month 1", "Month 2", "Month 3"]:
            if col not in muni.columns:
                issues.append(f"municipal_forecasts.parquet missing column: {col}")
        print(f"[Pipeline] Validation: municipal rows={len(muni)} (3-month horizon)")
    else:
        issues.append("municipal_forecasts.parquet missing")

    if issues:
        for msg in issues:
            print(f"[Pipeline] ⚠️ VALIDATION WARNING: {msg}")
    else:
        print("[Pipeline] ✅ Validation passed: provincial 6-month price + 4-quarter yield, municipal 3-month.")


# =========================
# MAIN PIPELINE
# =========================
def run_pipeline(
    provincial_path: Path,
    municipal_path: Path,
    output_dir: Path,
) -> dict:
    """
    Execute the full training + inference pipeline and write Parquet outputs.
    Returns a dict with paths to generated files and metadata.
    """
    _ensure_dir(output_dir)
    print(f"[Pipeline] Output directory: {output_dir}")

    # ------------------------------------------------------------------
    # 1. EDA — Load and clean data
    # ------------------------------------------------------------------
    print("[Pipeline] Running EDA...")
    provincial_df, supply_df, municipality_df = run_eda(str(provincial_path))
    perMunicipality_df = run_eda_municipality(str(municipal_path))

    # Save historical data (cleaned, ready for UI)
    provincial_df.to_parquet(output_dir / "provincial_history.parquet", index=False)
    perMunicipality_df.to_parquet(output_dir / "municipal_history.parquet", index=False)
    supply_df.to_parquet(output_dir / "supply_data.parquet", index=False)
    print(f"[Pipeline] Saved historical data ({len(provincial_df)} provincial, {len(perMunicipality_df)} municipal rows)")

    # ------------------------------------------------------------------
    # 2. Feature Engineering
    # ------------------------------------------------------------------
    print("[Pipeline] Running Feature Engineering...")
    df_fancy, df_features_fancy = feature_engineering_fancy(provincial_df)
    df_regular, df_features_regular = feature_engineering_variety(provincial_df)
    df_yield, df_features_yield = feature_engineering_yield(provincial_df)
    df_municipal, df_features_municipal = feature_engineering_municipal(perMunicipality_df)

    # ------------------------------------------------------------------
    # 3. Training & Forecasting — Provincial (Fancy, Regular, Yield)
    # ------------------------------------------------------------------
    print("[Pipeline] Training Provincial models...")

    # Fancy Palay
    res_fancy = train_price_fancy(df_fancy)
    regressor_fancy = res_fancy["model"]
    model_name_fancy = res_fancy["model_name"]
    bias_fancy = res_fancy["bias"]
    forecast_fancy = forecast_next_3_months(
        regressor_fancy, df_fancy, df_features_fancy, bias_fancy, model_name_fancy
    )

    # Regular Palay
    res_regular = train_variety_price(df_regular)
    regressor_regular = res_regular["model"]
    model_name_regular = res_regular["model_name"]
    bias_regular = res_regular["bias"]
    forecast_regular = forecast_next_3_months_variety(
        regressor_regular, df_regular, df_features_regular, bias_regular, model_name_regular
    )

    # Yield
    res_yield = train_yield(df_yield)
    regressor_yield = res_yield["model"]
    model_name_yield = res_yield["model_name"]
    bias_yield = res_yield["bias"]
    forecast_yield = forecast_4quarters_yield(regressor_yield, df_features_yield, bias_yield)

    # ------------------------------------------------------------------
    # 4. Training & Forecasting — Municipal
    # ------------------------------------------------------------------
    print("[Pipeline] Training Municipal models...")
    municipal_results, df_municipal_forecasts = train_price_Municipal(df_features_municipal)

    # The municipal forecasts are already generated inside train_price_Municipal
    # (last 3 months of test predictions). We also generate true forward forecasts.
    print("[Pipeline] Generating forward municipal forecasts...")
    municipal_forward_forecasts = []
    municipalities = perMunicipality_df["municipality"].unique()
    target_columns = [
        "hybridpremium_dry", "hybridpremium_wet",
        "hybridordinary_dry", "hybridordinary_wet",
        "inbredpremium_dry", "inbredpremium_wet",
        "inbredordinary_dry", "inbredordinary_wet"
    ]

    for muni in municipalities:
        muni_hist = perMunicipality_df[perMunicipality_df["municipality"] == muni].copy()
        last_date = _get_last_date(muni_hist)
        month_labels = _generate_forecast_months(last_date, MUNICIPAL_FORECAST_MONTHS)

        for target in target_columns:
            if muni in municipal_results and target in municipal_results[muni]:
                try:
                    months, forecasts = forecast_3_months_M(
                        municipal_results, df_municipal, muni, target
                    )
                    municipal_forward_forecasts.append({
                        "Municipality": muni.upper(),
                        "Rice Type & Season": target,
                        "Month 1": round(forecasts[0], 2) if len(forecasts) > 0 else None,
                        "Month 2": round(forecasts[1], 2) if len(forecasts) > 1 else None,
                        "Month 3": round(forecasts[2], 2) if len(forecasts) > 2 else None,
                        "forecast_month_1_label": month_labels[0] if len(month_labels) > 0 else None,
                        "forecast_month_2_label": month_labels[1] if len(month_labels) > 1 else None,
                        "forecast_month_3_label": month_labels[2] if len(month_labels) > 2 else None,
                    })
                except Exception as e:
                    print(f"[Pipeline] Warning: Failed to forecast {muni} / {target}: {e}")

    df_municipal_forward = pd.DataFrame(municipal_forward_forecasts)

    # Guarantee every municipal row has exactly 3 forecast months.
    # Missing forward forecasts fall back to the test-period predictions.
    if df_municipal_forward.empty and not df_municipal_forecasts.empty:
        df_municipal_forward = df_municipal_forecasts.copy()

    # Combine the test-period forecasts (from training) with forward forecasts.
    # The UI expects the test-period format, so we save both.
    df_municipal_forecasts.to_parquet(output_dir / "municipal_forecasts_test.parquet", index=False)
    df_municipal_forward.to_parquet(output_dir / "municipal_forecasts_forward.parquet", index=False)

    # Primary UI file = 3-month forward forecast with month labels.
    # (Columns Municipality / Rice Type & Season / Month 1-3 are preserved so
    #  existing dashboard filtering continues to work unchanged.)
    df_municipal_forward.to_parquet(output_dir / "municipal_forecasts.parquet", index=False)

    print(f"[Pipeline] Saved municipal forecasts ({len(df_municipal_forecasts)} test-period, {len(df_municipal_forward)} forward)")

    # ------------------------------------------------------------------
    # 5. Provincial Forecasts — Create unified Parquet
    # ------------------------------------------------------------------
    # Horizons are strictly enforced here: 6-month Fancy, 6-month Regular,
    # 4-quarter Yield. Any deviation is padded/truncated so the unified
    # parquet always has aligned (forecast_type, period_label, forecast_value).
    last_prov_date = _get_last_date(provincial_df)
    fancy_month_labels = _generate_forecast_months(last_prov_date, FORECAST_HORIZON_MONTHS)
    regular_month_labels = fancy_month_labels  # same horizon
    yield_quarter_labels = _generate_forecast_quarters(last_prov_date, FORECAST_HORIZON_QUARTERS)

    fancy_values = _fit_horizon(forecast_fancy, FORECAST_HORIZON_MONTHS)
    regular_values = _fit_horizon(forecast_regular, FORECAST_HORIZON_MONTHS)
    yield_values = _fit_horizon(forecast_yield, FORECAST_HORIZON_QUARTERS)

    provincial_forecasts = pd.DataFrame({
        "forecast_type": (["fancy"] * len(fancy_values)
                          + ["regular"] * len(regular_values)
                          + ["yield"] * len(yield_values)),
        "period_label": (fancy_month_labels + regular_month_labels + yield_quarter_labels),
        "forecast_value": fancy_values + regular_values + yield_values,
    })
    provincial_forecasts.to_parquet(output_dir / "provincial_forecasts.parquet", index=False)
    print(f"[Pipeline] Saved provincial forecasts ({len(provincial_forecasts)} rows: "
          f"{len(fancy_values)} fancy, {len(regular_values)} regular, {len(yield_values)} yield)")

    # ------------------------------------------------------------------
    # 6. Metrics & Metadata
    # ------------------------------------------------------------------
    metrics = {
        "fancy": {
            "model_name": res_fancy["model_name"],
            "mae": float(res_fancy["mae"]),
            "rmse": float(res_fancy["rmse"]),
            "r2": float(res_fancy["r2"]),
            "mape": float(res_fancy["mape"]),
            "bias": float(res_fancy["bias"]),
            "baselines": res_fancy["baselines"],
            "walk_forward": res_fancy["walk_forward"],
        },
        "regular": {
            "model_name": res_regular["model_name"],
            "mae": float(res_regular["mae"]),
            "rmse": float(res_regular["rmse"]),
            "r2": float(res_regular["r2"]),
            "mape": float(res_regular["mape"]),
            "bias": float(res_regular["bias"]),
            "baselines": res_regular["baselines"],
            "walk_forward": res_regular["walk_forward"],
        },
        "yield": {
            "model_name": res_yield["model_name"],
            "mae": float(res_yield["mae"]),
            "rmse": float(res_yield["rmse"]),
            "r2": float(res_yield["r2"]),
            "mape": float(res_yield["mape"]),
            "bias": float(res_yield["bias"]),
            "baselines": res_yield["baselines"],
            "walk_forward": res_yield["walk_forward"],
        },
    }

    # Municipal aggregate metrics
    muni_metrics = {}
    for muni, targets in municipal_results.items():
        muni_metrics[muni] = {}
        for target, res in targets.items():
            muni_metrics[muni][target] = {
                "mae": float(res["MAE"]),
                "rmse": float(res["RMSE"]),
                "r2": float(res["R2"]),
                "mape": float(res["MAPE"]),
                "bias": float(res["Bias"]),
                "baselines": res["baselines"],
                "walk_forward": res["walk_forward"],
            }
    metrics["municipal"] = muni_metrics

    with open(output_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)
    print("[Pipeline] Saved metrics.json")

    # Metadata
    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "provincial_last_date": last_prov_date.isoformat(),
        "municipal_last_date": _get_last_date(perMunicipality_df).isoformat(),
        "forecast_horizon_months": FORECAST_HORIZON_MONTHS,
        "forecast_horizon_quarters": FORECAST_HORIZON_QUARTERS,
        "municipal_forecast_months": MUNICIPAL_FORECAST_MONTHS,
        "provincial_rows": int(len(provincial_df)),
        "municipal_rows": int(len(perMunicipality_df)),
        "municipalities": sorted(municipalities.tolist()),
    }
    with open(output_dir / "forecast_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    print("[Pipeline] Saved forecast_metadata.json")

    # ------------------------------------------------------------------
    # 7. Save Municipal Models (for future inference without retraining)
    # ------------------------------------------------------------------
    models_dir = PROJECT_ROOT / "data" / "models"
    _ensure_dir(models_dir)
    joblib.dump(municipal_results, models_dir / "municipality_models.pkl")
    print("[Pipeline] Saved municipality_models.pkl")

    # ------------------------------------------------------------------
    # 8. Validation — verify forecast horizons & output shapes
    # ------------------------------------------------------------------
    _validate_outputs(output_dir)

    print("\n[Pipeline] ✅ Pipeline completed successfully!")
    return {
        "provincial_history": str(output_dir / "provincial_history.parquet"),
        "municipal_history": str(output_dir / "municipal_history.parquet"),
        "supply_data": str(output_dir / "supply_data.parquet"),
        "provincial_forecasts": str(output_dir / "provincial_forecasts.parquet"),
        "municipal_forecasts": str(output_dir / "municipal_forecasts.parquet"),
        "municipal_forecasts_forward": str(output_dir / "municipal_forecasts_forward.parquet"),
        "metrics": str(output_dir / "metrics.json"),
        "metadata": str(output_dir / "forecast_metadata.json"),
    }


# =========================
# CLI ENTRY POINT
# =========================
def main():
    parser = argparse.ArgumentParser(description="PalaySense Forecasting Pipeline")
    parser.add_argument("--provincial", type=Path, default=DEFAULT_PROVINCIAL,
                        help="Path to provincial cleaned Excel file")
    parser.add_argument("--municipal", type=Path, default=DEFAULT_MUNICIPAL,
                        help="Path to municipal cleaned Excel file")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Directory to write Parquet outputs")
    args = parser.parse_args()

    if not args.provincial.exists():
        print(f"[Pipeline] ERROR: Provincial file not found: {args.provincial}")
        sys.exit(1)
    if not args.municipal.exists():
        print(f"[Pipeline] ERROR: Municipal file not found: {args.municipal}")
        sys.exit(1)

    run_pipeline(args.provincial, args.municipal, args.output_dir)


if __name__ == "__main__":
    main()