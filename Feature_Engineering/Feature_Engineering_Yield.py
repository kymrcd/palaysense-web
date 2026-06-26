import numpy as np  # needed for mathematical functions like sine and cosine

def feature_engineering_yield(provincial_df):

    # create a copy so the original dataset is not modified
    df = provincial_df.copy()

    # sort the data in correct time order using year and quarter
    df = df.sort_values(by=["year", "quarter"]).reset_index(drop=True)

    # check if date column exists so we can extract time features
    if "date" in df.columns:

        # extract the month from the date (values 1 to 12)
        df["month_num"] = df["date"].dt.month

        # create a simple time index to represent sequence of data
        df["year_index"] = range(len(df))

        # convert month into sine value to capture seasonal pattern
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"] / 12)

        # convert month into cosine value for full seasonal cycle encoding
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"] / 12)

    # keep quarter column if it exists in the dataset
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"]

    # create features only if yield column is available
    if "quarterly_yield_mt_per_ha" in df.columns:

        # create lag features to use past yield values as input
        for lag in [1, 2, 3, 4]:
            df[f"yield_lag{lag}"] = df["quarterly_yield_mt_per_ha"].shift(lag)

        # approximate yearly pattern by shifting 4 quarters back
        df["yield_lag12"] = df["quarterly_yield_mt_per_ha"].shift(4)

        # compute short-term average trend using last 2 quarters
        df["yield_roll2"] = df["quarterly_yield_mt_per_ha"].rolling(2).mean()

        # compute medium-term trend using last 4 quarters
        df["yield_roll4"] = df["quarterly_yield_mt_per_ha"].rolling(4).mean()

        # measure how unstable or volatile the yield is over time
        df["yield_std3"] = df["quarterly_yield_mt_per_ha"].rolling(3).std()

        # compute quarter-to-quarter percentage change in yield
        df["yield_qoq"] = df["quarterly_yield_mt_per_ha"].pct_change()

        # compare current quarter with same quarter from 1 year ago
        df["yield_yoy"] = df.groupby("quarter")["quarterly_yield_mt_per_ha"].shift(4)

    # create price-based features if fancy price exists
    if "fancy_palay_price" in df.columns:

        # add past 1 to 3 time step prices as features
        for lag in [1, 2, 3]:
            df[f"price_lag{lag}"] = df["fancy_palay_price"].shift(lag)

        # compute short-term average price trend
        df["price_roll3"] = df["fancy_palay_price"].rolling(3).mean()

        # measure how stable or unstable price is
        df["price_std3"] = df["fancy_palay_price"].rolling(3).std()

    # create price features for other rice variety if available
    if "other_variety_price" in df.columns:

        # add past price values for other variety
        for lag in [1, 2, 3]:
            df[f"variety_price_lag{lag}"] = df["other_variety_price"].shift(lag)

        # short-term trend of other variety price
        df["variety_price_roll3"] = df["other_variety_price"].rolling(3).mean()

        # volatility of other variety price
        df["variety_price_std3"] = df["other_variety_price"].rolling(3).std()

    # compute difference between two rice prices if both exist
    if all(col in df.columns for col in ["fancy_palay_price", "other_variety_price"]):
        df["price_diff"] = df["fancy_palay_price"] - df["other_variety_price"]

    # create production-based features if available
    if "production_total" in df.columns:

        # use previous production value as feature
        df["production_lag1"] = df["production_total"].shift(1)

        # compute production trend using last 4 periods
        df["production_roll4"] = df["production_total"].rolling(4).mean()

    # create interaction features only if both yield and production exist
    if "quarterly_yield_mt_per_ha" in df.columns and "production_total" in df.columns:

        # combine yield and production to capture supply effect
        df["yield_x_production"] = (
            df["quarterly_yield_mt_per_ha"] * df["production_total"]
        )

    # combine yield and price to capture economic relationship
    if "fancy_palay_price" in df.columns:

        df["yield_x_price"] = (
            df["quarterly_yield_mt_per_ha"] * df["fancy_palay_price"]
        )

    # remove unnecessary columns if they exist
    df = df.drop(columns=["province", "month"], errors="ignore")

    # remove rows with missing values caused by lag and rolling features
    df = df.dropna().reset_index(drop=True)

    # columns not used for model training
    drop_cols = [
        "date",
        "quarterly_yield_mt_per_ha",
        "fancy_palay_price",
        "other_variety_price"
    ]

    # final dataset containing only features for ML model
    df_features = df.drop(columns=[c for c in drop_cols if c in df.columns])

    return df, df_features