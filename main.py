import os

# /// script
# dependencies = [
#   "fastapi",
#   "uvicorn",
#   "pydantic",
#   "opencv-python-headless",
#   "torch",
#   "transformers",
#   "Pillow",
# ]
# requires-python = ">=3.11"
# ///

import base64
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

app = FastAPI()
HERE = Path(__file__).parent

# Legal adult threshold under Brazil's ECA (Law 8.069/90)
ECA_ADULT_THRESHOLD = 18

# ViT model: nateraw/vit-age-classifier
# Trained on the Adience dataset — covers all age ranges including children.
# Outputs 9 probability classes; we compute a weighted average for a continuous estimate.
_AGE_BUCKETS = {
    "0-2":   1,
    "3-9":   6,
    "10-19": 14,
    "20-29": 24,
    "30-39": 34,
    "40-49": 44,
    "50-59": 54,
    "60-69": 64,
    "70+":   75,
}
_VIT_MODEL = "nateraw/vit-age-classifier"

_processor = None
_model     = None

# Haar cascade — fast face detection for orientation correction and cropping.
# Ships with opencv-python-headless, no extra download needed.
_haar = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)
_ROTATIONS = [
    None,
    cv2.ROTATE_180,
    cv2.ROTATE_90_CLOCKWISE,
    cv2.ROTATE_90_COUNTERCLOCKWISE,
]


# ── lazy model loader ──────────────────────────────────────────────────────────

def _get_model():
    global _processor, _model
    if _model is None:
        from transformers import ViTForImageClassification, ViTImageProcessor
        _processor = ViTImageProcessor.from_pretrained(_VIT_MODEL)
        _model = ViTForImageClassification.from_pretrained(_VIT_MODEL)
        _model.eval()
    return _processor, _model


# ── image helpers ──────────────────────────────────────────────────────────────

def decode_image(b64: str) -> np.ndarray | None:
    try:
        if "," in b64:
            b64 = b64.split(",")[1]
        data = base64.b64decode(b64)
        arr  = np.frombuffer(data, np.uint8)
        img  = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def _haar_count(img: np.ndarray) -> int:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = _haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    return len(faces)


def auto_orient(image: np.ndarray) -> np.ndarray:
    """
    Test 4 rotations with the Haar cascade (~5 ms, CPU-only).
    Returns the rotation where the most faces are found, fixing
    upside-down or sideways images before they reach the age model.
    """
    best_img, best_n = image, _haar_count(image)
    for rot in _ROTATIONS[1:]:
        candidate = cv2.rotate(image, rot)
        n = _haar_count(candidate)
        if n > best_n:
            best_n, best_img = n, candidate
    return best_img


def crop_face(image_bgr: np.ndarray) -> np.ndarray | None:
    """
    Detect the largest face with the Haar cascade, expand the bounding
    box by 20 % to include forehead/chin context, and return an RGB crop.
    Returns None if no face is detected.
    """
    gray  = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    faces = _haar.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    if len(faces) == 0:
        return None

    x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

    pad = int(max(w, h) * 0.20)
    x1  = max(0, x - pad)
    y1  = max(0, y - pad)
    x2  = min(image_bgr.shape[1], x + w + pad)
    y2  = min(image_bgr.shape[0], y + h + pad)

    crop = image_bgr[y1:y2, x1:x2]
    return cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)


# ── age estimation ─────────────────────────────────────────────────────────────

def estimate_age(face_rgb: np.ndarray) -> int:
    """
    Feed the face crop into the ViT classifier.
    Returns a continuous age estimate as the probability-weighted average
    of the 9 bucket midpoints.
    """
    import torch
    from PIL import Image

    processor, model = _get_model()

    inputs = processor(images=Image.fromarray(face_rgb), return_tensors="pt")
    with torch.no_grad():
        probs = torch.softmax(model(**inputs).logits, dim=1)[0]

    id2label = model.config.id2label
    weighted = sum(
        probs[i].item() * _AGE_BUCKETS.get(id2label[i], 35)
        for i in range(len(probs))
    )
    return max(0, int(round(weighted)))


# ── routes ─────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing():
    return (HERE / "index.html").read_text(encoding="utf-8")


class ImagePayload(BaseModel):
    image_base64: str


@app.post("/verify-age")
async def verify_age(payload: ImagePayload):
    image = decode_image(payload.image_base64)
    if image is None:
        raise HTTPException(status_code=400, detail="Invalid or corrupted image")

    oriented = auto_orient(image)
    face_rgb = crop_face(oriented)

    if face_rgb is None:
        raise HTTPException(status_code=404, detail="No face detected in the image")

    try:
        estimated_age = estimate_age(face_rgb)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Age estimation error: {str(e)}")

    return {
        "estimated_age": estimated_age,
        "is_adult":      estimated_age >= ECA_ADULT_THRESHOLD,
        "confidence":    1.0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
