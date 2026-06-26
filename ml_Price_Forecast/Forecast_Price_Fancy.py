import calendar
import numpy as np

def forecast_next_3_months(model, df_features, bias, model_name):
    """
        Forecast the next 3 months of Fancy Palay Price using a trained model.

        Parameters:
        - model: trained selected Model
        - df_features: dataframe with ML-ready features
        - bias: historical bias to adjust predictions
        """
    # -----------------------------
    # SARIMA CASE
    # -----------------------------
    if model_name == "SARIMA":

        forecasts = model.forecast(steps=3)
        forecasts = [f + bias for f in forecasts]

        month = (df_features["month_num"].iloc[-1] % 12) + 1
        month_names = []

        print("\nNext 3 Months Forecast (SARIMA):")
        for i, price in enumerate(forecasts):
            month_names.append(calendar.month_name[month])
            print(f"{calendar.month_name[month]}: ₱{forecasts[i]:.2f}")
            month = (month % 12) + 1

        return forecasts

    # -----------------------------
    # RANDOM FOREST CASE
    # -----------------------------
    if hasattr(model, "feature_names_in_"):
        trained_features = model.feature_names_in_
    else:
        trained_features = df_features.columns

    current_features = df_features[trained_features].iloc[-1:].copy()

    forecasts = []
    month = (current_features["month_num"].values[0] % 12) + 1
    month_names = []

    for _ in range(3):
        # Predict and apply bias
        pred = model.predict(current_features)[0] + bias
        forecasts.append(pred)
        month_names.append(calendar.month_name[month])

        # Update lag features
        if "fancy_palay_price_lag3" in current_features.columns:
            current_features["fancy_palay_price_lag3"] = current_features["fancy_palay_price_lag2"]
        if "fancy_palay_price_lag2" in current_features.columns:
            current_features["fancy_palay_price_lag2"] = current_features["fancy_palay_price_lag1"]
        if "fancy_palay_price_lag1" in current_features.columns:
            current_features["fancy_palay_price_lag1"] = pred

        # update seasonality
        month = (month % 12) + 1
        current_features["month_num"] = month
        current_features["month_sin"] = np.sin(2 * np.pi * month / 12)
        current_features["month_cos"] = np.cos(2 * np.pi * month / 12)

    # Display forecast
    print("\nNext 3 Months Forecast (Random Forest):")
    for m, price in zip(month_names, forecasts):
        print(f"{m}: ₱{price:.2f}")

    return forecasts