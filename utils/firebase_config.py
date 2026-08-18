"""
Firebase Configuration & Data Sync Module
=========================================
Integrates Firebase Admin SDK for Firestore (cloud database), Firebase Auth REST API,
and Pyrebase client-side auth for user authentication in the PalaySense Streamlit app.

=== SETUP INSTRUCTIONS ===

1. Create a Firebase project at https://console.firebase.google.com/
2. Enable Authentication -> Sign-in method -> Email/Password
3. Create Firestore Database -> Start in test mode
4. Get Service Account Key: Project Settings -> Service Accounts -> Generate New Private Key
   Save as `serviceAccountKey.json` in project root
5. Get Web API Key: Project Settings -> General -> Web API Key
6. Configure .env file in project root:
   ```
   FIREBASE_WEB_API_KEY=your-web-api-key-here
   FIREBASE_STORAGE_BUCKET=palaysense.firebasestorage.app
   FIREBASE_PROJECT_ID=palaysense
   ```
"""

import os
import json
import streamlit as st
import pyrebase
import requests
from dotenv import load_dotenv

# =============================================================
# LOAD .ENV
# =============================================================
load_dotenv()


def get_secret(key: str, default: str = "") -> str:
    """Read from .env first, then Streamlit secrets if available."""
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets[key]
    except Exception:
        return default


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Web API Key: check Streamlit secrets first, then .env
FIREBASE_WEB_API_KEY = get_secret("FIREBASE_WEB_API_KEY")
FIREBASE_PROJECT_ID = get_secret("FIREBASE_PROJECT_ID", "palaysense")
FIREBASE_STORAGE_BUCKET_CONFIG = get_secret("FIREBASE_STORAGE_BUCKET", "")
FIREBASE_SENDER_ID = get_secret("FIREBASE_SENDER_ID", "")
FIREBASE_APP_ID = get_secret("FIREBASE_APP_ID", "")

SERVICE_ACCOUNT_KEY_PATH = os.path.join(PROJECT_ROOT, "serviceAccountKey.json")

# REST API URLs for direct Firebase Auth calls
FIREBASE_AUTH_BASE_URL = "https://identitytoolkit.googleapis.com/v1/accounts"
FIREBASE_SIGN_IN_URL = f"{FIREBASE_AUTH_BASE_URL}:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
FIREBASE_SIGN_UP_URL = f"{FIREBASE_AUTH_BASE_URL}:signUp?key={FIREBASE_WEB_API_KEY}"
FIREBASE_RESET_PASSWORD_URL = f"{FIREBASE_AUTH_BASE_URL}:sendOobCode?key={FIREBASE_WEB_API_KEY}"

# =============================================================
# PYRERASE AUTH (Client-side Firebase Authentication)
# =============================================================
_pyrebase_auth = None


def get_pyrebase_auth():
    """
    Returns a Pyrebase auth object for client-side Firebase Authentication.
    Uses the Web API Key and project config to initialize Pyrebase.
    """
    global _pyrebase_auth
    if _pyrebase_auth is not None:
        return _pyrebase_auth

    if not FIREBASE_WEB_API_KEY:
        print("[Pyrebase] No API Key configured.")
        return None

    try:
        fb_config = {
            "apiKey": FIREBASE_WEB_API_KEY,
            "authDomain": f"{FIREBASE_PROJECT_ID}.firebaseapp.com",
            "databaseURL": f"https://{FIREBASE_PROJECT_ID}.firebaseio.com",
            "projectId": FIREBASE_PROJECT_ID,
            "storageBucket": FIREBASE_STORAGE_BUCKET_CONFIG,
            "messagingSenderId": FIREBASE_SENDER_ID,
            "appId": FIREBASE_APP_ID,
        }
        firebase = pyrebase.initialize_app(fb_config)
        _pyrebase_auth = firebase.auth()
        print("[Pyrebase] Auth initialized successfully.")
        return _pyrebase_auth
    except Exception as e:
        print(f"[Pyrebase] Initialization error: {e}")
        return None


# =============================================================
# PYRERASE AUTH HELPER FUNCTIONS
# =============================================================

def pyrebase_sign_in(email: str, password: str) -> dict:
    """Sign in using Pyrebase (Firebase Auth REST under the hood)."""
    auth = get_pyrebase_auth()
    if auth is None:
        return {"error": "Firebase Authentication not available."}

    try:
        user = auth.sign_in_with_email_and_password(
            email.strip().lower(), password
        )
        uid = user.get("localId", "")
        email_addr = user.get("email", "")
        display_name = user.get("displayName", "")
        if uid:
            save_user_profile(uid, email_addr, display_name)

        return {
            "idToken": user.get("idToken"),
            "localId": uid,
            "email": email_addr,
            "displayName": display_name,
            "registered": user.get("registered", False),
        }
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_NOT_FOUND" in error_msg:
            return {"error": "No account found with this email."}
        if "INVALID_PASSWORD" in error_msg:
            return {"error": "Incorrect password."}
        if "USER_DISABLED" in error_msg:
            return {"error": "Account disabled."}
        if "INVALID_EMAIL" in error_msg:
            return {"error": "Invalid email format."}
        if "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
            return {"error": "Too many attempts. Try later."}
        return {"error": error_msg}


