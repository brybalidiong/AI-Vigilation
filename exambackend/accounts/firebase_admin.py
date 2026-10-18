import json
import os
from pathlib import Path

import firebase_admin
from firebase_admin import credentials
from django.core.exceptions import ImproperlyConfigured


def _initialize_firebase():
    if firebase_admin._apps:
        return

    credentials_json = os.getenv('FIREBASE_CREDENTIALS_JSON')
    key_path = Path(
        os.getenv('FIREBASE_CREDENTIALS')
        or Path(__file__).resolve().parent.parent / 'serviceAccountKey.json'
    )
    try:
        if credentials_json:
            cred = credentials.Certificate(json.loads(credentials_json))
        elif key_path.is_file():
            cred = credentials.Certificate(str(key_path))
        else:
            raise ImproperlyConfigured(
                'Set FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_JSON for Firebase Admin.'
            )
    except (ValueError, OSError):
        raise ImproperlyConfigured('Firebase Admin credentials are invalid.') from None
    firebase_admin.initialize_app(cred)


_initialize_firebase()
