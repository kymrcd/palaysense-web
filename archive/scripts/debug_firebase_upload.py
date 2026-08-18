"""
Debug script to trace the Firebase Storage upload flow step-by-step.
Run this to see exactly where the upload is failing.
"""
import os
import sys
import traceback

# Ensure the project root is in sys.path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print("=" * 60)
print("FIREBASE STORAGE UPLOAD DIAGNOSTIC")
print("=" * 60)

# Step 1: Check if service account exists
print("\n[STEP 1] Checking service account key...")
sa_path = os.path.join(project_root, "serviceAccountKey.json")
print(f"  Path: {sa_path}")
print(f"  Exists: {os.path.exists(sa_path)}")
if os.path.exists(sa_path):
    print(f"  Size: {os.path.getsize(sa_path)} bytes")

# Step 2: Check .env variables
print("\n[STEP 2] Checking .env configuration...")
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv("FIREBASE_WEB_API_KEY", "")
storage_bucket = os.getenv("FIREBASE_STORAGE_BUCKET", "")
print(f"  FIREBASE_WEB_API_KEY: {'SET' if api_key else 'NOT SET'}")
print(f"  FIREBASE_STORAGE_BUCKET: '{storage_bucket}'")

# Step 3: Try to initialize Firebase Admin
print("\n[STEP 3] Initializing Firebase Admin...")
try:
    from utils.firebase_config import get_firebase_app
    app = get_firebase_app()
    if app is not None:
        print(f"  ✅ Firebase App initialized: {app.project_id}")
        print(f"  App name: {app.name}")
    else:
        print("  ❌ get_firebase_app() returned None!")
except Exception as e:
    print(f"  ❌ Error: {e}")
    traceback.print_exc()

# Step 4: Try to get storage bucket
print("\n[STEP 4] Getting Firebase Storage bucket...")
try:
    from firebase_admin import storage
    bucket = storage.bucket(app=app)
    print(f"  ✅ Bucket object created: {bucket.name}")
    print(f"  Bucket type: {type(bucket)}")
except Exception as e:
    print(f"  ❌ Error getting bucket: {e}")
    traceback.print_exc()

# Step 5: Try to upload a test file
print("\n[STEP 5] Testing upload via upload_file()...")
from utils.firebase_storage import upload_file
test_local = os.path.join(project_root, "serviceAccountKey.json")
test_cloud = "test/diagnostic_upload_test.txt"
print(f"  Local file: {test_local}")
print(f"  Cloud path: {test_cloud}")
print(f"  Local exists: {os.path.exists(test_local)}")

result = upload_file(test_local, test_cloud)
print(f"  ✅ Upload result: {result}") if result else print(f"  ❌ Upload result: {result}")

# Step 6: List all files in bucket
print("\n[STEP 6] Listing all files in bucket...")
try:
    from utils.firebase_storage import list_files
    all_files = list_files()
    print(f"  Found {len(all_files)} files:")
    for f in all_files:
        print(f"    - {f}")
except Exception as e:
    print(f"  ❌ Error listing: {e}")

# Step 7: Check upload_raw_file specifically
print("\n[STEP 7] Testing upload_raw_file() directly...")
from utils.firebase_storage import upload_raw_file
test_local2 = os.path.join(project_root, "serviceAccountKey.json")
cloud_path = upload_raw_file(test_local2, "Provincial")
if cloud_path:
    print(f"  ✅ upload_raw_file returned: {cloud_path}")
else:
    print(f"  ❌ upload_raw_file returned empty string!")

# Step 8: List files again to see if raw/ appeared
print("\n[STEP 8] Listing files after test upload...")
try:
    all_files = list_files()
    print(f"  Found {len(all_files)} files:")
    for f in all_files:
        print(f"    - {f}")
except Exception as e:
    print(f"  ❌ Error listing: {e}")

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
print("\nIf you see '❌' anywhere, that indicates the problem point.")
print("Share the full output with the developer for analysis.")
