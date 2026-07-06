from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import numpy as np
import warnings

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
                and np.issubdtype(df_muni[col].dtype, np.number)
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
            tscv = TimeSeriesSplit(n_splits=5)

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
                        random_state=42
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
            bias = y_test.mean() - y_pred.mean()

            print("\nEvaluation")
            print(f"MAE  : {mae:.3f}")
            print(f"RMSE : {rmse:.3f}")
            print(f"R²   : {r2:.3f}")
            print(f"Bias : {bias:.3f}")

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
                "Bias": bias
            }

    print("\n=== TRAINING COMPLETED ===")

    return results