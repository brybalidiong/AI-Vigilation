from pathlib import Path

import firebase_admin
from firebase_admin import credentials


def _initialize_firebase():
    if firebase_admin._apps:
        return

    base_dir = Path(__file__).resolve().parent.parent
    key_path = base_dir / 'serviceAccountKey.json'
    cred = credentials.Certificate(str(key_path))
    firebase_admin.initialize_app(cred)


_initialize_firebase()
