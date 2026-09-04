import numpy as np

def feature_engineering_fancy(provincial_df):
    # =========================================================
    # COPY DATA
    # =========================================================

    df = provincial_df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # =========================================================
    # TIME FEATURES
    # =========================================================

    if "date" in df.columns:
        # Month number
        df["month_num"] = df["date"].dt.month

        # Time order
        df["year_index"] = range(len(df))

        # Seasonal features
        df["month_sin"] = np.sin(
            2 * np.pi * df["month_num"] / 12
        )

        df["month_cos"] = np.cos(
            2 * np.pi * df["month_num"] / 12
        )

    # Quarter
    if "quarter" in df.columns:
        df["quarter"] = df["quarter"]

    # =========================================================
    # PRICE FEATURES
    # =========================================================

    if "fancy_palay_price" in df.columns:

        # -----------------------------------------------------
        # PRICE LAGS
        # -----------------------------------------------------

        for lag in [1, 2, 3, 4, 5, 6]:
            df[f"fancy_palay_price_lag{lag}"] = (
                df["fancy_palay_price"].shift(lag)
            )

        # 12-month lag
        df["fancy_palay_price_lag12"] = (
            df["fancy_palay_price"].shift(12)
        )

        # -----------------------------------------------------
        # ROLLING FEATURES
        # IMPORTANT:
        # shift(1) prevents current-price data leakage
        # -----------------------------------------------------

        df["fancy_palay_price_roll3"] = (
            df["fancy_palay_price"]
            .shift(1)
            .rolling(3)
            .mean()
        )

        df["fancy_palay_price_roll6"] = (
            df["fancy_palay_price"]
            .shift(1)
            .rolling(6)
            .mean()
        )

        df["fancy_palay_price_roll12"] = (
            df["fancy_palay_price"]
            .shift(1)
            .rolling(12)
            .mean()
        )

        # -----------------------------------------------------
        # PRICE VARIABILITY
        # -----------------------------------------------------

        df["fancy_palay_price_std3"] = (
            df["fancy_palay_price"]
            .shift(1)
            .rolling(3)
            .std()
        )

        # -----------------------------------------------------
        # PRICE CHANGE
        # -----------------------------------------------------

        df["fancy_palay_price_change"] = (
                df["fancy_palay_price"].shift(1)
                - df["fancy_palay_price"].shift(2)
        )

    # =========================================================
    # YIELD FEATURES
    # =========================================================

    if (
        "production_total" in df.columns
        and "harvested_total" in df.columns
    ):
        # Yield per hectare
        df["yield_per_ha"] = (
            df["production_total"]
            / df["harvested_total"]
        )

        # Previous production
        df["production_lag1"] = (
            df["production_total"].shift(1)
        )

    # =========================================================
    # PREVIOUS YIELD FEATURES
    # =========================================================

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

    # =========================================================
    # PRICE × YIELD
    # =========================================================

    if (
        "fancy_palay_price_lag1" in df.columns
        and "yield_per_ha" in df.columns
    ):
        df["price_x_yield"] = (
            df["fancy_palay_price_lag1"]
            * df["yield_per_ha"]
        )

    # =========================================================
    # REMOVE MISSING VALUES
    # =========================================================

    df = (
        df
        .dropna()
        .reset_index(drop=True)
    )

    # =========================================================
    # CREATE ML FEATURES DATAFRAME
    # =========================================================

    df_features = df.drop(columns=[
        "date",
        "fancy_palay_price",
        "other_variety_price"
    ], errors="ignore")

    return df, df_features