"""Copy gaze model assets from TrainModel/ into exambackend/gaze_tracker/assets/."""
from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC = REPO_ROOT / "TrainModel" / "gaze_tracker" / "assets"
DST = REPO_ROOT / "exambackend" / "gaze_tracker" / "assets"

FILES = (
    "EfficientNetB0_gaze_float32.tflite",
    "class_names.json",
    "face_landmarker.task",
    "gaze_model_float32.tflite",
)


def main():
    if not SRC.is_dir():
        raise SystemExit(f"Source not found: {SRC}")
    DST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src_file = SRC / name
        if not src_file.is_file():
            print(f"skip (missing): {src_file}")
            continue
        dst_file = DST / name
        shutil.copy2(src_file, dst_file)
        print(f"copied: {name}")
    print(f"Done. Assets in {DST}")


if __name__ == "__main__":
    main()
