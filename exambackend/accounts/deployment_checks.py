import importlib.util
import os
from pathlib import Path

from django.conf import settings
from django.core.checks import Error, Tags, register


@register(Tags.security, deploy=True)
def check_production_assets(app_configs, **kwargs):
    """Fail deployment checks before missing private model files affect exams."""
    if settings.DEBUG:
        return []

    errors = []
    face_dir = Path(os.getenv('FACE_MODELS_DIR') or settings.BASE_DIR / 'models')
    missing_face_models = [
        filename for filename in ('yunet.onnx', 'sface.onnx')
        if not (face_dir / filename).is_file()
    ]
    if missing_face_models:
        errors.append(Error(
            f'Missing face models in FACE_MODELS_DIR: {", ".join(missing_face_models)}.',
            id='accounts.E001',
        ))

    from accounts.gaze_service import resolve_gaze_assets_dir

    gaze_dir = Path(resolve_gaze_assets_dir())
    if not (gaze_dir / 'class_names.json').is_file() or not any(
        (gaze_dir / name).is_file()
        for name in ('EfficientNetB0_gaze_float32.tflite', 'gaze_model_float32.tflite')
    ) or not (gaze_dir / 'face_landmarker.task').is_file():
        errors.append(Error('Missing gaze model assets in GAZE_ASSETS_DIR.', id='accounts.E002'))

    gadget_path = Path(
        os.getenv('GADGET_MODEL_PATH') or settings.BASE_DIR / 'models' / 'yolo11n.pt'
    )
    if not gadget_path.is_file():
        errors.append(Error('Missing gadget model at GADGET_MODEL_PATH.', id='accounts.E003'))

    if not settings.USE_LOCAL_MEDIA and any(
        importlib.util.find_spec(package) is None for package in ('storages', 'boto3')
    ):
        errors.append(Error(
            'Install django-storages[s3] for production media storage.',
            id='accounts.E004',
        ))
    return errors
