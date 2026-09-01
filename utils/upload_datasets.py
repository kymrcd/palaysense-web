import os
import shutil
from pathlib import Path
from datetime import datetime
import pandas as pd


# ==========================================================
# BASE PATHS
# ==========================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TEMP_FOLDER = os.path.join(BASE_DIR, "data", "temp")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "data", "uploads")
MASTER_FOLDER = os.path.join(BASE_DIR, "data", "Master")
CLEAN_FOLDER = os.path.join(BASE_DIR, "data", "cleaned")

os.makedirs(TEMP_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(MASTER_FOLDER, exist_ok=True)
os.makedirs(CLEAN_FOLDER, exist_ok=True)
# ==========================================================
# CLEANED DATASET OUTPUTS
# ==========================================================

MUNICIPALITY_CLEANED = os.path.join(
    CLEAN_FOLDER,
    "municipality_cleaned.xlsx"
)

PROVINCIAL_CLEANED = os.path.join(
    CLEAN_FOLDER,
    "provincial_cleaned.xlsx"
)
# ==========================================================
# SNAPSHOT CONFIG — Option B safety: backup master BEFORE append
# ==========================================================
SNAPSHOT_FOLDER = os.path.join(BASE_DIR, "data", "uploads", "snapshots")
MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 2000
ALLOWED_YEARS_MIN = 2000
ALLOWED_YEARS_MAX = datetime.now().year + 1  # e.g. 2027
VALID_MONTHS = {
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december"
}

os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)


def create_snapshot(dataset_type: str) -> str:
    """
    Creates a timestamped snapshot of the current master file BEFORE append.
    Returns snapshot path or empty string if master does not exist.
    Safe to call even if file missing — returns "".
    """
    try:
        if dataset_type == "Provincial":
            master_path = os.path.join(MASTER_FOLDER, "provincial_raw.xlsx")
            prefix = "provincial_raw"
        else:
            master_path = os.path.join(MASTER_FOLDER, "municipality_raw.xlsx")
            prefix = "municipality_raw"

        if not os.path.exists(master_path):
            return ""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_name = f"{prefix}_{timestamp}.xlsx"
        snapshot_path = os.path.join(SNAPSHOT_FOLDER, snapshot_name)
        os.makedirs(SNAPSHOT_FOLDER, exist_ok=True)
        shutil.copy2(master_path, snapshot_path)

        # Keep only last 10 snapshots per type to avoid disk bloat
        try:
            snaps = sorted(
                [f for f in os.listdir(SNAPSHOT_FOLDER) if f.startswith(prefix)],
                reverse=True
            )
            for old in snaps[10:]:
                try:
                    os.remove(os.path.join(SNAPSHOT_FOLDER, old))
                except Exception:
                    pass
        except Exception:
            pass

        print(f"[Snapshot] Created: {snapshot_path}")
        return snapshot_path
    except Exception as e:
        print(f"[Snapshot] Failed: {e}")
        return ""


def validate_file_size(temp_path: str, max_bytes: int = MAX_FILE_SIZE_BYTES) -> None:
    """Raise ValueError if file exceeds max_bytes (default 5 MB)."""
    size = os.path.getsize(temp_path)
    if size > max_bytes:
        raise ValueError(
            f"File too large: {size / (1024*1024):.2f} MB exceeds limit of {max_bytes / (1024*1024):.0f} MB"
        )


def validate_row_limit(df: pd.DataFrame, max_rows: int = MAX_ROWS) -> None:
    """Raise ValueError if row count exceeds max_rows (default 2000)."""
    n = len(df)
    if n > max_rows:
        raise ValueError(
            f"Too many rows: {n} exceeds limit of {max_rows} rows per upload"
        )
    if n == 0:
        raise ValueError("File is empty — no data rows found.")


# ==========================================================
# SAVE TEMP FILE
# ==========================================================
def save_temp_file(uploaded_file):
    """
    Saves the uploaded file temporarily.
    Returns the temporary file path.
    """

    temp_path = os.path.join(TEMP_FOLDER, uploaded_file.name)

    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return temp_path


