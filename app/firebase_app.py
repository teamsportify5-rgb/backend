"""Initialize Firebase Admin once; used by push delivery and notification routes."""
import json
import os

import firebase_admin
from firebase_admin import credentials
from dotenv import load_dotenv

load_dotenv()

_initialized = False


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
