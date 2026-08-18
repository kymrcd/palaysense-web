import calendar
import numpy as np
import pandas as pd


def forecast_next_3_months(model, df, df_features, bias, model_name):
    """
    Forecast the next 6 months of Fancy Palay Price.

    Function name is kept as forecast_next_3_months
    for compatibility with existing imports/calls.
    """

    # =========================================================
    # GET LAST HISTORICAL DATE
    # =========================================================

    if "date" not in df.columns:
        raise KeyError(
            "The 'date' column is required in df for forecasting."
        )

    last_date = pd.to_datetime(df["date"].iloc[-1])

    last_month = int(last_date.month)
    last_year = int(last_date.year)

    # =========================================================
    # SARIMA CASE
    # =========================================================

    if model_name == "SARIMA":

        forecasts = model.forecast(steps=6)

        forecasts = [
            float(f) + bias
            for f in forecasts
        ]

    # =========================================================
    # RANDOM FOREST CASE
    # =========================================================

    else:

        # -----------------------------------------------------
        # Get exact features used during training
        # -----------------------------------------------------

        if hasattr(model, "feature_names_in_"):
            trained_features = list(model.feature_names_in_)
        else:
            trained_features = list(df_features.columns)

        # Check if all required features exist
        missing_features = [
            feature
            for feature in trained_features
            if feature not in df_features.columns
        ]

        if missing_features:
            raise KeyError(
                f"Missing features for forecasting: {missing_features}"
            )

        # Latest feature row
        current_features = (
            df_features[trained_features]
            .iloc[-1:]
            .copy()
        )

        # -----------------------------------------------------
        # Get historical price values from ORIGINAL df
        # -----------------------------------------------------

        if "fancy_palay_price" not in df.columns:
            raise KeyError(
                "The 'fancy_palay_price' column is required in df."
            )

        price_history = list(
            df["fancy_palay_price"].iloc[-12:]
        )

        price_history = [
            float(x)
            for x in price_history
            if not pd.isna(x)
        ]

        if len(price_history) < 12:
            raise ValueError(
                "At least 12 historical price values are required "
                "for the 12-month lag and rolling features."
            )

        month = last_month
        year = last_year

        forecasts = []

        # =====================================================
        # 6-MONTH FORECAST
        # =====================================================

        for _ in range(6):

            # -------------------------------------------------
            # PREDICT
            # -------------------------------------------------

            pred = float(
                model.predict(current_features)[0]
            )

            # Bias correction
            pred_corrected = pred + bias

            forecasts.append(pred_corrected)

            # Add forecasted value to price history
            price_history.append(pred_corrected)

            # Keep latest 12 values
            price_history = price_history[-12:]

            # -------------------------------------------------
            # UPDATE LAG FEATURES
            # -------------------------------------------------

            if "fancy_palay_price_lag1" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag1"
                ] = price_history[-1]

            if "fancy_palay_price_lag2" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag2"
                ] = price_history[-2]

            if "fancy_palay_price_lag3" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag3"
                ] = price_history[-3]

            if "fancy_palay_price_lag4" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag4"
                ] = price_history[-4]

            if "fancy_palay_price_lag5" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag5"
                ] = price_history[-5]

            if "fancy_palay_price_lag6" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag6"
                ] = price_history[-6]

            if "fancy_palay_price_lag12" in current_features.columns:
                current_features[
                    "fancy_palay_price_lag12"
                ] = price_history[-12]

            # -------------------------------------------------
            # UPDATE ROLLING FEATURES
            # -------------------------------------------------

            if "fancy_palay_price_roll3" in current_features.columns:
                current_features[
                    "fancy_palay_price_roll3"
                ] = np.mean(price_history[-3:])

            if "fancy_palay_price_roll6" in current_features.columns:
                current_features[
                    "fancy_palay_price_roll6"
                ] = np.mean(price_history[-6:])

            if "fancy_palay_price_roll12" in current_features.columns:
                current_features[
                    "fancy_palay_price_roll12"
                ] = np.mean(price_history[-12:])

            # -------------------------------------------------
            # UPDATE STANDARD DEVIATION
            # -------------------------------------------------

            if "fancy_palay_price_std3" in current_features.columns:
                current_features[
                    "fancy_palay_price_std3"
                ] = np.std(
                    price_history[-3:],
                    ddof=1
                )

            # -------------------------------------------------
            # UPDATE PRICE CHANGE
            # -------------------------------------------------

            if "fancy_palay_price_change" in current_features.columns:
                current_features[
                    "fancy_palay_price_change"
                ] = (
                    price_history[-1]
                    - price_history[-2]
                )

            # -------------------------------------------------
            # UPDATE MONTH
            # -------------------------------------------------

            month = (month % 12) + 1

            if month == 1:
                year += 1

            if "month_num" in current_features.columns:
                current_features["month_num"] = month

            if "month_sin" in current_features.columns:
                current_features["month_sin"] = np.sin(
                    2 * np.pi * month / 12
                )

            if "month_cos" in current_features.columns:
                current_features["month_cos"] = np.cos(
                    2 * np.pi * month / 12
                )

            # -------------------------------------------------
            # UPDATE QUARTER
            # -------------------------------------------------

            if "quarter" in current_features.columns:
                current_features["quarter"] = (
                    (month - 1) // 3
                ) + 1

    # =========================================================
    # CREATE FORECAST MONTHS
    # =========================================================

    forecast_months = []

    month = last_month
    year = last_year

    for _ in range(6):

        month = (month % 12) + 1

        if month == 1:
            year += 1

        forecast_months.append(
            f"{calendar.month_name[month]} {year}"
        )

    # =========================================================
    # FINAL PRINTING
    # =========================================================

    print("\n")
    print("=" * 65)
    print("       NEXT 6 MONTHS FANCY PALAY PRICE FORECAST")
    print("=" * 65)

    print(f"Model: {model_name}")
    print(f"Bias Correction: {bias:.3f}")

    print("\nForecast Period:")
    print(
        f"{forecast_months[0]} → {forecast_months[-1]}"
    )

    print("-" * 65)
    print(
        f"{'Month':<25}"
        f"{'Forecasted Price':>20}"
    )
    print("-" * 65)

    for month_name, price in zip(
        forecast_months,
        forecasts
    ):
        print(
            f"{month_name:<25}"
            f"₱{price:>18.2f}"
        )

    print("-" * 65)
    print("=" * 65)

    return forecasts