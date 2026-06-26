import os
import numpy as np
import streamlit as st

from Data_Cleaning.Data_Cleaning_Capstone import run_cleaning
# =========================
# EDA
# =========================
from Exploratory_Data_Analysis.EDA_Capstone import run_eda

# =========================
# FEATURE ENGINEERING
# =========================
from Feature_Engineering.Feature_Engineering_Fancy import feature_engineering_fancy
from Feature_Engineering.Feature_Engineering_Yield import feature_engineering_yield
from Feature_Engineering.Feature_Engineering_Variety import feature_engineering_variety

# =========================
# TRAINING
# =========================
from ml_Price_Forecast.train_test_split_fancy import train_price_fancy
from ml_Price_Forecast.train_test_split_variety import train_variety_price
from ml_Yield_Forecast.train_test_split_yield import train_yield

# =========================
# FORECASTING
# =========================
from ml_Price_Forecast.Forecast_Price_Fancy import forecast_next_3_months
from ml_Price_Forecast.Forecast_Price_OtherVariety import forecast_next_3_months_variety
from ml_Yield_Forecast.forecast_yield import forecast_4quarters_yield

# =========================
# FILE PATH SETUP
# =========================
# Use relative paths so the app works on any machine
base_dir = os.path.dirname(__file__)

# Default pre-cleaned dataset (used if no upload)
default_cleaned = os.path.join(base_dir, "", "Capstone_Dataset_Cleaned_ML.xlsx")

# Temporary files for uploaded dataset
temp_input = os.path.join(base_dir, "", "temp_upload.xlsx")
temp_output = os.path.join(base_dir, "", "temp_cleaned.xlsx")
# =========================
# DATA SOURCE SELECTION (UPLOAD OR DEFAULT)
# =========================
# # Allow user to upload dataset
# uploaded_file = st.file_uploader("Upload Dataset", type=["xlsx", "csv"])
#
# if uploaded_file is not None:
#     # Save uploaded file temporarily
#     with open(temp_input, "wb") as f:
#         f.write(uploaded_file.getbuffer())
#
#     # Run cleaning to match ML-required format
#     run_cleaning(temp_input, temp_output)
#
#     # Use cleaned uploaded dataset
#     data_path = temp_output
#     st.success("Using uploaded dataset (cleaned automatically)")
#
# else:
#     # Use default pre-cleaned dataset
data_path = default_cleaned
#     st.info("Using default cleaned dataset")
#

# =========================
# EDA
# =========================
# Run exploratory data analysis using selected dataset
provincial_df, supply_df, municipality_df = run_eda(data_path)

# =========================
# FEATURE ENGINEERING
# =========================
df_fancy, df_features_fancy = feature_engineering_fancy(provincial_df)
df_regular, df_features_regular = feature_engineering_variety(provincial_df)
df_yield, df_features_yield = feature_engineering_yield(provincial_df)

# =========================================================
# FANCY MODEL
# =========================================================
regressor_fancy, model_name_fancy, X_test, y_test, y_pred, bias_fancy, mae_fancy, rmse_fancy, r2_fancy = train_price_fancy(df_fancy)

print("\nModel used for Fancy:", model_name_fancy)

forecast_3months_fancy = forecast_next_3_months(
    regressor_fancy,
    df_features_fancy,
    bias_fancy,
    model_name_fancy,
)

# =========================================================
# REGULAR VARIETY MODEL
# =========================================================
regressor_regular, model_name_regular, X_test, y_test, y_pred_regular, bias_regular, mae_regular, rmse_regular, r2_regular = train_variety_price(df_regular)

print("\nModel used for Regular:", model_name_regular)

forecast_variety_3months = forecast_next_3_months_variety(
    regressor_regular,
    df_features_regular,
    bias_regular,
    model_name_regular
)

# =========================================================
# YIELD MODEL
# =========================================================
regressor_yield, model_name_yield, X_test, y_test, y_pred_yield, bias_yield, mae_yield, rmse_yield, r2_yield = train_yield(df_yield)

forecast_quarterly_yield = forecast_4quarters_yield(
    regressor_yield,
    df_features_yield,
    bias_yield,
)
