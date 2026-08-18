from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.base import clone
from statsmodels.tsa.statespace.sarimax import SARIMAX
import numpy as np
import warnings

from ml_shared.evaluation import (
    compute_metrics,
    baseline_metrics,
    estimate_bias_cv,
    estimate_bias_cv_univariate,
    walk_forward_eval,
    walk_forward_eval_univariate,
)

warnings.filterwarnings("ignore") # Hide warnings for cleaner output


def train_yield(df, rmse_threshold=2.0, max_attempts=3):

    print("\nStart of Train and Testing (YIELD)")

    # List of features to use in the models
    features = [
        "month_num",
        "month_sin",
        "month_cos",
        "quarter",
        "yield_lag1",
        "yield_lag2",
        "yield_lag3",
        "yield_lag4",
        "yield_roll2",
        "yield_roll4",
        "yield_std3",
        "yield_qoq",
        "yield_yoy"
    ]

    # Split the data into train (80%) and test (20%)
    split_index = int(len(df) * 0.8)
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    # Training inputs and target
    X_train = train_df[features]
    y_train = train_df["quarterly_yield_mt_per_ha"]

    # Testing inputs and target
    X_test = test_df[features]
    y_test = test_df["quarterly_yield_mt_per_ha"]

    # Time series cross-validation
    tscv = TimeSeriesSplit(n_splits=5)

    attempt = 1 # Start of tuning attempts
    best_rmse_rf = float("inf") # Initialize best RMSE very high
    best_model_rf = None # No best model at the start

    while attempt <= max_attempts: # Loop to tune Random Forest
        print(f"\n[RF] Attempt {attempt}")
        scores = [] # Store RMSE for each fold

        for train_index, val_index in tscv.split(X_train):
            X_tr, X_val = X_train.iloc[train_index], X_train.iloc[val_index]
            y_tr, y_val = y_train.iloc[train_index], y_train.iloc[val_index]

            # Initialize the Random Forest with parameters depending on attempt
            model = RandomForestRegressor(
                n_estimators=200 + (attempt * 50),
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42
            )

            # Train model on the fold
            model.fit(X_tr, y_tr)
            # Predict on validation fold
            val_pred = model.predict(X_val)
            # Calculate RMSE
            rmse = np.sqrt(mean_squared_error(y_val, val_pred))
            # Save fold RMSE
            scores.append(rmse)

        # Average RMSE across folds
        avg_rmse = np.mean(scores)
        print(f"RF Average RMSE: {avg_rmse:.3f}")

        # Update best model if RMSE is lower
        if avg_rmse < best_rmse_rf:
            best_rmse_rf = avg_rmse
            best_model_rf = model

        # Stop if RMSE meets threshold
        if avg_rmse <= rmse_threshold:
            print("RF acceptable.")
            break
        else:
            print("RF tuning...")
            attempt += 1 #Increase attempt counter

    # Final training on all train data
    best_model_rf.fit(X_train, y_train)
    # Predict on test set
    rf_pred = best_model_rf.predict(X_test)

    # Evaluate Random Forest predictions
    rf_mae_yield = mean_absolute_error(y_test, rf_pred)
    rf_rmse_yield = np.sqrt(mean_squared_error(y_test, rf_pred))
    rf_r2_yield = r2_score(y_test, rf_pred)
    # Bias estimated from TRAINING-ONLY TimeSeriesSplit folds (no test leakage).
    rf_bias_yield = estimate_bias_cv(
        lambda: clone(best_model_rf), X_train, y_train, n_splits=5
    )

    print("\nRandom Forest Evaluation:")
    print(f"MAE: {rf_mae_yield:.3f}")
    print(f"RMSE: {rf_rmse_yield:.3f}")
    print(f"R²: {rf_r2_yield:.3f}")
    print(f"Bias: {rf_bias_yield:.3f}")

    # SARIMA model with validation
    print("\n[SARIMA] Training with validation...")

    try:
        sarima_scores = []

        for train_index, val_index in tscv.split(y_train):
            y_tr, y_val = y_train.iloc[train_index], y_train.iloc[val_index]

            # Initialize SARIMA model
            model = SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12)
            )

            fit = model.fit(disp=False)  # Fit model
            pred = fit.forecast(steps=len(y_val))  # Forecast validation

            rmse = np.sqrt(mean_squared_error(y_val, pred)) # Compute RMSE
            sarima_scores.append(rmse)

        avg_sarima_rmse = np.mean(sarima_scores) # Average RMSE
        print(f"SARIMA Avg RMSE (Validation): {avg_sarima_rmse:.3f}")

        # Train final SARIMA on full train set
        sarima_model = SARIMAX(
            y_train,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12)
        )

        sarima_fit = sarima_model.fit(disp=False)
        sarima_pred = sarima_fit.forecast(steps=len(y_test))

        # Evaluate SARIMA predictions
        sarima_mae_yield = mean_absolute_error(y_test, sarima_pred)
        sarima_rmse_yield = np.sqrt(mean_squared_error(y_test, sarima_pred))
        sarima_r2_yield = r2_score(y_test, sarima_pred)
        # Bias estimated from TRAINING-ONLY folds (no test leakage).
        sarima_bias_yield = estimate_bias_cv_univariate(
            lambda y_tr: SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12)
            ).fit(disp=False),
            y_train,
            n_splits=3,
        )

        print("\nSARIMA Model Evaluation:")
        print(f"MAE: {sarima_mae_yield:.3f}")
        print(f"RMSE: {sarima_rmse_yield:.3f}")
        print(f"R²: {sarima_r2_yield:.3f}")
        print(f"Bias: {sarima_bias_yield:.3f}")

    except Exception as e:
        print("SARIMA failed:", e)
        sarima_rmse_yield = float("inf")
        avg_sarima_rmse = float("inf")

    # Compare RF and SARIMA, pick model with lower validation RMSE
    if avg_sarima_rmse < best_rmse_rf:
        print("\nSelected Model: SARIMA")

        best_model_yield = sarima_fit
        model_name_yield = "SARIMA"

        y_pred_yield = sarima_pred
        mae_yield = sarima_mae_yield
        rmse_yield = sarima_rmse_yield
        r2_yield = sarima_r2_yield
        bias_yield = sarima_bias_yield

    else:
        print("\nSelected Model: Random Forest")

        best_model_yield = best_model_rf
        model_name_yield = "Random Forest Regression"

        y_pred_yield = rf_pred
        mae_yield = rf_mae_yield
        rmse_yield = rf_rmse_yield
        r2_yield = rf_r2_yield
        bias_yield = rf_bias_yield

    # Print final metrics
    print("\nFinal Model Evaluation (YIELD):")
    print(f"Model: {model_name_yield}")
    print(f"MAE: {mae_yield:.3f}")
    print(f"RMSE: {rmse_yield:.3f}")
    print(f"R²: {r2_yield:.3f}")
    print(f"Bias (train-only CV): {bias_yield:.3f}")

    # =========================================================
    # HONEST EVALUATION PACKAGE (for the defense)
    # =========================================================
    mape_yield = compute_metrics(y_test, y_pred_yield)["mape"]

    # Baselines evaluated on the SAME held-out window as the model.
    baselines_yield = baseline_metrics(df["quarterly_yield_mt_per_ha"], split_index, season=4)

    # Walk-forward (rolling-origin) evaluation of the SELECTED model family,
    # benchmarked against Naive and Seasonal Naive on identical windows.
    if model_name_yield == "SARIMA":
        walk_forward_yield = walk_forward_eval_univariate(
            lambda y_tr: SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12)
            ).fit(disp=False),
            df["quarterly_yield_mt_per_ha"],
            n_origins=3,
            horizon=4,
            season=4,
        )
    else:
        walk_forward_yield = walk_forward_eval(
            lambda: clone(best_model_rf),
            df[features],
            df["quarterly_yield_mt_per_ha"],
            n_origins=3,
            horizon=4,
            season=4,
        )

    # Return final model and metrics
    return {
        "model": best_model_yield,
        "model_name": model_name_yield,
        "X_test": X_test,
        "y_test": y_test,
        "y_pred": y_pred_yield,
        "bias": bias_yield,
        "mae": mae_yield,
        "rmse": rmse_yield,
        "r2": r2_yield,
        "mape": mape_yield,
        "baselines": baselines_yield,
        "walk_forward": walk_forward_yield,
    }