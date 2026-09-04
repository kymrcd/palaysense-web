import numpy as np

def feature_engineering_variety(provincial_df):
    # Make a copy so original data is not changed
    df = provincial_df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

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

        # Create past 1, 2, 3, 4, 5, 6 price values
        for lag in [1, 2, 3, 4, 5, 6]:
            df[f"other_variety_price_lag{lag}"] = (
                df["other_variety_price"].shift(lag)
            )

        #12-month lag
        df["other_variety_price_lag12"] = (
            df["other_variety_price"].shift(12)
        )

        # -----------------------------------------------------
        # ROLLING FEATURES
        # IMPORTANT:
        # shift(1) prevents current-price data leakage
        # -----------------------------------------------------
        df["other_variety_price_roll3"] = (
            df["other_variety_price"]
            .shift(1)
            .rolling(3)
            .mean()
        )

        df["other_variety_price_roll6"] = (
            df["other_variety_price"]
            .shift(1)
            .rolling(6)
            .mean()
        )

        df["other_variety_price_roll12"] = (
            df["other_variety_price"]
            .shift(1)
            .rolling(12)
            .mean()
        )

        #price variability
        df["other_variety_price_std3"] = (
            df["other_variety_price"]
            .shift(1)
            .rolling(3)
            .std()
        )

        #Price Change
        df["other_variety_price_change"] = (
                df["other_variety_price"].shift(1)
                - df["other_variety_price"].shift(2)
        )

    #YIELD FEATURES

    # Check if production and harvest data exist
    if (
        "production_total" in df.columns
        and "harvested_total" in df.columns
    ):

        #Yield per hectare
        df["yield_per_ha"] = (
            df["production_total"]/
            df["harvested_total"]
        )

        #Previous production
        df["production_lag1"] = (
            df["production_total"].shift(1)
        )

    #Previous Yield Features and checking if it exists in dataset
    if "yield_per_ha" in df.columns:
        for lag in [1, 2, 3]:
            df[f"yield_lag{lag}"] = (
                df["yield_per_ha"].shift(lag)
            )

        df["yield_roll3"] = (
            df["yield_per_ha"]
            .shift(1)
            .rolling(3)
            .mean()
        )

        df["yield_std3"] = (
            df["yield_per_ha"]
            .shift(1)
            .rolling(3)
            .std()
        )

    # Interaction between price and yield
    if (
        "other_variety_price_lag1" in df.columns
        and "yield_per_ha" in df.columns
    ):
        df["price_x_yield"] = (
            df["other_variety_price_lag1"]
            * df["yield_per_ha"]
        )

    #Remove Missing Values
    df = (
        df
        .dropna()
        .reset_index(drop=True)
    )

    #Creare ML Features DataFrame
    df_features = df.drop(columns=[
        "date",
        "fancy_palay_price",
        "other_variety_price"
    ], errors = "ignore")

    return df, df_features