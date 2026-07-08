import streamlit as st
import pandas as pd

from utils.upload_dataset import (
    save_temp_file,
    validate_template,
    archive_upload,
    append_to_raw_master
)
from Data_Cleaning.Data_Cleaning_Capstone import (
    run_cleaning,
    file_path,
    output_path,
    file_path2,
    output_path2,
)

from Exploratory_Data_Analysis.EDA_Capstone import run_eda

from Feature_Engineering.Feature_Engineering_Fancy import feature_engineering_fancy
from Feature_Engineering.Feature_Engineering_Variety import feature_engineering_variety
from Feature_Engineering.Feature_Engineering_Yield import feature_engineering_yield

from ml_Price_Forecast.train_test_split_fancy import train_price_fancy

from ml_Price_Forecast.train_test_split_variety import train_variety_price

from ml_Yield_Forecast.train_test_split_yield import train_yield
from ml_Price_Forecast.Forecast_Price_Fancy import (
    forecast_next_3_months
)

from ml_Price_Forecast.Forecast_Price_OtherVariety import (
    forecast_next_3_months_variety
)

from ml_Yield_Forecast.forecast_yield import (
    forecast_4quarters_yield
)
def upload_dataset():



    st.title("📂 Dataset Management")

    st.write(
        "Upload the latest datasets to update the forecasting system."
    )

    st.divider()

    # ==========================================================
    # MUNICIPALITY DATASET
    # ==========================================================
    st.subheader("🏘 Municipality Dataset")

    muni_file = st.file_uploader(
        "Upload Municipality Dataset",
        type=["xlsx"],
        key="municipality_file"
    )

    if muni_file is not None:

        st.success(f"Selected File: {muni_file.name}")

        if st.button(
            "Upload Municipality Dataset",
            use_container_width=True,
            key="upload_municipality"
        ):

            try:

                # Save temporarily
                temp_path = save_temp_file(muni_file)

                # Read file
                df = pd.read_excel(temp_path)

                # Validate template
                validate_template(df, "Municipality")

                # Save original upload
                archive_upload(temp_path, "Municipality")

                # Append to historical dataset
                master_path = append_to_raw_master(
                    temp_path,
                    "Municipality"
                )

                st.success("Historical dataset updated.")

                # ================================
                # CLEAN DATA
                # ================================
                with st.spinner("Cleaning dataset..."):

                    run_cleaning(
                        file_path,
                        output_path,
                        file_path2,
                        output_path2
                    )

                st.success("Dataset cleaned successfully.")

                # ================================
                # NEXT PIPELINE
                # ================================
                st.info("Retraining municipality model... (Next Step)")
                st.info("Updating dashboard... (Next Step)")

            except Exception as e:
                st.error(e)

    st.divider()

    # ==========================================================
    # PROVINCIAL DATASET
    # ==========================================================
    st.subheader("🏛 Provincial Dataset")

    prov_file = st.file_uploader(
        "Upload Provincial Dataset",
        type=["xlsx"],
        key="provincial_file"
    )

    if prov_file is not None:

        st.success(f"Selected File: {prov_file.name}")

        if st.button(
            "Upload Provincial Dataset",
            use_container_width=True,
            key="upload_provincial"
        ):

            try:

                # Save temporarily
                temp_path = save_temp_file(prov_file)

                # Read file
                df = pd.read_excel(temp_path)

                # Validate template
                validate_template(df, "Provincial")

                # Save original upload
                archive_upload(temp_path, "Provincial")

                # Append to historical dataset
                master_path = append_to_raw_master(
                    temp_path,
                    "Provincial"
                )

                st.success("Historical dataset updated.")

                # ================================
                # CLEAN DATA
                # ================================
                with st.spinner("Cleaning dataset..."):

                    run_cleaning(
                        file_path,
                        output_path,
                        file_path2,
                        output_path2
                    )

                st.success("Dataset cleaned successfully.")

                # ================================
                # EDA
                # ================================
                with st.spinner("Running Exploratory Data Analysis..."):

                    provincial_df, supply_df, municipality_df = run_eda(output_path)

                st.success("EDA completed.")

                # ================================
                # FEATURE ENGINEERING
                # ================================
                with st.spinner("Generating ML Features..."):

                    fancy_df, fancy_features = feature_engineering_fancy(provincial_df)

                    variety_df, variety_features = feature_engineering_variety(provincial_df)

                    yield_df, yield_features = feature_engineering_yield(provincial_df)

                st.success("Feature engineering completed.")

                # ================================
                # TRAIN MODELS
                # ================================
                with st.spinner("Training forecasting models..."):

                    (
                        fancy_model,
                        fancy_model_name,
                        _,
                        _,
                        _,
                        fancy_bias,
                        fancy_mae,
                        fancy_rmse,
                        fancy_r2
                    ) = train_price_fancy(fancy_df)

                    (
                        variety_model,
                        variety_model_name,
                        _,
                        _,
                        _,
                        variety_bias,
                        variety_mae,
                        variety_rmse,
                        variety_r2
                    ) = train_variety_price(variety_df)

                    (
                        yield_model,
                        yield_model_name,
                        _,
                        _,
                        _,
                        yield_bias,
                        yield_mae,
                        yield_rmse,
                        yield_r2
                    ) = train_yield(yield_df)

                st.success("Models retrained successfully.")
                st.subheader("Training Results")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Fancy Price RMSE",
                        f"{fancy_rmse:.3f}"
                    )
                    st.caption(f"Model: {fancy_model_name}")

                with col2:
                    st.metric(
                        "Regular Price RMSE",
                        f"{variety_rmse:.3f}"
                    )
                    st.caption(f"Model: {variety_model_name}")

                with col3:
                    st.metric(
                        "Yield RMSE",
                        f"{yield_rmse:.3f}"
                    )
                    st.caption(f"Model: {yield_model_name}")
                # ================================
                # FORECAST
                # ================================
                with st.spinner("Generating forecasts..."):

                    fancy_forecast = forecast_next_3_months(
                        fancy_model,
                        fancy_features,
                        fancy_bias,
                        fancy_model_name
                    )

                    variety_forecast = forecast_next_3_months_variety(
                        variety_model,
                        variety_features,
                        variety_bias,
                        variety_model_name
                    )

                    yield_forecast = forecast_4quarters_yield(
                        yield_model,
                        yield_features,
                        yield_bias
                    )

                st.success("Forecasts generated successfully.")

            except Exception as e:
                st.error(e)

