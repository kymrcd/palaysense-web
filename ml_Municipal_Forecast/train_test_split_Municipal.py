from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.base import clone
import numpy as np
import warnings
import pandas as pd
import os
import joblib

from ml_shared.evaluation import (
    compute_metrics,
    baseline_metrics,
    estimate_bias_cv,
    walk_forward_eval,
)

warnings.filterwarnings("ignore")


def train_price_Municipal(df_features_municipal, rmse_threshold=2.0, max_attempts=3):
    print("\nStart of Train and Testing (Municipality)")

    target_columns = [
        "hybridpremium_dry",
        "hybridpremium_wet",
        "hybridordinary_dry",
        "hybridordinary_wet",
        "inbredpremium_dry",
        "inbredpremium_wet",
        "inbredordinary_dry",
        "inbredordinary_wet"
    ]

    results = {}
    all_forecasts_list = []

    # =============================
    # LOOP PER MUNICIPALITY
    # =============================
    municipalities = df_features_municipal["municipality"].unique()

    for muni in municipalities:

        print(f"\n==============================")
        print(f"Municipality: {muni}")
        print(f"==============================")

        # FILTER DATA PER MUNICIPALITY
        df_muni = df_features_municipal[
            df_features_municipal["municipality"] == muni
            ].copy()

        results[muni] = {}

        # =============================
        # LOOP PER TARGET COLUMN
        # =============================
        for target in target_columns:

            print(f"\nTraining: {target}")

            # FEATURES (exclude target columns + non-numeric)
            features = [
                col for col in df_muni.columns
                if col not in target_columns
                   and col != "municipality"
                   and pd.api.types.is_numeric_dtype(df_muni[col])
            ]

            X = df_muni[features]
            y = df_muni[target]

            # -----------------------------
            # TRAIN / TEST SPLIT
            # -----------------------------
            split_index = int(len(df_muni) * 0.8)

            X_train = X.iloc[:split_index]
            X_test = X.iloc[split_index:]

            y_train = y.iloc[:split_index]
            y_test = y.iloc[split_index:]

            # -----------------------------
            # TIME SERIES CROSS VALIDATION
            # -----------------------------
            tscv = TimeSeriesSplit(n_splits=3)

            attempt = 1
            best_rmse = float("inf")
            best_model = None

            while attempt <= max_attempts:

                print(f"Attempt {attempt}")

                scores = []

                for train_idx, val_idx in tscv.split(X_train):
                    X_tr = X_train.iloc[train_idx]
                    X_val = X_train.iloc[val_idx]

                    y_tr = y_train.iloc[train_idx]
                    y_val = y_train.iloc[val_idx]

                    model = RandomForestRegressor(
                        n_estimators=200 + attempt * 50,
                        max_depth=10 + attempt,
                        min_samples_split=4,
                        random_state=42,
                        n_jobs=-1
                    )

                    model.fit(X_tr, y_tr)

                    pred = model.predict(X_val)

                    rmse = np.sqrt(mean_squared_error(y_val, pred))
                    scores.append(rmse)

                avg_rmse = np.mean(scores)

                print(f"Average CV RMSE: {avg_rmse:.3f}")

                if avg_rmse < best_rmse:
                    best_rmse = avg_rmse
                    best_model = model

                if avg_rmse <= rmse_threshold:
                    print("Acceptable model found.")
                    break

                attempt += 1

            # -----------------------------
            # FINAL TRAINING
            # -----------------------------
            best_model.fit(X_train, y_train)
            y_pred = best_model.predict(X_test)

            mae = mean_absolute_error(y_test, y_pred)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            r2 = r2_score(y_test, y_pred)
            # Bias estimated from TRAINING-ONLY TimeSeriesSplit folds (no test leakage).
            bias = estimate_bias_cv(
                lambda: clone(best_model), X_train, y_train, n_splits=3
            )
            mape = compute_metrics(y_test, y_pred)["mape"]

            print("\nEvaluation")
            print(f"MAE  : {mae:.3f}")
            print(f"RMSE : {rmse:.3f}")
            print(f"R²   : {r2:.3f}")
            print(f"Bias (train-only CV): {bias:.3f}")
            print(f"MAPE : {mape:.2f}%")

            # Baselines evaluated on the SAME held-out window as the model.
            baselines_muni = baseline_metrics(df_muni[target], split_index, season=12)

            # Walk-forward (rolling-origin) evaluation of the selected model,
            # benchmarked against Naive and Seasonal Naive on identical windows.
            walk_forward_muni = walk_forward_eval(
                lambda: clone(best_model),
                df_muni[features],
                df_muni[target],
                n_origins=3,
                horizon=3,
                season=12,
            )

            # STORE RESULT
            results[muni][target] = {
                "model": best_model,
                "features": features,
                "X_test": X_test,
                "y_test": y_test,
                "y_pred": y_pred,
                "MAE": mae,
                "RMSE": rmse,
                "R2": r2,
                "MAPE": mape,
                "Bias": bias,
                "baselines": baselines_muni,
                "walk_forward": walk_forward_muni,
            }

            # =========================================================
            # EXTRACT THE LAST 3 MONTHS OF FORECASTS PER COMBINATION
            # =========================================================
            m1 = y_pred[-3] if len(y_pred) >= 3 else (y_pred[-1] if len(y_pred) > 0 else 0)
            m2 = y_pred[-2] if len(y_pred) >= 2 else (y_pred[-1] if len(y_pred) > 0 else 0)
            m3 = y_pred[-1] if len(y_pred) >= 1 else 0

            all_forecasts_list.append({
                "Municipality": muni.upper(),
                "Rice Type & Season": target,
                "Month 1": round(m1, 2),
                "Month 2": round(m2, 2),
                "Month 3": round(m3, 2)
            })

    print("\n=== TRAINING COMPLETED ===")

    # =========================================================
    # DISPLAY UNIFIED SUMMARY TABLE FOR THE 3-MONTH FORECAST
    # =========================================================
    print("\n" + "=" * 95)
    print("                FINAL SUMMARY: 3-MONTH PRICE FORECAST PER MUNICIPALITY & SEASON")
    print("=" * 95)

    # Convert the accumulated list into a single clean DataFrame
    df_summary = pd.DataFrame(all_forecasts_list)

    # Print the entire table to the terminal
    print(df_summary.to_string(index=False))
    print("=" * 95 + "\n")

    # =========================================================
    # Training results persisted by caller
    # =========================================================

    print("\nMunicipality models trained successfully!")

    return results, df_summary
