import streamlit as st
import pandas as pd
import os
import subprocess
import sys
from pathlib import Path

from utils.upload_datasets import (
    save_temp_file,
    validate_template,
    archive_upload,
    append_to_raw_master,
    MASTER_FOLDER,
    CLEAN_FOLDER,
    TEMP_FOLDER,
    create_originals_backup
)
from utils.firebase_storage import (
    upload_raw_file,
    upload_cleaned_file,
    cleanup_temp_file,
)
from Data_Cleaning.Data_Cleaning_Capstone import run_cleaning

MASTER_PROVINCIAL_RAW = os.path.join(MASTER_FOLDER, "provincial_raw.xlsx")
MASTER_MUNICIPAL_RAW = os.path.join(MASTER_FOLDER, "municipality_raw.xlsx")
PROVINCIAL_CLEANED = os.path.join(CLEAN_FOLDER, "provincial_cleaned.xlsx")
MUNICIPALITY_CLEANED = os.path.join(CLEAN_FOLDER, "municipality_cleaned.xlsx")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PIPELINE_SCRIPT = PROJECT_ROOT / "scripts" / "run_pipeline.py"


def process_municipality(muni_temp_path):
    """Process municipality upload: validate and upload to Firebase Storage."""
    try:
        df = pd.read_excel(muni_temp_path, engine='openpyxl')
        validate_template(df, "Municipality")
        cloud_path = upload_raw_file(muni_temp_path, "Municipality")
        if cloud_path:
            st.success(f"Raw municipality file uploaded to Firebase Storage.")
        else:
            st.warning("Firebase Storage upload failed for municipality.")
        st.success("Municipality dataset validated successfully.")
    except Exception as e:
        st.error(f"[process_municipality ERROR] {e}")
        st.exception(e)
        raise


def process_provincial(prov_temp_path):
    """Process provincial upload: validate and upload to Firebase Storage."""
    try:
        df = pd.read_excel(prov_temp_path, engine='openpyxl')
        validate_template(df, "Provincial")
        cloud_path = upload_raw_file(prov_temp_path, "Provincial")
        if cloud_path:
            st.success(f"Raw provincial file uploaded to Firebase Storage.")
        else:
            st.warning("Firebase Storage upload failed for provincial.")
        st.success("Provincial dataset validated successfully.")
    except Exception as e:
        st.error(f"[process_provincial ERROR] {e}")
        st.exception(e)
        raise


def run_forecasting_pipeline(provincial_path: str, municipal_path: str) -> bool:
    """
    Run the forecasting pipeline as a subprocess with a clean st.status() UI wrapper.
    Returns True on success, False on failure.
    """
    try:
        # Use st.status for a clean, collapsible progress UI
        with st.status("Running forecasting pipeline (training + inference)...", expanded=True) as status:
            status.write("Starting pipeline subprocess...")
            
            result = subprocess.run(
                [sys.executable, str(PIPELINE_SCRIPT),
                 "--provincial", provincial_path,
                 "--municipal", municipal_path],
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=str(PROJECT_ROOT)
            )

            if result.returncode != 0:
                status.update(label="Pipeline failed", state="error", expanded=True)
                st.error(f"Pipeline failed with return code {result.returncode}")
                if result.stderr:
                    st.code(result.stderr, language="bash")
                return False

            status.update(label="Pipeline completed successfully", state="complete", expanded=False)
            
            # Show output in expandable section
            if result.stdout:
                with st.expander("Pipeline Output"):
                    st.code(result.stdout, language="text")

        return True

    except subprocess.TimeoutExpired:
        st.error("Pipeline timed out after 10 minutes.")
        return False
    except Exception as e:
        st.error(f"Failed to run pipeline: {e}")
        return False


