from sklearn.model_selection import TimeSeriesSplit  # For splitting time-series data into train/validation
from sklearn.ensemble import RandomForestRegressor   # Random Forest model
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error  # Model evaluation metrics
from sklearn.base import clone
from statsmodels.tsa.statespace.sarimax import SARIMAX  # SARIMA time-series model
import numpy as np  # For numerical operations
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

# Define which columns to use as input features for the model
def train_variety_price(df, rmse_threshold=2.0, max_attempts=3):
    print("\nStart of Train and Testing (REGULAR)")

    # =========================================================
    # FEATURES
    # =========================================================

    features = [
        "month_num",
        "month_sin",
        "month_cos",
        "quarter",
        "other_variety_price_lag1",
        "other_variety_price_lag2",
        "other_variety_price_lag3",
        "other_variety_price_lag4",
        "other_variety_price_lag5",
        "other_variety_price_lag6",
        "other_variety_price_lag12",
        "other_variety_price_roll3",
        "other_variety_price_roll6",
        "other_variety_price_roll12",
        "other_variety_price_std3",
        "other_variety_price_change",
        "yield_per_ha"
    ]

    # =========================================================
    # TRAIN / TEST SPLIT
    # =========================================================

    split_index = int(len(df) * 0.8)

    train_df = df.iloc[:split_index].copy()
    test_df = df.iloc[split_index:].copy()

    X_train = train_df[features]
    y_train = train_df["other_variety_price"]

    X_test = test_df[features]
    y_test = test_df["other_variety_price"]

    print(f"\nTotal samples: {len(df)}")
    print(f"Training samples: {len(train_df)}")
    print(f"Testing samples: {len(test_df)}")

    # =========================================================
    # TIME SERIES CROSS VALIDATION
    # =========================================================

    tscv = TimeSeriesSplit(n_splits=5)

    # =========================================================
    # RANDOM FOREST TRAINING
    # =========================================================

    print("\n[RANDOM FOREST] Training with TimeSeriesSplit...")

    attempt = 1

    best_rmse_rf = float("inf")
    regressor_rf = None

    while attempt <= max_attempts:

        print(f"\n[RF] Attempt {attempt}")

        cv_scores = []

        for fold, (train_idx, val_idx) in enumerate(
                tscv.split(X_train),
                start=1
        ):
            X_tr = X_train.iloc[train_idx]
            X_val = X_train.iloc[val_idx]

            y_tr = y_train.iloc[train_idx]
            y_val = y_train.iloc[val_idx]

            rf_model = RandomForestRegressor(
                n_estimators=200 + (attempt * 50),
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42
            )

            rf_model.fit(X_tr, y_tr)

            y_pred_val = rf_model.predict(X_val)

            fold_rmse = np.sqrt(
                mean_squared_error(
                    y_val,
                    y_pred_val
                )
            )

            cv_scores.append(fold_rmse)

            print(
                f"Fold {fold} RMSE: "
                f"{fold_rmse:.3f}"
            )

        # =====================================================
        # AVERAGE RF VALIDATION RMSE
        # =====================================================

        avg_rmse = np.mean(cv_scores)

        print(
            f"RF CV Average RMSE: "
            f"{avg_rmse:.3f}"
        )

        # =====================================================
        # SAVE BEST RF MODEL
        # =====================================================

        if avg_rmse < best_rmse_rf:
            best_rmse_rf = avg_rmse

            regressor_rf = RandomForestRegressor(
                n_estimators=200 + (attempt * 50),
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42,
                n_jobs=-1
            )

            regressor_rf.fit(
                X_train,
                y_train
            )

        # =====================================================
        # STOP IF ACCEPTABLE
        # =====================================================

        if avg_rmse <= rmse_threshold:
            print("RF acceptable.")
            break

        attempt += 1

    # =========================================================
    # RANDOM FOREST TEST EVALUATION
    # =========================================================

    rf_pred = regressor_rf.predict(X_test)

    rf_mae = mean_absolute_error(
        y_test,
        rf_pred
    )

    rf_rmse = np.sqrt(
        mean_squared_error(
            y_test,
            rf_pred
        )
    )

    rf_r2 = r2_score(
        y_test,
        rf_pred
    )

    # Bias estimated from TRAINING-ONLY TimeSeriesSplit folds (no test leakage).
    rf_bias = estimate_bias_cv(
        lambda: clone(regressor_rf), X_train, y_train, n_splits=5
    )

    print("\nRandom Forest Evaluation:")
    print(f"MAE: {rf_mae:.3f}")
    print(f"RMSE: {rf_rmse:.3f}")
    print(f"R²: {rf_r2:.3f}")
    print(f"Bias: {rf_bias:.3f}")

    # =========================================================
    # SARIMA WITH VALIDATION
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
        # SARIMA CROSS VALIDATION
        # -----------------------------------------------------

        for fold, (train_idx, val_idx) in enumerate(
                tscv.split(y_train),
                start=1
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

            sarima_scores.append(
                fold_rmse
            )

            print(
                f"SARIMA Fold {fold} RMSE: "
                f"{fold_rmse:.3f}"
            )

        # -----------------------------------------------------
        # AVERAGE SARIMA RMSE
        # -----------------------------------------------------

        avg_sarima_rmse = np.mean(
            sarima_scores
        )

        print(
            f"SARIMA Avg RMSE (Validation): "
            f"{avg_sarima_rmse:.3f}"
        )

        # -----------------------------------------------------
        # FINAL SARIMA MODEL
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

        sarima_pred = sarima_fit.forecast(
            steps=len(y_test)
        )

        # -----------------------------------------------------
        # SARIMA EVALUATION
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

        print("\nSARIMA Model Evaluation:")
        print(f"MAE: {sarima_mae:.3f}")
        print(f"RMSE: {sarima_rmse:.3f}")
        print(f"R²: {sarima_r2:.3f}")
        print(f"Bias: {sarima_bias:.3f}")

    except Exception as e:

        print("SARIMA failed:", e)

        avg_sarima_rmse = float("inf")

    # =========================================================
    # MODEL COMPARISON
    # =========================================================

    print("\n----- MODEL COMPARISON (REGULAR) -----")

    print(
        f"Random Forest Validation RMSE: "
        f"{best_rmse_rf:.3f}"
    )

    if np.isfinite(avg_sarima_rmse):

        print(
            f"SARIMA Validation RMSE: "
            f"{avg_sarima_rmse:.3f}"
        )

    else:

        print(
            "SARIMA Validation RMSE: Failed"
        )

    # =========================================================
    # SELECT BEST MODEL
    # =========================================================

    if avg_sarima_rmse < best_rmse_rf:

        print("\nSelected Model: SARIMA")

        regressor_regular = sarima_fit
        model_name_regular = "SARIMA"

        y_pred_regular = sarima_pred
        mae_regular = sarima_mae
        rmse_regular = sarima_rmse
        r2_regular = sarima_r2
        bias_regular = sarima_bias

    else:

        print(
            "\nSelected Model: "
            "Random Forest Regression"
        )

        regressor_regular = regressor_rf
        model_name_regular = "Random Forest Regression"

        y_pred_regular = rf_pred
        mae_regular = rf_mae
        rmse_regular = rf_rmse
        r2_regular = rf_r2
        bias_regular = rf_bias

    # =========================================================
    # FINAL METRICS
    # =========================================================

    print("\nFinal Model Evaluation (REGULAR):")

    print(
        f"Model: {model_name_regular}"
    )

    print(
        f"MAE: {mae_regular:.3f}"
    )

    print(
        f"RMSE: {rmse_regular:.3f}"
    )

    print(
        f"R²: {r2_regular:.3f}"
    )

    print(
        f"Bias (train-only CV): {bias_regular:.3f}"
    )

    # =========================================================
    # HONEST EVALUATION PACKAGE (for the defense)
    # =========================================================
    mape_regular = compute_metrics(y_test, y_pred_regular)["mape"]

    # Baselines evaluated on the SAME held-out window as the model.
    baselines_regular = baseline_metrics(df["other_variety_price"], split_index, season=12)

    # Walk-forward (rolling-origin) evaluation of the SELECTED model family,
    # benchmarked against Naive and Seasonal Naive on identical windows.
    if model_name_regular == "SARIMA":
        walk_forward_regular = walk_forward_eval_univariate(
            lambda y_tr: SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12),
                enforce_stationarity=False,
                enforce_invertibility=False
            ).fit(disp=False),
            df["other_variety_price"],
            n_origins=4,
            horizon=6,
            season=12,
        )
    else:
        walk_forward_regular = walk_forward_eval(
            lambda: clone(regressor_rf),
            df[features],
            df["other_variety_price"],
            n_origins=4,
            horizon=6,
            season=12,
        )

    # =========================================================
    # RETURN
    # =========================================================

    return {
        "model": regressor_regular,
        "model_name": model_name_regular,
        "X_test": X_test,
        "y_test": y_test,
        "y_pred": y_pred_regular,
        "bias": bias_regular,
        "mae": mae_regular,
        "rmse": rmse_regular,
        "r2": r2_regular,
        "mape": mape_regular,
        "baselines": baselines_regular,
        "walk_forward": walk_forward_regular,
    }