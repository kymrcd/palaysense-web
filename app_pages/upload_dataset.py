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
    create_originals_backup,
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
            st.success("Municipality raw file backed up to Firebase Storage — secure.")
        else:
            st.warning("Firebase backup skipped for municipality (local save still succeeded).")
        st.success("Municipality dataset validated — ready for cleaning.")
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
            st.success("Provincial raw file backed up to Firebase Storage — secure.")
        else:
            st.warning("Firebase backup skipped for provincial (local save still succeeded).")
        st.success("Provincial dataset validated — ready for cleaning.")
    except Exception as e:
        st.error(f"[process_provincial ERROR] {e}")
        st.exception(e)
        raise


def run_forecasting_pipeline(provincial_path: str, municipal_path: str) -> bool:
    """
    Run the forecasting pipeline as a subprocess with HONEST live progress.

    Cleaning is ALREADY done before this call (run_cleaning), so this pipeline
    only covers: Feature Engineering + Training (RF vs SARIMA) + Forecast generation.
    We stream stdout line-by-line so the UI never freezes at fake 90%.
    """
    import time

    progress_bar = st.progress(0, text="Starting pipeline... 0%")
    log_lines: list[str] = []
    # Live log placeholder inside the st.status so user sees movement
    with st.status("Running forecasting pipeline (training + inference)...", expanded=True) as status:
        status.write("Cleaning already done — starting training pipeline...")
        progress_bar.progress(5, text="Pipeline started... 5%")

        try:
            # Build args — only include branch that was uploaded (single-type upload = skip other, avoid NoneType error)
            _popen_args = [sys.executable, str(PIPELINE_SCRIPT)]
            if provincial_path is not None:
                _popen_args.extend(["--provincial", str(provincial_path)])
            if municipal_path is not None:
                _popen_args.extend(["--municipal", str(municipal_path)])
            # Popen with line-buffered streaming + merged stderr → stdout so we never deadlock
            proc = subprocess.Popen(
                _popen_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                cwd=str(PROJECT_ROOT),
            )

            # Placeholder for live tail (last 25 lines) — proves it's not frozen
            log_placeholder = st.empty()
            last_progress = 5

            # Map pipeline log keywords → honest progress %
            def _progress_for_line(line: str) -> int | None:
                l = line.lower()
                if "running eda" in l:
                    return 15
                if "feature engineering" in l:
                    return 30
                if "training provincial" in l or "training with validation" in l or "[rf] attempt" in l:
                    return 55
                if "training municipal" in l or "municipality:" in l:
                    return 75
                if "generating forward" in l or "forecast" in l and "saving" not in l:
                    return 88
                if "saved provincial forecasts" in l or "saved municipal forecasts" in l:
                    return 95
                if "pipeline completed" in l:
                    return 100
                return None

            # Stream until process ends (with wall-clock timeout)
            start_ts = time.time()
            timeout_sec = 1800
            while True:
                # wall-clock timeout
                if time.time() - start_ts > timeout_sec:
                    proc.kill()
                    status.update(label="Pipeline timed out — check logs", state="error", expanded=True)
                    st.error(f"Pipeline timed out after {timeout_sec//60} minutes. Try with a smaller file.")
                    if log_lines:
                        with st.expander("Pipeline logs (before timeout)", expanded=True):
                            st.code("".join(log_lines[-200:]), language="text")
                    return False

                line = proc.stdout.readline() if proc.stdout else ""
                if line:
                    log_lines.append(line)
                    # live tail rendering
                    tail = "".join(log_lines[-25:])
                    log_placeholder.code(tail, language="text")
                    p = _progress_for_line(line)
                    if p is not None and p > last_progress:
                        last_progress = p
                        progress_bar.progress(p, text=f"{line.strip()[:60]}... {p}%")
                elif proc.poll() is not None:
                    break
                else:
                    time.sleep(0.05)

            proc.wait()
            # drain any remaining
            if proc.stdout:
                rest = proc.stdout.read()
                if rest:
                    log_lines.append(rest)

            if proc.returncode != 0:
                status.update(label="Pipeline failed — check details below", state="error", expanded=True)
                st.error("Forecasting failed. Pipeline exited with error.")
                # show last 150 lines — most relevant
                if log_lines:
                    st.code("".join(log_lines[-150:]), language="text")
                else:
                    st.caption("No output captured — check `data/forecasts/` and terminal logs.")
                progress_bar.progress(last_progress, text=f"Failed at {last_progress}%")
                return False

            progress_bar.progress(100, text="Done! 100%")
            status.update(label="Forecasting completed — all models trained", state="complete", expanded=False)
            if log_lines:
                with st.expander("View detailed pipeline logs", expanded=False):
                    st.code("".join(log_lines), language="text")
            return True

        except subprocess.TimeoutExpired:
            status.update(label="Pipeline timed out", state="error", expanded=True)
            st.error("Pipeline timed out after 30 minutes. Please try with a smaller file.")
            return False
        except Exception as e:
            status.update(label="Forecasting error", state="error", expanded=True)
            st.error(f"Forecasting error: {e}")
            if log_lines:
                with st.expander("Logs before error"):
                    st.code("".join(log_lines[-100:]), language="text")
            return False


