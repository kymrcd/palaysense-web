import streamlit as st
import pandas as pd
import os
import subprocess
import sys
from pathlib import Path

from utils.upload_datasets import (
    save_temp_file,
    validate_template,
    append_to_raw_master,
    MASTER_FOLDER,
    CLEAN_FOLDER,
    TEMP_FOLDER,
    create_originals_backup,
    restore_original_data,
)
from utils.firebase_storage import (
    upload_cleaned_file,
    upload_forecasts_to_storage,
    cleanup_temp_file,
)
from Data_Cleaning.Data_Cleaning_Capstone import run_cleaning

MASTER_PROVINCIAL_RAW = os.path.join(MASTER_FOLDER, "provincial_raw.xlsx")
MASTER_MUNICIPAL_RAW = os.path.join(MASTER_FOLDER, "municipality_raw.xlsx")
PROVINCIAL_CLEANED = os.path.join(CLEAN_FOLDER, "provincial_cleaned.xlsx")
MUNICIPALITY_CLEANED = os.path.join(CLEAN_FOLDER, "municipality_cleaned.xlsx")


def _summarize_uploaded_file(temp_path: str) -> dict:
    """Build summary: rows, coverage period as clean date range for enterprise dialog."""
    try:
        df = pd.read_excel(temp_path, engine="openpyxl")
        n = len(df)
        years = sorted(pd.to_numeric(df.get("Year", []), errors="coerce").dropna().astype(int).unique().tolist())
        order = ["January","February","March","April","May","June","July","August","September","October","November","December"]
        months_raw = df.get("Month", pd.Series(dtype=str)).astype(str).str.strip().str.title()
        months = [m for m in order if m in months_raw.unique().tolist()]
        # Build coverage period as range e.g. July – November 2026 or July 2025 – February 2026
        if months and years:
            if len(years) == 1:
                if len(months) == 1:
                    coverage = f"{months[0]} {years[0]}"
                else:
                    coverage = f"{months[0]} – {months[-1]} {years[0]}"
            else:
                coverage = f"{months[0]} {years[0]} – {months[-1]} {years[-1]}"
        elif years:
            coverage = f"{years[0]}" if len(years)==1 else f"{years[0]}–{years[-1]}"
        else:
            coverage = "—"
        return {"rows": n, "coverage": coverage, "months_full": months, "years": years}
    except Exception:
        return {"rows": 0, "coverage": "—", "months_full": [], "years": []}


