import numpy as np

def feature_engineering_variety(provincial_df):
    # Make a copy so original data is not changed
    df = provincial_df.copy()

    # Check if date column exists
    if "date" in df.columns:
        # Get month number from date (1 to 12)
        df["month_num"] = df["date"].dt.month

        # Simple order number for time
        df["year_index"] = range(len(df))

        # Convert month to sine form for season pattern
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"] / 12)

        # Convert month to cosine form for season pattern
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"] / 12)

    # Keep quarter column if it exists
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"]

    # Check if other variety price exists
    if "other_variety_price" in df.columns:

        # Create past 1, 2, 3 price values
        for lag in [1, 2, 3]:
            df[f"other_variety_price_lag{lag}"] = df["other_variety_price"].shift(lag)

        # Average price of last 3 rows
        df["other_variety_price_roll3"] = df["other_variety_price"].rolling(3).mean()

        # Average price of last 6 rows
        df["other_variety_price_roll6"] = df["other_variety_price"].rolling(6).mean()

        # Average price of last 12 rows
        df["other_variety_price_roll12"] = df["other_variety_price"].rolling(12).mean()

        # How much price changes in last 3 rows
        df["other_variety_price_std3"] = df["other_variety_price"].rolling(3).std()

        # Difference between current and previous price
        df["other_variety_price_change"] = df["other_variety_price"].diff()

    # Check if production and harvest data exist
    if "production_total" in df.columns and "harvested_total" in df.columns:

        # Compute yield per hectare
        df["yield_per_ha"] = df["production_total"] / df["harvested_total"]

        # Previous production value
        df["production_lag1"] = df["production_total"].shift(1)

    # Check if yield exists
    if "yield_per_ha" in df.columns:

        # Create past yield values (1 to 3 steps ago)
        for lag in [1, 2, 3]:
            df[f"yield_lag{lag}"] = df["yield_per_ha"].shift(lag)

        # Average yield of last 3 rows
        df["yield_roll3"] = df["yield_per_ha"].rolling(3).mean()

        # Variation of yield in last 3 rows
        df["yield_std3"] = df["yield_per_ha"].rolling(3).std()

    # Interaction between price and yield
    if "other_variety_price_lag1" in df.columns and "yield_per_ha" in df.columns:
        df["price_x_yield"] = df["other_variety_price_lag1"] * df["yield_per_ha"]

    # Remove rows with missing values caused by lag/rolling
    df = df.dropna().reset_index(drop=True)

    # Remove columns that are not used in model input
    df_features = df.drop(columns=[
        "date",
        "other_variety_price",
        "fancy_palay_price"
    ], errors="ignore")

    return df, df_features