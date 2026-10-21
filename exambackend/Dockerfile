FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# OpenCV and the model runtimes need these shared libraries on slim images.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libegl1 libgles2 libgl1 libglib2.0-0 libgomp1 tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# The Azure VM has no GPU. Install CPU-only PyTorch before Ultralytics so pip
# does not pull multi-gigabyte CUDA wheels into the image.
RUN pip install torch==2.13.0 torchvision==0.28.0 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt
# Fail the build early if native proctoring packages cannot load on the VM CPU.
RUN python -c "import cv2, mediapipe, tensorflow, torch; from mediapipe.tasks import python"

COPY . .

EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "exambackend.asgi:application"]
