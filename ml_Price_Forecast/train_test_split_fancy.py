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

warnings.filterwarnings("ignore")

def train_price_fancy(df, rmse_threshold=2.0, max_attempts=3):
    # =========================================================
    # START
    # =========================================================
    print("\nStart of Train and Testing (FANCY)")

    # =========================================================
    # FEATURES
    # =========================================================
    features = [
        "month_num",
        "month_sin",
        "month_cos",
        "quarter",

        # Price lag features
        "fancy_palay_price_lag1",
        "fancy_palay_price_lag2",
        "fancy_palay_price_lag3",
        "fancy_palay_price_lag4",
        "fancy_palay_price_lag5",
        "fancy_palay_price_lag6",
        "fancy_palay_price_lag12",

        # Rolling price features
        "fancy_palay_price_roll3",
        "fancy_palay_price_roll6",
        "fancy_palay_price_roll12",

        # Price behavior
        "fancy_palay_price_std3",
        "fancy_palay_price_change",

        # Yield
        "yield_per_ha"
    ]

    # =========================================================
    # TRAIN / TEST SPLIT
    # =========================================================

    # Chronological 80/20 split
    split_index = int(len(df) * 0.80)

    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    # Training data
    X_train = train_df[features]
    y_train = train_df["fancy_palay_price"]

    # Testing data
    X_test = test_df[features]
    y_test = test_df["fancy_palay_price"]

    print(f"\nTotal samples: {len(df)}")
    print(f"Training samples: {len(train_df)}")
    print(f"Testing samples: {len(test_df)}")

    # =========================================================
    # TIME SERIES CROSS-VALIDATION
    # =========================================================

    tscv = TimeSeriesSplit(n_splits=5)

    # =========================================================
    # RANDOM FOREST TRAINING
    # =========================================================

    print("\n[RANDOM FOREST] Training with TimeSeriesSplit...")

    attempt = 1
    best_rmse_rf = float("inf")
    best_model_rf = None

    while attempt <= max_attempts:

        print(f"\n[RF] Attempt {attempt}")

        cv_scores = []

        # -----------------------------------------------------
        # TimeSeriesSplit validation
        # -----------------------------------------------------
        for fold, (train_idx, val_idx) in enumerate(
                tscv.split(X_train), start=1
        ):
            X_tr = X_train.iloc[train_idx]
            X_val = X_train.iloc[val_idx]

            y_tr = y_train.iloc[train_idx]
            y_val = y_train.iloc[val_idx]

            # Random Forest model
            rf_model = RandomForestRegressor(
                n_estimators=200 + (attempt * 50),
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42,
                n_jobs=-1
            )

            # Train
            rf_model.fit(X_tr, y_tr)

            # Validation prediction
            y_pred_val = rf_model.predict(X_val)

            # Validation RMSE
            fold_rmse = np.sqrt(
                mean_squared_error(y_val, y_pred_val)
            )

            cv_scores.append(fold_rmse)

            print(
                f"Fold {fold} RMSE: {fold_rmse:.3f}"
            )

        # -----------------------------------------------------
        # Average validation RMSE
        # -----------------------------------------------------
        avg_rmse = np.mean(cv_scores)

        print(
            f"RF CV Average RMSE: {avg_rmse:.3f}"
        )

        # -----------------------------------------------------
        # Save best configuration
        # -----------------------------------------------------
        if avg_rmse < best_rmse_rf:
            best_rmse_rf = avg_rmse

            # Create final RF using the best configuration
            best_model_rf = RandomForestRegressor(
                n_estimators=200 + (attempt * 50),
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42,
                n_jobs=-1
            )

            # Train on ALL training data
            best_model_rf.fit(X_train, y_train)

        # -----------------------------------------------------
        # Stop if acceptable
        # -----------------------------------------------------
        if avg_rmse <= rmse_threshold:
            print("RF acceptable.")
            break

        attempt += 1

    # =========================================================
    # RANDOM FOREST TEST EVALUATION
    # =========================================================

    rf_pred = best_model_rf.predict(X_test)

    rf_mae = mean_absolute_error(
        y_test,
        rf_pred
    )

    rf_rmse = np.sqrt(
        mean_squared_error(y_test, rf_pred)
    )

    rf_r2 = r2_score(
        y_test,
        rf_pred
    )

    # Bias estimated from TRAINING-ONLY TimeSeriesSplit folds (no test leakage).
    rf_bias = estimate_bias_cv(
        lambda: clone(best_model_rf), X_train, y_train, n_splits=5
    )

    print("\nRandom Forest Evaluation:")
    print(f"MAE: {rf_mae:.3f}")
    print(f"RMSE: {rf_rmse:.3f}")
    print(f"R²: {rf_r2:.3f}")
    print(f"Bias: {rf_bias:.3f}")

    # =========================================================
    # SARIMA TRAINING
    # =========================================================

    print("\n[SARIMA] Training with validation...")

    sarima_mae = None
    sarima_rmse = None
    sarima_r2 = None
    sarima_bias = None

    avg_sarima_rmse = float("inf")

    sarima_fit = None
    sarima_pred = None

    try:

        sarima_scores = []

        # -----------------------------------------------------
        # SARIMA TimeSeriesSplit validation
        # -----------------------------------------------------

        for fold, (train_idx, val_idx) in enumerate(
                tscv.split(y_train), start=1
        ):
            y_tr = y_train.iloc[train_idx]
            y_val = y_train.iloc[val_idx]

            sarima_model = SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12),
                enforce_stationarity=False,
                enforce_invertibility=False
            )

            sarima_fold_fit = sarima_model.fit(
                disp=False
            )

            sarima_val_pred = sarima_fold_fit.forecast(
                steps=len(y_val)
            )

            fold_rmse = np.sqrt(
                mean_squared_error(
                    y_val,
                    sarima_val_pred
                )
            )

            sarima_scores.append(fold_rmse)

            print(
                f"SARIMA Fold {fold} RMSE: "
                f"{fold_rmse:.3f}"
            )

        # -----------------------------------------------------
        # Average SARIMA validation RMSE
        # -----------------------------------------------------

        avg_sarima_rmse = np.mean(
            sarima_scores
        )

        print(
            f"SARIMA Avg RMSE (Validation): "
            f"{avg_sarima_rmse:.3f}"
        )

        # -----------------------------------------------------
        # Train final SARIMA on all training data
        # -----------------------------------------------------

        sarima_model = SARIMAX(
            y_train,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12),
            enforce_stationarity=False,
            enforce_invertibility=False
        )

        sarima_fit = sarima_model.fit(
            disp=False
        )

        # Forecast test period
        sarima_pred = sarima_fit.forecast(
            steps=len(y_test)
        )

        # -----------------------------------------------------
        # SARIMA TEST EVALUATION
        # -----------------------------------------------------

        sarima_mae = mean_absolute_error(
            y_test,
            sarima_pred
        )

        sarima_rmse = np.sqrt(
            mean_squared_error(
                y_test,
                sarima_pred
            )
        )

        sarima_r2 = r2_score(
            y_test,
            sarima_pred
        )

        # Bias estimated from TRAINING-ONLY folds (no test leakage).
        sarima_bias = estimate_bias_cv_univariate(
            lambda y_tr: SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12),
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(disp=False),
            y_train,
            n_splits=3,
        )

        print("\nSARIMA Evaluation:")
        print(f"MAE: {sarima_mae:.3f}")
        print(f"RMSE: {sarima_rmse:.3f}")
        print(f"R²: {sarima_r2:.3f}")
        print(f"Bias: {sarima_bias:.3f}")

    except Exception as e:

        print("\nSARIMA failed:", e)

        avg_sarima_rmse = float("inf")

    # =========================================================
    # MODEL COMPARISON
    # =========================================================

    print("\n--- MODEL COMPARISON (FANCY) ---")

    print(
        f"Random Forest "
        f"Validation RMSE: {best_rmse_rf:.3f}"
    )

    if np.isfinite(avg_sarima_rmse):
        print(
            f"SARIMA "
            f"Validation RMSE: {avg_sarima_rmse:.3f}"
        )
    else:
        print(
            "SARIMA Validation RMSE: Failed"
        )

    # =========================================================
    # SELECT MODEL USING VALIDATION RMSE
    # =========================================================

    if avg_sarima_rmse < best_rmse_rf:

        print("\nSelected Model: SARIMA")

        best_model = sarima_fit
        model_name = "SARIMA"

        y_pred = sarima_pred
        mae = sarima_mae
        rmse = sarima_rmse
        r2 = sarima_r2
        bias = sarima_bias

    else:

        print(
            "\nSelected Model: "
            "Random Forest Regression"
        )

        best_model = best_model_rf
        model_name = "Random Forest Regression"

        y_pred = rf_pred
        mae = rf_mae
        rmse = rf_rmse
        r2 = rf_r2
        bias = rf_bias

    # =========================================================
    # FINAL OUTPUT
    # =========================================================

    print("\nFinal Model Evaluation (FANCY):")

    print(f"Model: {model_name}")
    print(f"MAE: {mae:.3f}")
    print(f"RMSE: {rmse:.3f}")
    print(f"R²: {r2:.3f}")
    print(f"Bias (train-only CV): {bias:.3f}")

    # =========================================================
    # HONEST EVALUATION PACKAGE (for the defense)
    # =========================================================
    mape = compute_metrics(y_test, y_pred)["mape"]

    # Baselines evaluated on the SAME held-out window as the model.
    baselines = baseline_metrics(df["fancy_palay_price"], split_index, season=12)

    # Walk-forward (rolling-origin) evaluation of the SELECTED model family,
    # benchmarked against Naive and Seasonal Naive on identical windows.
    if model_name == "SARIMA":
        walk_forward = walk_forward_eval_univariate(
            lambda y_tr: SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12),
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(disp=False),
            df["fancy_palay_price"],
            n_origins=4,
            horizon=6,
            season=12,
        )
    else:
        walk_forward = walk_forward_eval(
            lambda: clone(best_model_rf),
            df[features],
            df["fancy_palay_price"],
            n_origins=4,
            horizon=6,
            season=12,
        )

    # =========================================================
    # RETURN
    # =========================================================

    return {
        "model": best_model,
        "model_name": model_name,
        "X_test": X_test,
        "y_test": y_test,
        "y_pred": y_pred,
        "bias": bias,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "mape": mape,
        "baselines": baselines,
        "walk_forward": walk_forward,
    }