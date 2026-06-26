from sklearn.model_selection import TimeSeriesSplit
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from statsmodels.tsa.statespace.sarimax import SARIMAX
import numpy as np
import warnings

warnings.filterwarnings("ignore")

def train_price_fancy(df, rmse_threshold=2.0, max_attempts=3):

    # start
    print("\nStart of Train and Testing (FANCY)")

    features = [
        "month_num",
        "month_sin",
        "month_cos",
        "quarter",
        "fancy_palay_price_lag1",
        "fancy_palay_price_lag2",
        "fancy_palay_price_lag3",
        "fancy_palay_price_roll3",
        "fancy_palay_price_roll6",
        "fancy_palay_price_std3",
        "fancy_palay_price_change",
        "yield_per_ha"
    ]

    # Split data into train (80%) and test (20%) based on row index
    split_index = int(len(df) * 0.8)
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    # Separate features and target for training
    X_train = train_df[features]
    y_train = train_df["fancy_palay_price"]

    # Prepare test data
    X_test = test_df[features]
    y_test = test_df["fancy_palay_price"]

    # TimeSeriesSplit for cross-validation to respect time order
    tscv = TimeSeriesSplit(n_splits=5)

    # RANDOM FOREST TRAINING
    attempt = 1
    best_rmse_rf = float("inf")
    best_model_rf = None # Placeholder for best Random Forest model

    rf_mae = rf_rmse = rf_r2 = rf_bias = None

    # Random Forest training loop with up to max_attempts for tuning
    while attempt <= max_attempts:
        print(f"\n[RF] Attempt {attempt}")
        scores = [] # Store RMSE for each CV fold

        for train_idx, val_idx in tscv.split(X_train):
            X_tr, X_val = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            # Initialize Random Forest with slightly higher complexity each attempt
            model = RandomForestRegressor(
                n_estimators=200 + attempt * 50,
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42
            )

            # Train model on training fold
            model.fit(X_tr, y_tr)
            # Predict on validation fold
            y_pred_val = model.predict(X_val)

            rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))  # Calculate RMSE
            scores.append(rmse) # Save RMSE

        avg_rmse = np.mean(scores) # Average RMSE over all folds
        print(f"RF CV Average RMSE: {avg_rmse:.3f}")

        # If current model is better than previous best, save it
        if avg_rmse < best_rmse_rf:
            best_rmse_rf = avg_rmse
            best_model_rf = model

        # Stop if RMSE is below threshold
        if avg_rmse <= rmse_threshold:
            print("RF acceptable.")
            break
        attempt += 1

    # Train final Random Forest on all training data
    best_model_rf.fit(X_train, y_train)
    rf_pred = best_model_rf.predict(X_test) # Predict on test set

    # Calculate evaluation metrics for Random Forest
    rf_mae = mean_absolute_error(y_test, rf_pred)
    rf_rmse = np.sqrt(mean_squared_error(y_test, rf_pred))
    rf_r2 = r2_score(y_test, rf_pred)
    rf_bias = y_test.mean() - rf_pred.mean() # Average bias

    print("\nRandom Forest Evaluation:")
    print(f"MAE: {rf_mae:.3f}")
    print(f"RMSE: {rf_rmse:.3f}")
    print(f"R²: {rf_r2:.3f}")
    print(f"Bias: {rf_bias:.3f}")

    # -----------------------------
    # SARIMA TRAINING
    # -----------------------------
    print("\n[SARIMA] Training with validation...")

    sarima_mae = sarima_rmse = sarima_r2 = sarima_bias = None
    avg_sarima_rmse = float("inf")
    sarima_fit = None
    sarima_pred = None

    try:
        sarima_scores = [] # Store RMSE for SARIMA CV

        # Chronological split for SARIMA validation
        for train_idx, val_idx in tscv.split(y_train):
            y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]

            # Initialize SARIMA model
            model = SARIMAX(
                y_tr,
                order=(1, 1, 1),
                seasonal_order=(1, 1, 1, 12)
            )

            fit = model.fit(disp=False) # Fit SARIMA
            pred = fit.forecast(steps=len(y_val)) # Forecast validation period

            rmse = np.sqrt(mean_squared_error(y_val, pred)) # RMSE for validation
            sarima_scores.append(rmse)

        avg_sarima_rmse = np.mean(sarima_scores) # Average RMSE
        print(f"SARIMA Avg RMSE (Validation): {avg_sarima_rmse:.3f}")

        # Train final SARIMA on all training data
        sarima_model = SARIMAX(
            y_train,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12)
        )

        sarima_fit = sarima_model.fit(disp=False)
        sarima_pred = sarima_fit.forecast(steps=len(y_test))

        sarima_mae = mean_absolute_error(y_test, sarima_pred)
        sarima_rmse = np.sqrt(mean_squared_error(y_test, sarima_pred))
        sarima_r2 = r2_score(y_test, sarima_pred)
        sarima_bias = y_test.mean() - sarima_pred.mean()

        print("\nSARIMA Evaluation:")
        print(f"MAE: {sarima_mae:.3f}")
        print(f"RMSE: {sarima_rmse:.3f}")
        print(f"R²: {sarima_r2:.3f}")
        print(f"Bias: {sarima_bias:.3f}")

    except Exception as e:
        print("SARIMA failed:", e)
        avg_sarima_rmse = float("inf")
        sarima_r2 = float("-inf")

    # -----------------------------
    # FINAL MODEL COMPARISON (RMSE + R²)
    # -----------------------------
    print("\n--- MODEL COMPARISON (FANCY)---")
    print(f"Random Forest Regression -> RMSE: {rf_rmse:.3f}, R²: {rf_r2:.3f}")
    print(f"SARIMA                   -> RMSE: {sarima_rmse:.3f}, R²: {sarima_r2:.3f}")

    rf_score = rf_rmse - (0.5 * rf_r2)
    sarima_score = sarima_rmse - (0.5 * sarima_r2)

    if sarima_score < rf_score:
        print("\nSelected Model: SARIMA")

        best_model = sarima_fit
        model_name = "SARIMA"
        y_pred = sarima_pred
        mae = sarima_mae
        rmse = sarima_rmse
        r2 = sarima_r2
        bias = sarima_bias

    else:
        print("\nSelected Model: Random Forest Regression")

        best_model = best_model_rf
        model_name = "Random Forest Regression"
        y_pred = rf_pred
        mae = rf_mae
        rmse = rf_rmse
        r2 = rf_r2
        bias = rf_bias

    # -----------------------------
    # FINAL OUTPUT
    # -----------------------------
    print("\nFinal Model Evaluation (FANCY):")
    print(f"Model: {model_name}")
    print(f"MAE: {mae:.3f}")
    print(f"RMSE: {rmse:.3f}")
    print(f"R²: {r2:.3f}")
    print(f"Bias: {bias:.3f}")

    return best_model, model_name, X_test, y_test, y_pred, bias, mae, rmse, r2