def pyrebase_sign_up(email: str, password: str, display_name: str = "") -> dict:
    """Create a new Firebase Auth user account using Pyrebase."""
    auth = get_pyrebase_auth()
    if auth is None:
        return {"error": "Firebase Authentication not available."}

    try:
        user = auth.create_user_with_email_and_password(
            email.strip().lower(), password
        )
        uid = user.get("localId", "")
        email_addr = user.get("email", "")
        name = display_name or email_addr.split("@")[0]

        if uid:
            if display_name:
                try:
                    auth.update_profile(user["idToken"], display_name=display_name)
                except Exception:
                    pass
            save_user_profile(uid, email_addr, name)

        return {
            "idToken": user.get("idToken"),
            "localId": uid,
            "email": email_addr,
            "displayName": name,
        }
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            return {"error": "An account with this email already exists."}
        if "WEAK_PASSWORD" in error_msg:
            return {"error": "Password must be at least 6 characters."}
        if "INVALID_EMAIL" in error_msg:
            return {"error": "Invalid email format."}
        if "TOO_MANY_ATTEMPTS_TRY_LATER" in error_msg:
            return {"error": "Too many attempts. Try later."}
        return {"error": error_msg}


def pyrebase_send_password_reset(email: str) -> dict:
    """Send password reset email using Pyrebase."""
    auth = get_pyrebase_auth()
    if auth is None:
        return {"error": "Firebase Authentication not available."}

    try:
        auth.send_password_reset_email(email.strip().lower())
        return {"success": True, "email": email}
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_NOT_FOUND" in error_msg:
            return {"error": "No account found with this email."}
        return {"error": error_msg}


# =============================================================
# LAZY FIREBASE ADMIN INIT
# =============================================================
_firebase_app = None
_firestore_db = None


def get_firebase_app():
    """Lazy initialize Firebase Admin SDK with storage bucket support."""
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError:
        st.error("Missing firebase-admin. Run: pip install firebase-admin")
        return None

    if firebase_admin._apps:
        _firebase_app = list(firebase_admin._apps.values())[0]
        return _firebase_app

    storage_bucket = get_secret("FIREBASE_STORAGE_BUCKET")

    if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        try:
            cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
            options = {}
            if storage_bucket:
                options["storageBucket"] = storage_bucket
            _firebase_app = firebase_admin.initialize_app(cred, options)
            print(f"[Firebase] Initialized from: {SERVICE_ACCOUNT_KEY_PATH}")
            return _firebase_app
        except Exception as e:
            print(f"[Firebase] Failed to load serviceAccountKey.json: {e}")

    env_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON") or st.secrets.get("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    if env_json:
        try:
            cred_dict = json.loads(env_json) if isinstance(env_json, str) else env_json
            cred = credentials.Certificate(cred_dict)
            options = {}
            if storage_bucket:
                options["storageBucket"] = storage_bucket
            _firebase_app = firebase_admin.initialize_app(cred, options)
            print("[Firebase] Initialized from env var")
            return _firebase_app
        except Exception as e:
            print(f"[Firebase] Failed from env var: {e}")

    print("[Firebase] No service account found. Firestore unavailable.")
    return None


def get_firestore_db():
    """Lazy Firestore client."""
    global _firestore_db
    if _firestore_db is not None:
        return _firestore_db

    app = get_firebase_app()
    if app is None:
        return None

    try:
        from firebase_admin import firestore
        _firestore_db = firestore.client(app)
        print("[Firestore] Client ready.")
    except Exception as e:
        print(f"[Firestore] Error: {e}")
        return None

    return _firestore_db


# =============================================================
# FIRESTORE DATA OPERATIONS
# =============================================================

def save_forecast_data(collection_name: str, data: dict, doc_id: str = None) -> bool:
    """Save forecast/data dictionary to Firestore."""
    db = get_firestore_db()
    if db is None:
        return False
    try:
        if doc_id:
            db.collection(collection_name).document(doc_id).set(data)
        else:
            db.collection(collection_name).add(data)
        return True
    except Exception as e:
        print(f"[Firestore] Save error: {e}")
        return False


def load_forecast_data(collection_name: str, limit: int = 100, order_by: str = None) -> list:
    """Load documents from a Firestore collection."""
    db = get_firestore_db()
    if db is None:
        return []
    try:
        if order_by:
            docs = db.collection(collection_name).order_by(order_by).limit(limit).stream()
        else:
            docs = db.collection(collection_name).limit(limit).stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            results.append(data)
        return results
    except Exception as e:
        print(f"[Firestore] Load error: {e}")
        return []