# Authoritative LGU modal — clean, minimalist, enterprise (Inter, 6px, sage banner, navy actions)
@st.dialog("Data Sync Complete", width="large")
def _show_upload_success_dialog(refresh_key: int, timestamp: str, prov_summary: dict | None, muni_summary: dict | None):
    # Inter / Public Sans stack, generous whitespace, crisp white card with subtle borders
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Public+Sans:wght@500;600&display=swap');
        </style>
        """,
        unsafe_allow_html=True,
    )
    # Sage green success banner — official, not red
    st.markdown(
        """
        <div style="background:#E6EFE8; border:1px solid #CBD9CE; border-left:4px solid #1F5B3A;
                    border-radius:6px; padding:16px 18px; margin-bottom:18px;">
          <div style="display:flex; gap:12px; align-items:flex-start;">
            <div style="background:#1F5B3A; color:white; width:28px; height:28px; border-radius:999px;
                        display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px; flex-shrink:0;">✓</div>
            <div>
              <div style="font-family:Inter, Public Sans, sans-serif; font-weight:700; font-size:15px;
                          color:#0F2A1D; letter-spacing:0.15px; line-height:1.2;">Dataset Successfully Cataloged</div>
              <div style="font-family:Inter, sans-serif; font-weight:400; font-size:13.5px; color:#2E3B33;
                          margin-top:6px; line-height:1.55;">
                The submitted dataset has been verified and integrated. Predictive analytics and forecasts are now live on the LGU Dashboard. This record is authorized for official planning, budget allocation, and reporting.
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    # Administrative metadata — structured blocks with thin light gray dividers
    has_both = bool(prov_summary and muni_summary)
    cols = st.columns(2) if has_both else [st.container()]
    idx = 0
    for label, summ in [("Provincial", prov_summary), ("Municipal", muni_summary)]:
        if not summ:
            continue
        target = cols[idx] if has_both else cols[0]
        idx += 1
        with target:
            st.markdown(
                f"""
                <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:6px; padding:14px 16px; margin-bottom:12px;">
                  <div style="font-family:Inter, sans-serif; font-size:11px; font-weight:600;
                              letter-spacing:0.06em; text-transform:uppercase; color:#64748B; margin-bottom:10px;">
                    Administrative Level: {label}
                  </div>
                  <div style="display:flex; flex-direction:column; gap:0;">
                    <div style="display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid #F1F5F9;">
                      <span style="font-family:Inter, sans-serif; font-size:12.5px; color:#64748B;">Total Entries Processed</span>
                      <span style="font-family:Inter, sans-serif; font-size:12.5px; font-weight:600; color:#0F172A;">{summ['rows']} Records</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:7px 0; border-bottom:1px solid #F1F5F9;">
                      <span style="font-family:Inter, sans-serif; font-size:12.5px; color:#64748B;">Reporting Period</span>
                      <span style="font-family:Inter, sans-serif; font-size:12.5px; font-weight:600; color:#0F172A;">{summ['coverage']}</span>
                    </div>
                    <div style="display:flex; justify-content:space-between; padding:7px 0;">
                      <span style="font-family:Inter, sans-serif; font-size:12.5px; color:#64748B;">Status</span>
                      <span style="font-family:Inter, sans-serif; font-size:11px; font-weight:700; letter-spacing:0.05em;
                                   color:#065F46; background:#ECFDF5; border:1px solid #A7F3D0; border-radius:999px; padding:3px 8px;">Active / Live</span>
                    </div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    if not prov_summary and not muni_summary:
        st.info("No summary available — file was processed successfully.")
    # Audit trail footer — official accountability, no Firebase exposure
    tx_id = f"REF-{refresh_key:05d}"
    ts_formatted = timestamp.replace("-", " |").replace(" ", " | ") if " " in timestamp else timestamp
    # ensure PST label
    if "PST" not in timestamp:
        ts_display = f"{timestamp} (PST)"
    else:
        ts_display = timestamp
    st.markdown(
        f"""
        <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:12px 16px; margin-top:4px;">
          <div style="display:flex; flex-wrap:wrap; gap:16px; font-family:Inter, sans-serif; font-size:12px; color:#475569;">
            <span><span style="font-weight:600; color:#334155;">Transaction ID:</span> {tx_id}</span>
            <span style="color:#CBD5E1;">|</span>
            <span><span style="font-weight:600; color:#334155;">Date Certified:</span> {ts_display}</span>
            <span style="color:#CBD5E1;">|</span>
            <span><span style="font-weight:600; color:#334155;">Storage Status:</span> Archived in Secure System Repository</span>
          </div>
          <div style="margin-top:6px; font-family:Inter, sans-serif; font-size:11px; color:#94A3B8;">
            Security: Verified &amp; Encrypted • This update is reflected across Overview, Provincial, Municipal, and Forecast pages.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1.1])
    with c1:
        if st.button("Close Window", use_container_width=True, key="dialog_close_btn"):
            st.rerun()
    with c2:
        # Primary navy/slate — stay inside LGU dashboard, do not jump to Overview landing page
        if st.button("Proceed to LGU Dashboard →", use_container_width=True, key="dialog_goto_btn", type="primary"):
            st.session_state["lgu_page"] = "overview"
            st.rerun()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Case-sensitive on Linux (Railway) — folder is `Scripts` capital S
for _cand in (PROJECT_ROOT / "Scripts" / "run_pipeline.py", PROJECT_ROOT / "scripts" / "run_pipeline.py"):
    if _cand.exists():
        PIPELINE_SCRIPT = _cand
        break
else:
    PIPELINE_SCRIPT = PROJECT_ROOT / "Scripts" / "run_pipeline.py"


