import numpy as np
import pandas as pd

def feature_engineering_municipal(perMunicipality_df):
    # Make a copy so original is not modified
    df = perMunicipality_df.copy()
    # Normalize columns: lowercase + stripped -> fixes "Municipality" vs "municipality"
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Strict sort first -> correct time order per municipality
    sort_cols = [c for c in ["municipality", "year", "month_num", "date"] if c in df.columns]
    if sort_cols:
        df = df.sort_values(sort_cols).reset_index(drop=True)

    # -----------------------------
    # TIME FEATURES
    # -----------------------------
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df["month_num"] = df["date"].dt.month
        df["year_index"] = np.arange(len(df))
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"] / 12)

    if "quarter" in df.columns:
        df["quarter"] = df["quarter"]

    # -----------------------------
    # TARGET PRICE COLUMNS
    # -----------------------------
    price_columns = [
        "hybridpremium_dry",
        "hybridpremium_wet",
        "hybridordinary_dry",
        "hybridordinary_wet",
        "inbredpremium_dry",
        "inbredpremium_wet",
        "inbredordinary_dry",
        "inbredordinary_wet"
    ]

    # -----------------------------
    # FEATURE ENGINEERING - per municipality, no leakage
    # -----------------------------
    for col in price_columns:
        if col not in df.columns:
            continue
        df[col] = pd.to_numeric(df[col], errors="coerce")

        if "municipality" in df.columns:
            g = df.groupby("municipality")[col]
            # Lags per town
            df[f"{col}_lag1"] = g.shift(1)
            df[f"{col}_lag2"] = g.shift(2)
            df[f"{col}_lag12"] = g.shift(12)
            # Rolling means with shift(1) -> strictly prevent target leakage
            df[f"{col}_rolling_mean_3"] = g.shift(1).rolling(3).mean().reset_index(level=0, drop=True)
            df[f"{col}_rolling_mean_6"] = g.shift(1).rolling(6).mean().reset_index(level=0, drop=True)
            # Keep old names for backward compatibility
            df[f"{col}_roll3"] = df[f"{col}_rolling_mean_3"]
            df[f"{col}_roll6"] = df[f"{col}_rolling_mean_6"]
            # Also create lag3 for compatibility if needed
            df[f"{col}_lag3"] = g.shift(3)
        else:
            df[f"{col}_lag1"] = df[col].shift(1)
            df[f"{col}_lag2"] = df[col].shift(2)
            df[f"{col}_lag12"] = df[col].shift(12)
            df[f"{col}_rolling_mean_3"] = df[col].shift(1).rolling(3).mean()
            df[f"{col}_rolling_mean_6"] = df[col].shift(1).rolling(6).mean()
            df[f"{col}_roll3"] = df[f"{col}_rolling_mean_3"]
            df[f"{col}_roll6"] = df[f"{col}_rolling_mean_6"]
            df[f"{col}_lag3"] = df[col].shift(3)

    # Handle NaNs per group with bfill().ffill() - not drop all
    lag_roll_cols = [c for c in df.columns if any(x in c for x in ["lag", "rolling", "roll"])]
    for col in lag_roll_cols:
        if "municipality" in df.columns:
            df[col] = df.groupby("municipality")[col].transform(lambda s: s.bfill().ffill())
        else:
            df[col] = df[col].bfill().ffill()

    # Drop only rows where all price originals are NaN (keep max data)
    valid_price_cols = [c for c in price_columns if c in df.columns]
    if valid_price_cols:
        df = df.dropna(subset=valid_price_cols, how="all").reset_index(drop=True)
    # Fill any remaining NaNs
    df = df.fillna(0)

    # Prepare features - drop only date
    df_features = df.drop(columns=["date"], errors="ignore")

    return df, df_features
