import numpy as np

def feature_engineering_municipal(perMunicipality_df):
    # Make a copy of the data so the original dataset is not modified
    df = perMunicipality_df.copy()

    # -----------------------------
    # TIME FEATURES
    # -----------------------------
    if "date" in df.columns:

        # Month number (1-12)
        df["month_num"] = df["date"].dt.month

        # Continuous time index
        df["year_index"] = np.arange(len(df))

        # Cyclical month encoding
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"] / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"] / 12)

    # Keep quarter if available
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
    # FEATURE ENGINEERING
    # -----------------------------
    for col in price_columns:

        if col not in df.columns:
            continue

        # Previous values
        for lag in [1, 2, 3]:
            df[f"{col}_lag{lag}"] = df[col].shift(lag)

        # Previous year's value
        df[f"{col}_lag12"] = df[col].shift(12)

        # Rolling averages
        df[f"{col}_roll3"] = df[col].rolling(window=3).mean()
        df[f"{col}_roll6"] = df[col].rolling(window=6).mean()
        df[f"{col}_roll12"] = df[col].rolling(window=12).mean()

        # Rolling variability
        df[f"{col}_std3"] = df[col].rolling(window=3).std()

        # Month-to-month price change
        df[f"{col}_change"] = df[col].diff()

    # -----------------------------
    # REMOVE ROWS WITH NaN
    # -----------------------------
    # Lag and rolling features create missing values
    df = df.dropna().reset_index(drop=True)

    # -----------------------------
    # PREPARE FEATURES
    # -----------------------------
    # Remove only the date column.
    # Target variables will be separated during model training.
    df_features = df.drop(columns=["date"], errors="ignore")

    return df, df_features