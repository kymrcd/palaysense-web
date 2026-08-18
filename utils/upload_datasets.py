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
# VALIDATE TEMPLATE
# ==========================================================
def validate_template(df, dataset_type):
    """
    Checks if the uploaded dataset has the required columns.
    """

    if dataset_type == "Provincial":

        required_columns = [
            "Province",
            "Year",
            "Month"
        ]

    elif dataset_type == "Municipality":

        required_columns = [
            "Municipality",
            "Year",
            "Month"
        ]

    else:
        raise ValueError("Invalid dataset type.")

    missing = [
        col for col in required_columns
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required columns: {missing}"
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
# APPEND TO RAW MASTER (PRESERVES ALL SHEETS)
# ==========================================================
def append_to_raw_master(temp_path, dataset_type):
    """
    Appends uploaded rows to the raw master dataset.
    For Provincial type, preserves ALL sheets (3 sheets expected).
    """

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
