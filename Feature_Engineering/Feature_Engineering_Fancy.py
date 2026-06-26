import numpy as np

def feature_engineering_fancy(provincial_df):
    # Make a copy of the data so original file is not changed
    df = provincial_df.copy()

    # Get time-related information if date column exists
    if "date" in df.columns:
        # Get month number from date (1 to 12)
        df["month_num"] = df["date"].dt.month

        # Create a simple time order number
        df["year_index"] = range(len(df))

        # Make month usable for season pattern (sine form)
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"] / 12)

        # Make month usable for season pattern (cosine form)
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"] / 12)

    # Keep quarter value if it exists
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"]

    # Check if price column exists
    if "fancy_palay_price" in df.columns:

        # Create past 1, 2, 3 values of price
        for lag in [1, 2, 3]:
            df[f"fancy_palay_price_lag{lag}"] = df["fancy_palay_price"].shift(lag)

        # Create value from 12 steps ago (yearly pattern)
        df["fancy_palay_price_lag12"] = df["fancy_palay_price"].shift(12)

        # Average price of last 3 steps
        df["fancy_palay_price_roll3"] = df["fancy_palay_price"].rolling(3).mean()

        # Average price of last 6 steps
        df["fancy_palay_price_roll6"] = df["fancy_palay_price"].rolling(6).mean()

        # Average price of last 12 steps
        df["fancy_palay_price_roll12"] = df["fancy_palay_price"].rolling(12).mean()

        # How much price changes in 3 steps
        df["fancy_palay_price_std3"] = df["fancy_palay_price"].rolling(3).std()

        # Difference between current and previous price
        df["fancy_palay_price_change"] = df["fancy_palay_price"].diff()

    # Check if production and harvest data exist
    if "production_total" in df.columns and "harvested_total" in df.columns:

        # Compute yield per hectare (production divided by land)
        df["yield_per_ha"] = df["production_total"] / df["harvested_total"]

        # Previous production value
        df["production_lag1"] = df["production_total"].shift(1)

    # Check if yield exists
    if "yield_per_ha" in df.columns:

        # Create past yield values (1 to 3 steps ago)
        for lag in [1, 2, 3]:
            df[f"yield_lag{lag}"] = df["yield_per_ha"].shift(lag)

        # Average yield of last 3 steps
        df["yield_roll3"] = df["yield_per_ha"].rolling(3).mean()

        # Variation of yield in last 3 steps
        df["yield_std3"] = df["yield_per_ha"].rolling(3).std()

    # Combine price and yield information
    if "fancy_palay_price_lag1" in df.columns and "yield_per_ha" in df.columns:
        df["price_x_yield"] = df["fancy_palay_price_lag1"] * df["yield_per_ha"]

    # Remove rows with missing values caused by lag and rolling
    df = df.dropna().reset_index(drop=True)

    # Remove columns that should not be used in model input
    df_features = df.drop(columns=[
        "date",
        "fancy_palay_price",
        "other_variety_price"
    ], errors="ignore")

    return df, df_features