def save_user_profile(uid: str, email: str, display_name: str = "", role: str = "lgu") -> bool:
    """Save/update user profile in Firestore (collection: 'users')."""
    db = get_firestore_db()
    if db is None:
        return False
    try:
        from firebase_admin import firestore
        doc_ref = db.collection("users").document(uid)
        doc_ref.set({
            "email": email,
            "displayName": display_name,
            "role": role,
            "lastLogin": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        return True
    except Exception as e:
        print(f"[Firestore] Save user error: {e}")
        return False


def get_user_profile(uid: str) -> dict:
    """Retrieve user profile from Firestore by UID."""
    db = get_firestore_db()
    if db is None:
        return {}
    try:
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            return doc.to_dict()
        return {}
    except Exception as e:
        print(f"[Firestore] Get user error: {e}")
        return {}


# =============================================================
# AUTHENTICATION (Firebase Auth REST API) - Legacy
# =============================================================

def sign_in_with_email_password(email: str, password: str) -> dict:
    """Authenticate a user with email + password via Firebase Auth REST API."""
    if not FIREBASE_WEB_API_KEY:
        return {"error": "Firebase not configured. Contact admin."}

    payload = {
        "email": email.strip().lower(),
        "password": password,
        "returnSecureToken": True
    }

    try:
        resp = requests.post(FIREBASE_SIGN_IN_URL, json=payload)
        data = resp.json()

        if "error" in data:
            code = data["error"].get("message", "")
            msg_map = {
                "EMAIL_NOT_FOUND": "No account found with this email.",
                "INVALID_PASSWORD": "Incorrect password.",
                "USER_DISABLED": "Account disabled.",
                "INVALID_EMAIL": "Invalid email format.",
                "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Try later.",
            }
            return {"error": msg_map.get(code, code.replace("_", " ").title())}

        uid = data.get("localId")
        email_addr = data.get("email", "")
        display_name = data.get("displayName", "")
        if uid:
            save_user_profile(uid, email_addr, display_name)

        return {
            "idToken": data.get("idToken"),
            "localId": uid,
            "email": email_addr,
            "registered": data.get("registered", False),
            "displayName": display_name,
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}


def sign_up_with_email_password(email: str, password: str, display_name: str = "") -> dict:
    """Create a new Firebase Auth user account via REST API."""
    if not FIREBASE_WEB_API_KEY:
        return {"error": "Firebase not configured. Contact admin."}

    payload = {
        "email": email.strip().lower(),
        "password": password,
        "returnSecureToken": True
    }
    if display_name:
        payload["displayName"] = display_name

    try:
        resp = requests.post(FIREBASE_SIGN_UP_URL, json=payload)
        data = resp.json()

        if "error" in data:
            code = data["error"].get("message", "")
            msg_map = {
                "EMAIL_EXISTS": "An account with this email already exists.",
                "WEAK_PASSWORD": "Password must be at least 6 characters.",
                "INVALID_EMAIL": "Invalid email format.",
                "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Try later.",
            }
            return {"error": msg_map.get(code, code.replace("_", " ").title())}

        uid = data.get("localId")
        email_addr = data.get("email", "")
        name = data.get("displayName", display_name)
        if uid:
            save_user_profile(uid, email_addr, name)

        return {
            "idToken": data.get("idToken"),
            "localId": uid,
            "email": email_addr,
            "displayName": name,
        }

    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}


def send_password_reset_email(email: str) -> dict:
    """Send password reset email via Firebase."""
    if not FIREBASE_WEB_API_KEY:
        return {"error": "Firebase not configured."}

    payload = {
        "requestType": "PASSWORD_RESET",
        "email": email.strip().lower()
    }

    try:
        resp = requests.post(FIREBASE_RESET_PASSWORD_URL, json=payload)
        data = resp.json()
        if "error" in data:
            return {"error": data["error"].get("message", "")}
        return {"success": True, "email": email}
    except requests.exceptions.RequestException as e:
        return {"error": f"Network error: {str(e)}"}


def verify_id_token(id_token: str) -> dict:
    """Verify Firebase ID token using Admin SDK."""
    app = get_firebase_app()
    if app is None:
        return {"error": "Firebase not initialized."}

    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return dict(decoded)
    except Exception as e:
        return {"error": str(e)}


# =============================================================
# SESSION STATE HELPERS
# =============================================================

def is_authenticated() -> bool:
    """Check if user is authenticated in current Streamlit session."""
    return st.session_state.get("authenticated", False)


def get_current_user_email() -> str:
    """Get current user's email from session state."""
    return st.session_state.get("user_email", "")


def get_current_user_display_name() -> str:
    """Get current user's display name."""
    return st.session_state.get("user_display_name", "")


def get_current_user_id() -> str:
    """Get current user's Firebase UID."""
    return st.session_state.get("user_id", "")


def get_current_user_role() -> str:
    """Get current user's role from session state."""
    return st.session_state.get("user_role", "lgu")


def set_session_user(auth_result: dict):
    """Store authenticated user info in Streamlit session state."""
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = auth_result.get("localId", "")
    st.session_state["user_email"] = auth_result.get("email", "")
    st.session_state["user_display_name"] = auth_result.get("displayName", "")
    st.session_state["user_role"] = auth_result.get("role", "lgu")
    st.session_state["id_token"] = auth_result.get("idToken", "")


def clear_session_user():
    """Clear authentication from session state."""
    for key in ["authenticated", "user_id", "user_email", "user_display_name", "user_role", "id_token"]:
        st.session_state.pop(key, None)