def upload_dataset():

    st.markdown("## **Dataset Management**")
    st.caption("Upload the latest datasets to update the forecasting system. Data will be cleaned and forecasts will be generated automatically.")
    st.divider()
    # Simple success banner from session_state (no file persist)
    if st.session_state.get("upload_success"):
        ts = st.session_state.get("upload_success_time", "")
        rk = st.session_state.get("upload_refresh_key", 0)
        st.success(f"✅ Last import successful — forecasts updated! {ts} (refresh_key={rk})")
        if st.button("Dismiss ✓", key="dismiss_success", use_container_width=True):
            st.session_state["upload_success"] = False
            st.session_state.pop("upload_success_time", None)
            st.rerun()

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

                try:
                    df = pd.read_excel(temp_path, engine='openpyxl')
                except Exception as e:
                    st.error(f"❌ {file.name}: Cannot read Excel — {e}")
                    return

                # --- 2. Template validation ---
                prov_err, muni_err = None, None
                try:
                    validate_template(df, "Provincial")
                    prov_file_path = temp_path
                    prov_file_name = file.name
                    st.success(f"✅ {file.name}: Provincial template — validated ({len(df)} rows)")
                    continue
                except Exception as e:
                    prov_err = str(e)

                try:
                    validate_template(df, "Municipality")
                    muni_file_path = temp_path
                    muni_file_name = file.name
                    st.success(f"✅ {file.name}: Municipality template — validated ({len(df)} rows)")
                    continue
                except Exception as e:
                    muni_err = str(e)

                # Neither template passed — show detailed reason
                st.error(f"❌ {file.name} is not a valid template.")
                with st.expander(f"Why {file.name} failed?"):
                    st.write("**Provincial check:**", prov_err)
                    st.write("**Municipality check:**", muni_err)
                    st.write("**Tip:** Year must be 2000-2027, Month = January-December, Province/Municipality not empty, Month_Num must match Month if present.")
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
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

            # ---------- SAVE TO RAW MASTER ----------
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
                st.error("Cleaning completed, but no cleaned files were created. Please check your input files.")
                return
            elif not prov_exists and prov_file:
                st.warning("Provincial cleaning did not produce output. Please check the provincial file.")
                return
            elif not muni_exists and muni_file:
                st.warning("Municipal cleaning did not produce output. Please check the municipal file.")
                return

            st.success("Datasets cleaned and validated — ready for forecasting.")

            if prov_exists:
                if upload_cleaned_file(PROVINCIAL_CLEANED, "Provincial"):
                    st.success("Provincial cleaned file backed up to Firebase Storage.")
                else:
                    st.caption("Provincial cleaned file saved locally (Firebase backup skipped).")

            if muni_exists:
                if upload_cleaned_file(MUNICIPALITY_CLEANED, "Municipality"):
                    st.success("Municipal cleaned file backed up to Firebase Storage.")
                else:
                    st.caption("Municipal cleaned file saved locally (Firebase backup skipped).")

            # ---------- RUN FORECASTING PIPELINE (only for uploaded types — provincial alone won't trigger 30-min municipal) ----------
            pipeline_success = run_forecasting_pipeline(
                provincial_path=PROVINCIAL_CLEANED if prov_file is not None else None,
                municipal_path=MUNICIPALITY_CLEANED if muni_file is not None else None
            )

            if not pipeline_success:
                st.error("Forecasting did not complete. Please review the pipeline output above.")
                return

            # ---- Success: visible inside AND after the pipeline ----
            try:
                st.toast("Forecasting completed — forecasts are ready!", icon="✅")
            except Exception:
                pass
            st.success("✅ Forecasting completed — forecasts are ready!")

            create_originals_backup()
            from datetime import datetime as _dt
            _now_str = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
            _new_key = st.session_state.get("upload_refresh_key", 0) + 1
            st.session_state["upload_success"] = True
            st.session_state["upload_success_time"] = _now_str
            st.session_state["upload_refresh_key"] = _new_key
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass
            st.success(f"🎉 All done! Forecasts updated (refresh_key={_new_key}).")
            st.caption("Parquet mtimes updated: provincial/municipal forecasts + history.")
            st.balloons()
            c1, c2 = st.columns(2)
            with c1:
                if st.button("↻ Reset uploader", use_container_width=True, key="post_pipeline_rerun"):
                    st.rerun()
            with c2:
                st.link_button("Go to LGU Dashboard →", url="?page=lgu_dashboard", use_container_width=True)

        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.exception(e)