# ==========================================================
# VALIDATE TEMPLATE — strict (columns + Year/Month + empty checks)
# ==========================================================
def validate_template(df, dataset_type):
    """
    Strict validation:
      1. Required columns present
      2. Year: numeric, 2000..current_year+1, no NaN
      3. Month: valid month name (case-insensitive) or 1-12 if Month_Num present
      4. Province/Municipality: not empty / not all NaN
      5. Row limit & file size checked separately via validate_file_size/validate_row_limit
    """

    if dataset_type == "Provincial":
        required_columns = ["Province", "Year", "Month"]
    elif dataset_type == "Municipality":
        required_columns = ["Municipality", "Year", "Month"]
    else:
        raise ValueError("Invalid dataset type.")

    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # ---- Row-level checks ----
    # Empty check for location column
    loc_col = "Province" if dataset_type == "Provincial" else "Municipality"
    if df[loc_col].isna().all() or (df[loc_col].astype(str).str.strip() == "").all():
        raise ValueError(f"Column '{loc_col}' is empty — all rows missing location.")

    # ---- Year checks ----
    # Coerce to numeric; invalid -> NaN
    years = pd.to_numeric(df["Year"], errors="coerce")
    if years.isna().any():
        bad_idx = years[years.isna()].index.tolist()[:5]
        raise ValueError(f"Column 'Year' has non-numeric/empty values at rows {bad_idx}. Must be integer year.")
    # Range check
    year_min, year_max = ALLOWED_YEARS_MIN, ALLOWED_YEARS_MAX
    if ((years < year_min) | (years > year_max)).any():
        bad = df.loc[(years < year_min) | (years > year_max), "Year"].unique().tolist()[:5]
        raise ValueError(f"Column 'Year' out of range [{year_min}-{year_max}]. Found: {bad}")
    # Non-integer (e.g. 2023.5)
    if not (years == years.astype(int)).all():
        raise ValueError("Column 'Year' must be integer (e.g. 2024, not 2024.5).")

    # ---- Month checks ----
    months_raw = df["Month"].astype(str).str.strip().str.lower()
    # Reject empty/nan months
    if months_raw.isin(["nan", "none", "nat", ""]).any():
        bad_idx = months_raw[months_raw.isin(["nan", "none", "nat", ""])].index.tolist()[:5]
        raise ValueError(f"Column 'Month' has empty values at rows {bad_idx}.")
    invalid_months = months_raw[~months_raw.isin(VALID_MONTHS)].unique().tolist()
    if invalid_months:
        raise ValueError(
            f"Column 'Month' has invalid values: {invalid_months[:5]}. "
            f"Must be full month name (January-December)."
        )

    # Optional: Month_Num cross-check if present
    if "Month_Num" in df.columns:
        month_nums = pd.to_numeric(df["Month_Num"], errors="coerce")
        if month_nums.isna().any():
            raise ValueError("Column 'Month_Num' has non-numeric/empty values.")
        if ((month_nums < 1) | (month_nums > 12)).any():
            raise ValueError("Column 'Month_Num' must be 1-12.")
        # Cross-check Month vs Month_Num consistency
        month_to_num = {m: i+1 for i, m in enumerate(
            ["january","february","march","april","may","june","july","august","september","october","november","december"]
        )}
        expected_nums = months_raw.map(month_to_num)
        mismatched = (expected_nums != month_nums.astype(int)).sum()
        if mismatched > 0:
            raise ValueError(
                f"Column 'Month' and 'Month_Num' mismatch in {mismatched} row(s). "
                f"e.g. Month='January' must have Month_Num=1."
            )

    return True


# ==========================================================
# ARCHIVE ORIGINAL UPLOAD
# ==========================================================
def archive_upload(temp_path, dataset_type):
    """
    Saves a permanent copy of the uploaded file.
    """

    folder = os.path.join(UPLOAD_FOLDER, dataset_type)

    os.makedirs(folder, exist_ok=True)

    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".xlsx"

    archive_path = os.path.join(folder, filename)

    shutil.copy(temp_path, archive_path)

    return archive_path


# ==========================================================
# APPEND TO RAW MASTER (PRESERVES ALL SHEETS) — with SNAPSHOT
# ==========================================================
def append_to_raw_master(temp_path, dataset_type):
    """
    Appends uploaded rows to the raw master dataset.
    For Provincial type, preserves ALL sheets (3 sheets expected).

    SAFETY: Creates a timestamped snapshot of the current master BEFORE
    any write, so evaluator uploads can be rolled back instantly.
    """
    # --- SNAPSHOT BEFORE ANY WRITE (Option B safety) ---
    snapshot_path = create_snapshot(dataset_type)
    # snapshot_path may be "" if master didn't exist yet (first upload) — OK

    if dataset_type == "Provincial":
        master_path = os.path.join(MASTER_FOLDER, "provincial_raw.xlsx")
        # Read ALL sheets from uploaded file (preserves multi-sheet structure)
        uploaded_sheets = pd.read_excel(temp_path, sheet_name=None, engine='openpyxl')
        master_sheets = read_uploaded_file_all_sheets(master_path)

        with pd.ExcelWriter(master_path, engine="openpyxl") as writer:
            for sheet_name, uploaded_df in uploaded_sheets.items():
                master_df = master_sheets.get(sheet_name, pd.DataFrame())
                updated_df = pd.concat([master_df, uploaded_df], ignore_index=True)
                updated_df.to_excel(writer, sheet_name=sheet_name, index=False)

            # Copy over any sheets in master that weren't in the upload
            for sheet_name, master_df in master_sheets.items():
                if sheet_name not in uploaded_sheets:
                    master_df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        master_path = os.path.join(MASTER_FOLDER, "municipality_raw.xlsx")
        uploaded_df = pd.read_excel(temp_path, engine='openpyxl')
        master_df = read_uploaded_file(master_path)
        updated_df = pd.concat([master_df, uploaded_df], ignore_index=True)
        updated_df.to_excel(master_path, index=False)

    if snapshot_path:
        print(f"[append_to_raw_master] Snapshot saved -> {snapshot_path}")
    return master_path


