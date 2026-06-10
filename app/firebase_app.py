"""Initialize Firebase Admin once; used by push delivery and notification routes."""
import json
import os
from typing import Any, Dict

import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()

_initialized = False
_last_auth_error: str | None = None


def ensure_firebase_initialized() -> bool:
    """Return True if Firebase app is ready for messaging.send."""
    global _initialized
    if _initialized:
        return True
    try:
        firebase_admin.get_app()
        _initialized = True
        return True
    except ValueError:
        pass

    try:
        path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if path and os.path.exists(path):
            cred = credentials.Certificate(path)
            firebase_admin.initialize_app(cred)
            _initialized = True
            return True

        raw = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if raw:
            cred = credentials.Certificate(json.loads(raw))
            firebase_admin.initialize_app(cred)
            _initialized = True
            return True
    except Exception as e:
        print(f"Warning: Firebase Admin SDK initialization failed: {e}")

    return False


def firebase_status() -> Dict[str, Any]:
    """Report whether Firebase credentials are present and can obtain an access token."""
    global _last_auth_error
    configured = bool(os.getenv("FIREBASE_CREDENTIALS_JSON") or os.getenv("FIREBASE_CREDENTIALS_PATH"))
    if not ensure_firebase_initialized():
        return {
            "configured": configured,
            "ready": False,
            "error": "Firebase Admin SDK not initialized (missing or invalid credentials JSON)",
        }

    try:
        import google.auth.transport.requests
        from google.oauth2 import service_account

        info = None
        path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if path and os.path.exists(path):
            cred_obj = service_account.Credentials.from_service_account_file(
                path,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )
            project_id = cred_obj.project_id
        else:
            info = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON", "{}"))
            project_id = info.get("project_id")
            cred_obj = service_account.Credentials.from_service_account_info(
                info,
                scopes=["https://www.googleapis.com/auth/firebase.messaging"],
            )

        req = google.auth.transport.requests.Request()
        cred_obj.refresh(req)
        _last_auth_error = None
        return {
            "configured": True,
            "ready": True,
            "project_id": project_id,
            "error": None,
        }
    except Exception as e:
        _last_auth_error = str(e)
        return {
            "configured": configured,
            "ready": False,
            "project_id": json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON", "{}")).get("project_id")
            if os.getenv("FIREBASE_CREDENTIALS_JSON")
            else None,
            "error": str(e),
        }
