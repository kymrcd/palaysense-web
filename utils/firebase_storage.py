"""
Firebase Storage Module
=======================
Provides helper functions for uploading, downloading, and managing
Excel files in Firebase Cloud Storage.

Uses the existing Firebase Admin app from firebase_config.py.
No authentication logic is modified.

Cloud Path Convention:
    raw/provincial/{filename}.xlsx
    raw/municipality/{filename}.xlsx
    cleaned/provincial_cleaned.xlsx
    cleaned/municipality_cleaned.xlsx
    archives/{timestamp}_{filename}.xlsx
"""

import os
import streamlit as st
from datetime import datetime

# Reuse the Firebase app from firebase_config
from utils.firebase_config import get_firebase_app

# =============================================================
# CONSTANTS
# =============================================================

# Cloud paths for permanent storage
CLOUD_RAW_PROVINCIAL_DIR = "raw/provincial"
CLOUD_RAW_MUNICIPALITY_DIR = "raw/municipality"
CLOUD_CLEANED_PROVINCIAL = "cleaned/provincial_cleaned.xlsx"
CLOUD_CLEANED_MUNICIPALITY = "cleaned/municipality_cleaned.xlsx"
CLOUD_ARCHIVE_DIR = "archives"

# Temporary local paths (only temporary files stored locally)
TEMP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "temp"
)

# =============================================================
# LAZY BUCKET INITIALIZATION
# =============================================================
_bucket = None


def get_bucket():
    """
    Get the Firebase Storage bucket.

    The bucket name is read from the service account JSON or
    falls back to FIREBASE_STORAGE_BUCKET env var.

    Returns:
        google.cloud.storage.bucket.Bucket or None on failure
    """
    global _bucket
    if _bucket is not None:
        return _bucket

    app = get_firebase_app()
    if app is None:
        print("[Firebase Storage] Firebase Admin not initialized.")
        return None

    try:
        from firebase_admin import storage
        _bucket = storage.bucket(app=app)
        print(f"[Firebase Storage] Bucket ready: {_bucket.name}")
        return _bucket
    except Exception as e:
        print(f"[Firebase Storage] Failed to get bucket: {e}")
        return None


# =============================================================
# CORE STORAGE OPERATIONS
# =============================================================

def upload_file(local_path: str, cloud_path: str) -> bool:
    """
    Upload a local file to Firebase Storage.

    Args:
        local_path: Absolute path to local file
        cloud_path: Destination path in storage bucket

    Returns:
        True on success, False on failure
    """
    bucket = get_bucket()
    if bucket is None:
        print("[Firebase Storage] Bucket unavailable. Cannot upload.")
        return False

    if not os.path.exists(local_path):
        print(f"[Firebase Storage] Local file not found: {local_path}")
        return False

    try:
        blob = bucket.blob(cloud_path)
        blob.upload_from_filename(local_path)
        print(f"[Firebase Storage] Uploaded: {local_path} -> {cloud_path}")
        return True
    except Exception as e:
        print(f"[Firebase Storage] Upload error: {e}")
        return False


def download_file(cloud_path: str, local_path: str) -> bool:
    """
    Download a file from Firebase Storage to a local path.

    Args:
        cloud_path: Path in storage bucket
        local_path: Absolute destination path

    Returns:
        True on success, False on failure
    """
    bucket = get_bucket()
    if bucket is None:
        print("[Firebase Storage] Bucket unavailable. Cannot download.")
        return False

    try:
        blob = bucket.blob(cloud_path)
        if not blob.exists():
            print(f"[Firebase Storage] Cloud file not found: {cloud_path}")
            return False

        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)
        print(f"[Firebase Storage] Downloaded: {cloud_path} -> {local_path}")
        return True
    except Exception as e:
        print(f"[Firebase Storage] Download error: {e}")
        return False


def delete_file(cloud_path: str) -> bool:
    """
    Delete a file from Firebase Storage.

    Args:
        cloud_path: Path in storage bucket

    Returns:
        True on success, False on failure
    """
    bucket = get_bucket()
    if bucket is None:
        return False

    try:
        blob = bucket.blob(cloud_path)
        if blob.exists():
            blob.delete()
            print(f"[Firebase Storage] Deleted: {cloud_path}")
        return True
    except Exception as e:
        print(f"[Firebase Storage] Delete error: {e}")
        return False


def file_exists(cloud_path: str) -> bool:
    """
    Check if a file exists in Firebase Storage.

    Args:
        cloud_path: Path in storage bucket

    Returns:
        True if file exists, False otherwise
    """
    bucket = get_bucket()
    if bucket is None:
        return False

    try:
        blob = bucket.blob(cloud_path)
        return blob.exists()
    except Exception as e:
        print(f"[Firebase Storage] Existence check error: {e}")
        return False


