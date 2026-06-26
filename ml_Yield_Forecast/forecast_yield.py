def forecast_4quarters_yield(model, df_features, bias):
    """
    Forecast the next 4 quarters of yield in the province using a trained model

    Parameters:
    - model: trained selected model
    - df_features: dataframe with ML-ready features (quarterly)
    - bias: historical bias to adjust predictions
    """
    trained_features_y = model.feature_names_in_
    current_features_y = df_features[trained_features_y].iloc[-1:].copy()

    forecasts_y = []
    quarter = current_features_y["quarter"].values[0]
    quarter_names = [f"Q{q}" for q in range(1,5)]

    for _ in range(4):
        # predict and apply bias
        pred_y = model.predict(current_features_y)[0] + bias
        forecasts_y.append(pred_y)

        # update lags
        for i in range(4,1,-1):
            if f"yield_lag{i}" in current_features_y.columns:
                current_features_y[f"yield_lag{i}"] = current_features_y[f"yield_lag{i-1}"]
        if "yield_lag1" in current_features_y.columns:
            current_features_y["yield_lag1"] = pred_y

        # update quarter
        quarter = (quarter % 4) + 1
        current_features_y["quarter"] = quarter

    # print forecast
    print("\nNext 4 Quarters Yield Forecast (Bias Corrected):")
    for i, yield_y in enumerate(forecasts_y, 1):
        print(f"Q{i}: {yield_y:.2f}")

    return forecasts_y