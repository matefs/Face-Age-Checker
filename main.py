import os

os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# /// script
# dependencies = [
#   "fastapi",
#   "uvicorn",
#   "pydantic",
#   "opencv-python-headless",
#   "deepface",
#   "tf-keras",
#   "tensorflow",
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


@app.get("/", response_class=HTMLResponse)
async def landing():
    return (HERE / "index.html").read_text(encoding="utf-8")


class ImagePayload(BaseModel):
    image_base64: str


def decode_image(b64: str):
    try:
        if "," in b64:
            b64 = b64.split(",")[1]
        data = base64.b64decode(b64)
        arr = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


@app.post("/verify-age")
async def verify_age(payload: ImagePayload):
    # DeepFace/TensorFlow são importados só aqui para o servidor iniciar rápido
    from deepface import DeepFace

    image = decode_image(payload.image_base64)
    if image is None:
        raise HTTPException(status_code=400, detail="Imagem inválida ou corrompida")

    try:
        results = DeepFace.analyze(
            img_path=image,
            actions=["age"],
            enforce_detection=True,
            detector_backend="opencv",
        )
        estimated_age = results[0]["age"]
        return {
            "estimated_age": estimated_age,
            "is_adult": estimated_age >= 18,
            "confidence": 1.0,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Nenhum rosto detectado na imagem")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
