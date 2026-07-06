import calendar
import numpy as np

def forecast_3_months_M(results, df, municipality, target_column):

    model = results[municipality][target_column]["model"]
    features = results[municipality][target_column]["features"]

    df_muni = df[df["municipality"] == municipality].copy()

    # =========================
    # START FROM LAST ROW
    # =========================
    current_row = df_muni[features].iloc[-1:].copy()

    # last known values
    last_month = int(df_muni["month_num"].iloc[-1])

    forecasts = []
    months = []

    for step in range(3):

        # =========================
        # PREDICT
        # =========================
        pred = model.predict(current_row)[0]
        forecasts.append(pred)

        # advance month
        last_month += 1
        if last_month > 12:
            last_month = 1

        months.append(calendar.month_name[last_month])

        # =========================
        # CREATE NEW ROW (COPY OLD STATE)
        # =========================
        new_row = current_row.copy()

        # =========================
        # UPDATE TIME FEATURES
        # =========================
        if "month_num" in features:
            new_row["month_num"] = last_month

        if "month_sin" in features:
            new_row["month_sin"] = np.sin(2 * np.pi * last_month / 12)

        if "month_cos" in features:
            new_row["month_cos"] = np.cos(2 * np.pi * last_month / 12)

        # =========================
        # TRUE RECURSIVE LAG UPDATE
        # =========================
        if "price_lag3" in features:
            new_row["price_lag3"] = current_row["price_lag2"].values[0]

        if "price_lag2" in features:
            new_row["price_lag2"] = current_row["price_lag1"].values[0]

        if "price_lag1" in features:
            new_row["price_lag1"] = pred   # 🔥 KEY PART (recursive feed)

        # =========================
        # MOVE TO NEXT STEP
        # =========================
        current_row = new_row.copy()

        #DISPLAY