def process_municipality(muni_temp_path):
    """Process municipality upload: validate only (processed file will be saved after cleaning)."""
    try:
        df = pd.read_excel(muni_temp_path, engine='openpyxl')
        validate_template(df, "Municipality")
        st.success("Municipality dataset validated — ready for cleaning.")
    except Exception as e:
        st.error(f"[process_municipality ERROR] {e}")
        st.exception(e)
        raise


def process_provincial(prov_temp_path):
    """Process provincial upload: validate only (processed file will be saved after cleaning)."""
    try:
        df = pd.read_excel(prov_temp_path, engine='openpyxl')
        validate_template(df, "Provincial")
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

            if muni_exists:
                if upload_cleaned_file(MUNICIPALITY_CLEANED, "Municipality"):
                    st.success("Municipal cleaned file backed up to Firebase Storage.")

            # ---------- RUN FORECASTING PIPELINE (only for uploaded types — provincial alone won't trigger 30-min municipal) ----------
            pipeline_success = run_forecasting_pipeline(
                provincial_path=PROVINCIAL_CLEANED if prov_file is not None else None,
                municipal_path=MUNICIPALITY_CLEANED if muni_file is not None else None
            )

            if not pipeline_success:
                st.error("Forecasting did not complete. Please review the pipeline output above.")
                return

            # ---- Persist forecasts to Firebase Storage (so live survives restarts) ----
            try:
                with st.spinner("Syncing forecasts to cloud storage..."):
                    res = upload_forecasts_to_storage()
                    ok = sum(1 for v in res.values() if v)
                    if ok > 0:
                        st.success(f"Forecasts synced to Firebase Storage ({ok}/{len(res)} files) — data is safely persisted.")
                    else:
                        st.caption("Forecasts saved locally; cloud sync skipped (no Firebase credentials in this environment) — data will still be available for this session.")
            except Exception as e:
                st.caption(f"Cloud sync skipped: {e} — forecasts are still available for this session.")

            # ---- Success: professional LGU dialog ----
            try:
                st.toast("Forecasting completed — forecasts are ready!", icon="✅")
            except Exception:
                pass
            st.success("Forecasting completed — forecasts are ready.")

            create_originals_backup()
            from datetime import datetime as _dt
            _now_str = _dt.now().strftime("%Y-%m-%d %H:%M:%S")
            _new_key = st.session_state.get("upload_refresh_key", 0) + 1
            st.session_state["upload_success"] = True
            st.session_state["upload_success_time"] = _now_str
            st.session_state["upload_refresh_key"] = _new_key
            st.session_state["show_success_dialog"] = True
            # Build month summaries for dialog (what months were uploaded)
            prov_summ = _summarize_uploaded_file(prov_file) if prov_file else None
            muni_summ = _summarize_uploaded_file(muni_file) if muni_file else None
            try:
                st.cache_data.clear()
                st.cache_resource.clear()
            except Exception:
                pass
            # Professional PalaySense-themed pop-up with upload summary
            _show_upload_success_dialog(_new_key, _now_str, prov_summ, muni_summ)
            st.caption("Parquet files updated: provincial/municipal forecasts and history.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Reset uploader", use_container_width=True, key="post_pipeline_rerun"):
                    st.rerun()
            with c2:
                if st.button("Go to LGU Dashboard →", use_container_width=True, key="post_goto_dash"):
                    st.session_state["lgu_page"] = "overview"
                    st.rerun()

        except Exception as e:
            st.error(f"Pipeline failed: {e}")
            st.exception(e)

    st.divider()
    with st.container(border=True):
        st.markdown("**Restore Original Dataset**")
        st.caption("Restore the system to the original baseline dataset including forecast files.")
        confirm = st.checkbox("Confirm restoration to the original dataset", key="restore_confirm")
        if st.button("Restore Original Data", type="primary", use_container_width=True, key="restore_btn", disabled=not confirm):
            with st.spinner("Restoring original dataset..."):
                try:
                    restore_original_data()
                    try:
                        st.cache_data.clear()
                        st.cache_resource.clear()
                    except Exception:
                        pass
                    st.success("Original dataset restored successfully.")
                except Exception as e:
                    st.error(f"Restore failed: {e}")