def upload_dataset():

    st.markdown("## **Dataset Management**")
    st.caption("Upload the latest datasets to update the forecasting system.")
    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_files = st.file_uploader(
            "Upload Provincial and/or Municipality Dataset",
            type=["xlsx"],
            accept_multiple_files=True,
            key="dataset_upload"
        )
        if uploaded_files:
            for file in uploaded_files:
                st.success(file.name)

    with col2:
        with open("data/templates/provincial_template.xlsx", "rb") as file:
            st.download_button(
                "Provincial Template",
                data=file,
                file_name="Provincial_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        with open("data/templates/municipality_template.xlsx", "rb") as file:
            st.download_button(
                "Municipality Template",
                data=file,
                file_name="Municipality_Template.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

    # ---------- UPLOAD BUTTON ----------
    if st.button(
            "Upload Dataset",
            use_container_width=True,
            key="upload_dataset"
    ):

        st.info("Upload pipeline triggered...")

        try:

            if not uploaded_files:
                st.warning("Please upload at least one dataset.")
                return

            st.write(f"Found {len(uploaded_files)} file(s) to process.")

            prov_file_path = None
            muni_file_path = None
            prov_file_name = None
            muni_file_name = None

            for file in uploaded_files:
                temp_path = save_temp_file(file)
                df = pd.read_excel(temp_path, engine='openpyxl')

                try:
                    validate_template(df, "Provincial")
                    prov_file_path = temp_path
                    prov_file_name = file.name
                    continue
                except Exception:
                    pass

                try:
                    validate_template(df, "Municipality")
                    muni_file_path = temp_path
                    muni_file_name = file.name
                    continue
                except Exception:
                    pass

                st.error(f"{file.name} is not a valid template.")
                return

            prov_file = prov_file_path
            muni_file = muni_file_path

            if prov_file_path:
                try:
                    process_provincial(prov_file_path)
                except Exception as e:
                    st.error(f"Error in process_provincial: {e}")
                    return
            if muni_file_path:
                try:
                    process_municipality(muni_file_path)
                except Exception as e:
                    st.error(f"Error in process_municipality: {e}")
                    return

            # ---------- SAVE TO RAW MASTER (PRESERVES ALL SHEETS) ----------
            if prov_file:
                try:
                    append_to_raw_master(prov_file, "Provincial")
                    st.success("Provincial data saved to master (all sheets preserved).")
                except Exception as e:
                    st.error(f"Failed to save provincial to master: {e}")
                    return

            if muni_file:
                try:
                    append_to_raw_master(muni_file, "Municipality")
                    st.success("Municipality data saved to master.")
                except Exception as e:
                    st.error(f"Failed to save municipality to master: {e}")
                    return

            # ---------- RUN CLEANING ----------
            try:
                run_cleaning(
                    MASTER_PROVINCIAL_RAW, PROVINCIAL_CLEANED,
                    MASTER_MUNICIPAL_RAW, MUNICIPALITY_CLEANED,
                    clean_provincial=(prov_file is not None),
                    clean_municipality=(muni_file is not None)
                )
            except FileNotFoundError as e:
                st.error(f"Cleaning failed. File not found: {e}")
                st.info("TIP: Upload BOTH Provincial and Municipality files, or ensure the raw master files exist from a previous full upload.")
                return
            except Exception as e:
                st.error(f"Cleaning failed: {e}")
                return

            prov_exists = os.path.exists(PROVINCIAL_CLEANED)
            muni_exists = os.path.exists(MUNICIPALITY_CLEANED)
            if not prov_exists and not muni_exists:
                st.error("Cleaning ran, but NO cleaned output files were found.")
                return
            elif not prov_exists and prov_file:
                st.warning("Cleaning ran, but PROVINCIAL_CLEANED was NOT created.")
                return
            elif not muni_exists and muni_file:
                st.warning("Cleaning ran, but MUNICIPALITY_CLEANED was NOT created.")
                return

            st.success("Datasets cleaned successfully.")

            # Upload cleaned files to Firebase Storage
            if prov_exists:
                if upload_cleaned_file(PROVINCIAL_CLEANED, "Provincial"):
                    st.success("Provincial cleaned data uploaded to Firebase Storage.")
                else:
                    st.warning("Could not upload provincial cleaned data to Firebase Storage.")

            if muni_exists:
                if upload_cleaned_file(MUNICIPALITY_CLEANED, "Municipality"):
                    st.success("Municipality cleaned data uploaded to Firebase Storage.")
                else:
                    st.warning("Could not upload municipality cleaned data to Firebase Storage.")

            # ---------- RUN FORECASTING PIPELINE (via subprocess with st.status) ----------
            pipeline_success = run_forecasting_pipeline(
                provincial_path=PROVINCIAL_CLEANED if prov_exists else MASTER_PROVINCIAL_RAW,
                municipal_path=MUNICIPALITY_CLEANED if muni_exists else MASTER_MUNICIPAL_RAW
            )

            if not pipeline_success:
                st.error("Forecasting pipeline failed. Check the output above for details.")
                return

            st.success("Forecasting pipeline completed successfully!")

            # ---------- FINISH ----------
            create_originals_backup()
            st.session_state["upload_success"] = True
            st.session_state["upload_refresh_key"] = st.session_state.get("upload_refresh_key", 0) + 1

            # Clear Streamlit caches so new data loads on next page view
            try:
                st.cache_resource.clear()
                st.cache_data.clear()
            except Exception:
                pass

            st.success("Dataset pipeline completed successfully! You can now go back to Dashboard to see the updated data.")

        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.exception(e)