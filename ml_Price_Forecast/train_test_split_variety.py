from sklearn.model_selection import TimeSeriesSplit  # For splitting time-series data into train/validation
from sklearn.ensemble import RandomForestRegressor   # Random Forest model
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error  # Model evaluation metrics
from statsmodels.tsa.statespace.sarimax import SARIMAX  # SARIMA time-series model
import numpy as np  # For numerical operations
import warnings

warnings.filterwarnings("ignore")

# Define which columns to use as input features for the model
def train_variety_price(df, rmse_threshold=2.0, max_attempts=3):

    # start
    print("\nStart of Train and Testing (REGULAR)")

    features = [
        "month_num",  # Month number 1-12
        "month_sin",  # Sine transformation of month (seasonality)
        "month_cos",  # Cosine transformation of month
        "quarter",  # Quarter of the year
        "other_variety_price_lag1",  # Previous month's price
        "other_variety_price_lag2",  # 2 months ago
        "other_variety_price_lag3",  # 3 months ago
        "other_variety_price_roll3",  # 3-month rolling mean
        "other_variety_price_roll6",  # 6-month rolling mean
        "other_variety_price_std3",  # 3-month rolling std deviation
        "other_variety_price_change",  # Month-over-month change
        "yield_per_ha"  # Yield per hectare (agriculture factor)
    ]

    # Split data into train (80%) and test (20%) based on row index
    split_index = int(len(df) * 0.8)
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    # Separate features and target for training
    X_train = train_df[features] # Input features
    y_train = train_df["other_variety_price"] # Target variable (price)

    # Prepare test data
    X_test = test_df[features]
    y_test = test_df["other_variety_price"]

    # TimeSeriesSplit for cross-validation to respect time order
    tscv = TimeSeriesSplit(n_splits=5)

    #Random Forest Training
    attempt = 1
    best_rmse_rf = float("inf")  # Start with a very high RMSE
    best_model_rf = None  # Placeholder for best Random Forest model

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
                n_estimators=200 + (attempt * 50),
                max_depth=10 + attempt,
                min_samples_split=4,
                random_state=42
            )

            # Train model on training fold
            model.fit(X_tr, y_tr)
            # Predict on validation fold
            y_pred_val = model.predict(X_val)

            # Calculate RMSE
            rmse = np.sqrt(mean_squared_error(y_val, y_pred_val))
            scores.append(rmse) # Save RMSE

        avg_rmse = np.mean(scores) # Average RMSE over all folds
        print(f"RF Average RMSE: {avg_rmse:.3f}")

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
    rf_mae_regular = mean_absolute_error(y_test, rf_pred)
    rf_rmse_regular = np.sqrt(mean_squared_error(y_test, rf_pred))
    rf_r2_regular = r2_score(y_test, rf_pred)
    rf_bias_regular = y_test.mean() - rf_pred.mean() # Average bias

    print("\nRandom Forest Evaluation:")
    print(f"MAE: {rf_mae_regular:.3f}")
    print(f"RMSE: {rf_rmse_regular:.3f}")
    print(f"R²: {rf_r2_regular:.3f}")
    print(f"Bias: {rf_bias_regular:.3f}")

    # -----------------------------
    # SARIMA WITH VALIDATION
    # -----------------------------
    print("\n[SARIMA] Training with validation...")

    sarima_mae_r = sarima_rmse_r = sarima_r2_r = sarima_bias_r = None
    avg_sarima_rmse_r = float("inf")
    sarima_fit_r = None
    sarima_pred_r = None

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

            fit = model.fit(disp=False)  # Fit SARIMA
            pred = fit.forecast(steps=len(y_val)) # Forecast validation period

            rmse_s = np.sqrt(mean_squared_error(y_val, pred)) # RMSE for validation
            sarima_scores.append(rmse_s)

        avg_sarima_rmse_r = np.mean(sarima_scores) # Average RMSE
        print(f"SARIMA Avg RMSE (Validation): {avg_sarima_rmse_r:.3f}")

        # Train final SARIMA on all training data
        sarima_model = SARIMAX(
            y_train,
            order=(1, 1, 1),
            seasonal_order=(1, 1, 1, 12)
        )

        sarima_fit = sarima_model.fit(disp=False)
        sarima_pred = sarima_fit.forecast(steps=len(y_test)) # Forecast on test set

        # SARIMA evaluation metrics
        sarima_mae_regular = mean_absolute_error(y_test, sarima_pred)
        sarima_rmse_regular = np.sqrt(mean_squared_error(y_test, sarima_pred))
        sarima_r2_regular = r2_score(y_test, sarima_pred)
        sarima_bias_regular = y_test.mean() - sarima_pred.mean()

        print("\nSARIMA Model Evaluation:")
        print(f"MAE: {sarima_mae_regular:.3f}")
        print(f"RMSE: {sarima_rmse_regular:.3f}")
        print(f"R²: {sarima_r2_regular:.3f}")
        print(f"Bias: {sarima_bias_regular:.3f}")

    except Exception as e:
        print("SARIMA failed:", e)
        avg_sarima_rmse_r = float("inf")
        sarima_r2_r = float("inf")

    # -----------------------------
    # FINAL MODEL COMPARISON (RMSE + R²)
    # -----------------------------
    print("\n-----MODEL COMPARISON (REGULAR)------")
    print(f"Random Forest Regression -> RMSE: {rf_rmse_regular:.3f}, R²: {rf_r2_regular:.3f}")
    print(f"SARIMA                   -> RMSE: {sarima_rmse_regular:.3f}, R²: {sarima_r2_regular:.3f}")

    rf_score = rf_rmse_regular - (0.5 * rf_r2_regular)
    sarima_score = sarima_rmse_regular - (0.5 * sarima_r2_regular)

    if sarima_score < rf_score:
        print("\nSelected Model: SARIMA")

        best_model_regular = sarima_fit
        model_name_regular = "SARIMA"

        y_pred_regular = sarima_pred
        mae_regular = sarima_mae_regular
        rmse_regular = sarima_rmse_regular
        r2_regular = sarima_r2_regular
        bias_regular = sarima_bias_regular

    else:
        print("\nSelected Model: Random Forest")

        best_model_regular = best_model_rf
        model_name_regular = "Random Forest Regression"

        y_pred_regular = rf_pred
        mae_regular = rf_mae_regular
        rmse_regular = rf_rmse_regular
        r2_regular = rf_r2_regular
        bias_regular = rf_bias_regular

    # -----------------------------
    # FINAL METRICS
    # -----------------------------
    print("\nFinal Model Evaluation (REGULAR):")
    print(f"Model: {model_name_regular}")
    print(f"MAE: {mae_regular:.3f}")
    print(f"RMSE: {rmse_regular:.3f}")
    print(f"R²: {r2_regular:.3f}")
    print(f"Bias: {bias_regular:.3f}")

    # Return all relevant outputs
    return best_model_regular, model_name_regular, X_test, y_test, y_pred_regular, bias_regular, mae_regular, rmse_regular, r2_regular