def list_files(prefix: str = "") -> list:
    """
    List files in Firebase Storage under a given prefix.

    Args:
        prefix: Optional path prefix to filter (e.g., 'cleaned/', 'raw/')

    Returns:
        List of blob names (strings)
    """
    bucket = get_bucket()
    if bucket is None:
        return []

    try:
        blobs = list(bucket.list_blobs(prefix=prefix))
        return [b.name for b in blobs]
    except Exception as e:
        print(f"[Firebase Storage] List error: {e}")
        return []


def get_download_url(cloud_path: str, expiration_hours: int = 1) -> str:
    """
    Generate a signed download URL for a file in Firebase Storage.

    Args:
        cloud_path: Path in storage bucket
        expiration_hours: Hours until URL expires

    Returns:
        Signed URL string, or empty string on failure
    """
    bucket = get_bucket()
    if bucket is None:
        return ""

    try:
        from datetime import timedelta
        blob = bucket.blob(cloud_path)
        if not blob.exists():
            return ""
        url = blob.generate_signed_url(
            expiration=timedelta(hours=expiration_hours),
            method='GET'
        )
        return url
    except Exception as e:
        print(f"[Firebase Storage] Signed URL error: {e}")
        return ""


# =============================================================
# HIGH-LEVEL HELPERS
# =============================================================

def upload_raw_file(local_path: str, dataset_type: str) -> str:
    """
    Upload raw uploaded file to Firebase Storage with timestamp.

    Args:
        local_path: Local temp file path
        dataset_type: 'Provincial' or 'Municipality'

    Returns:
        Cloud path of uploaded file, or empty string on failure
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.basename(local_path)

    if dataset_type == "Provincial":
        cloud_dir = CLOUD_RAW_PROVINCIAL_DIR
    else:
        cloud_dir = CLOUD_RAW_MUNICIPALITY_DIR

    cloud_path = f"{cloud_dir}/{timestamp}_{filename}"

    if upload_file(local_path, cloud_path):
        return cloud_path
    return ""


def download_cleaned_file(dataset_type: str, local_dest: str = None) -> str:
    """
    Download the latest cleaned Excel file from Firebase Storage.

    Args:
        dataset_type: 'Provincial' or 'Municipality'
        local_dest: Optional local destination path (auto-generated if None)

    Returns:
        Local path to downloaded file, or empty string on failure
    """
    cloud_path = (
        CLOUD_CLEANED_PROVINCIAL
        if dataset_type == "Provincial"
        else CLOUD_CLEANED_MUNICIPALITY
    )

    if local_dest is None:
        os.makedirs(TEMP_DIR, exist_ok=True)
        suffix = "provincial" if dataset_type == "Provincial" else "municipality"
        local_dest = os.path.join(TEMP_DIR, f"cleaned_{suffix}.xlsx")

    if download_file(cloud_path, local_dest):
        return local_dest
    return ""


def upload_cleaned_file(local_path: str, dataset_type: str) -> bool:
    """
    Upload cleaned file to Firebase Storage (overwrites previous).

    Args:
        local_path: Local cleaned file path
        dataset_type: 'Provincial' or 'Municipality'

    Returns:
        True on success
    """
    cloud_path = (
        CLOUD_CLEANED_PROVINCIAL
        if dataset_type == "Provincial"
        else CLOUD_CLEANED_MUNICIPALITY
    )
    return upload_file(local_path, cloud_path)


def cleanup_temp_file(local_path: str):
    """Remove a temporary local file."""
    try:
        if local_path and os.path.exists(local_path):
            os.remove(local_path)
            print(f"[Firebase Storage] Cleaned up temp: {local_path}")
    except Exception as e:
        print(f"[Firebase Storage] Cleanup error: {e}")


def ensure_cleaned_files_synced():
    """
    Ensure local cleaned files exist by downloading from Firebase Storage.
    Called by the dashboard before reading cleaned Excel files.

    Returns:
        (provincial_path, municipality_path) - paths to local cleaned files,
        or empty strings if not available.
    """
    os.makedirs(TEMP_DIR, exist_ok=True)

    prov_local = os.path.join(TEMP_DIR, "provincial_cleaned.xlsx")
    muni_local = os.path.join(TEMP_DIR, "municipality_cleaned.xlsx")

    prov_ok = download_file(CLOUD_CLEANED_PROVINCIAL, prov_local)
    muni_ok = download_file(CLOUD_CLEANED_MUNICIPALITY, muni_local)

    prov_path = prov_local if prov_ok else ""
    muni_path = muni_local if muni_ok else ""

    return prov_path, muni_path