def read_uploaded_file_all_sheets(file_path):
    """
    Reads all sheets from an Excel file.
    Returns a dict of sheet_name -> DataFrame.
    Returns empty dict if file does not exist.
    """
    if not os.path.exists(file_path):
        return {}
    return pd.read_excel(file_path, sheet_name=None, engine='openpyxl')


# ==========================================================
# BACKUP & RESTORE
# ==========================================================
BACKUP_FOLDER = os.path.join(BASE_DIR, "data", "backup_originals")
DASHBOARD_READY_FOLDER = os.path.join(BASE_DIR, "data", "Dashboard_Ready")
MODELS_FOLDER = os.path.join(BASE_DIR, "data", "models")

def create_originals_backup():
    """
    Creates a backup of the original master files if not yet backed up.
    """
    os.makedirs(BACKUP_FOLDER, exist_ok=True)

    files_to_backup = [
        ("provincial_raw.xlsx", MASTER_FOLDER),
        ("municipality_raw.xlsx", MASTER_FOLDER),
        ("provincial_cleaned.xlsx", MASTER_FOLDER),
        ("municipality_cleaned.xlsx", MASTER_FOLDER),
    ]

    backed_up = 0
    for filename, source_dir in files_to_backup:
        src = os.path.join(source_dir, filename)
        dst = os.path.join(BACKUP_FOLDER, filename)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            backed_up += 1

    return backed_up


def restore_original_data():
    """
    Restores the original master files from backup and cleans
    up all generated files (cleaned, forecasts, models).
    Returns a list of actions performed.
    """
    actions = []

    # 1. Restore master files from backup
    files_to_restore = [
        "provincial_raw.xlsx",
        "municipality_raw.xlsx",
        "provincial_cleaned.xlsx",
        "municipality_cleaned.xlsx",
    ]

    for filename in files_to_restore:
        src = os.path.join(BACKUP_FOLDER, filename)
        dst = os.path.join(MASTER_FOLDER, filename)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            actions.append(f"Restored {filename}")

    # 2. Delete cleaned files (they will be regenerated on next load)
    for filename in ["provincial_cleaned.xlsx", "municipality_cleaned.xlsx"]:
        path = os.path.join(CLEAN_FOLDER, filename)
        if os.path.exists(path):
            os.remove(path)
            actions.append(f"Removed cleaned/{filename}")

    # 3. Delete Dashboard_Ready files (forecasts, metrics)
    if os.path.exists(DASHBOARD_READY_FOLDER):
        for f in os.listdir(DASHBOARD_READY_FOLDER):
            file_path = os.path.join(DASHBOARD_READY_FOLDER, f)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    actions.append(f"Removed Dashboard_Ready/{f}")
            except Exception:
                pass

    # 4. Delete model files
    if os.path.exists(MODELS_FOLDER):
        for f in os.listdir(MODELS_FOLDER):
            file_path = os.path.join(MODELS_FOLDER, f)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    actions.append(f"Removed models/{f}")
            except Exception:
                pass

    if not actions:
        actions.append("No backup found. Please upload data first.")

    return actions


# ==========================================================
# READ UPLOADED FILE
# ==========================================================
def read_uploaded_file(file_path):
    """
    Reads either Excel or CSV.
    Returns an empty DataFrame if the file does not exist (first-time upload).
    """

    if not os.path.exists(file_path):
        return pd.DataFrame()

    extension = Path(file_path).suffix.lower()

    if extension == ".xlsx":
        return pd.read_excel(file_path, engine='openpyxl')

    elif extension == ".csv":
        return pd.read_csv(file_path)

    else:
        raise ValueError("Unsupported file type.")
