# Face Age Checker

<img width="1915" height="1026" alt="Face Age Checker landing page" src="https://github.com/user-attachments/assets/3055ad08-dbd6-4473-aab0-db4002c1c1ef" />

### Identifying minors: 

<img width="709" height="576" alt="image" src="https://github.com/user-attachments/assets/74dad4f2-7840-48bc-b97c-3da209099e64" />


An open-source facial age verification API built with FastAPI — designed to help digital platforms comply with Brazil's **Estatuto da Criança e do Adolescente (ECA, Law nº 8.069/90)**, which restricts minors from accessing certain content and services.



---

## How it works

1. The client captures a photo and encodes it as **base64**
2. Sends a `POST /verify-age` request with the JSON payload
3. OpenCV's Haar cascade auto-corrects the image orientation (handles upside-down or rotated photos)
4. The face is detected and cropped, then fed into a **Vision Transformer (ViT)** age classifier
5. The API returns the estimated age and an `is_adult` flag the application can act on

```
is_adult: true  → grant access
is_adult: false → deny access
```

No images are stored. Processing happens entirely in memory.

---

## Age estimation model

The project uses [`nateraw/vit-age-classifier`](https://huggingface.co/nateraw/vit-age-classifier) — a Vision Transformer fine-tuned on the **Adience dataset**, which covers all age ranges from infants to the elderly.

The model outputs probability scores for 9 age buckets (`0-2`, `3-9`, `10-19`, …, `70+`). A probability-weighted average of the bucket midpoints produces a continuous age estimate.

| Age | Old model (DeepFace) | Current model (ViT) |
|-----|---------------------|---------------------|
| 7 years old | ~25 years (wrong) | ~6–8 years (accurate) |
| 15 years old | ~27 years (wrong) | ~14–16 years (accurate) |
| 30 years old | ~32 years (ok) | ~28–32 years (accurate) |

> Previous versions used DeepFace + TensorFlow, which has a documented positive bias of ±7–15 years for children. The ViT model eliminates this issue.

---

## API Reference

### `POST /verify-age`

**Request**
```json
{
  "image_base64": "iVBORw0KGgo..."
}
```

**Response `200 OK`**
```json
{
  "estimated_age": 28,
  "is_adult": true,
  "confidence": 1.0
}
```

| Field | Description |
|-------|-------------|
| `estimated_age` | Continuous age estimate (probability-weighted average of ViT buckets) |
| `is_adult` | `true` if `estimated_age ≥ 18` (ECA legal threshold) |
| `confidence` | Always `1.0` — placeholder for future per-face detector confidence |

**Error responses**

| Status | Detail |
|--------|--------|
| `400`  | Invalid or corrupted image |
| `404`  | No face detected in the image |
| `422`  | Face detected but image quality too low for reliable estimation |
| `500`  | Internal processing error |

---

## Self-hosted setup with `uv`

The project uses [uv](https://github.com/astral-sh/uv) inline script metadata (`# /// script`) so you can run it with **zero manual dependency management** and no `requirements.txt`.

### Prerequisites

- Python ≥ 3.11
- `uv` installed

```bash
pip install uv
```

### Run

```bash
# Clone the repository
git clone https://github.com/your-username/face-age-checker
cd face-age-checker

# uv reads the # /// script block, creates an isolated venv and installs everything
uv run main.py
```

The server starts at `http://localhost:8000`.

### Dependencies (managed by uv)

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `torch` | PyTorch — inference backend for the ViT model |
| `transformers` | HuggingFace — loads `nateraw/vit-age-classifier` |
| `Pillow` | Image conversion for the ViT preprocessor |
| `opencv-python-headless` | Image decoding + Haar cascade face detection |
| `pydantic` | Request validation |

> **First run:** `uv` installs PyTorch (~180 MB) and the model weights are downloaded from HuggingFace (~350 MB) on the first `/verify-age` call. Subsequent runs are instant — both are cached locally.
>
> All model imports are **lazy** (inside the route handler), so the server starts in under a second.

---

## Test with curl

```bash
curl -X POST http://localhost:8000/verify-age \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "<your_base64_image>"}'
```

Interactive Swagger docs: `http://localhost:8000/docs`

---

## Local network access (mobile testing)

The server binds to `0.0.0.0` by default, so it is reachable from any device on the same network.

1. Find your machine's local IP (e.g. `192.168.1.105`)
2. Open a firewall rule for port 8000 — run PowerShell **as Administrator**:

```powershell
New-NetFirewallRule -DisplayName "Face Age Checker dev (8000)" `
  -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

3. Access from your phone: `http://192.168.1.105:8000`

> **Camera on mobile requires HTTPS.** Browsers block `getUserMedia` on non-localhost HTTP origins. Use [ngrok](https://ngrok.com) for a quick HTTPS tunnel:
> ```bash
> ngrok http 8000
> ```

---

## Playground

The landing page at `/` includes an interactive **Playground** — a four-step wizard that lets you test the API directly in the browser using your webcam:

| Step | Description |
|------|-------------|
| Introduction | Overview of the flow |
| Camera | Live webcam capture via the browser's native `getUserMedia` API |
| Confirm | Review the photo before sending |
| Result | Estimated age, adult status, and raw API response |

---

## Image orientation

The API automatically corrects image orientation before analysis. It tests four rotations (0°, 90°, 180°, 270°) using the OpenCV Haar cascade and picks the one where a face is detected. Upside-down or sideways photos are handled transparently — if no valid face can be found in any orientation, the request is rejected with `404`.

---

## Roadmap

- **JavaScript / TypeScript SDK** — a typed, Promise-based wrapper that abstracts the camera, base64 conversion, and API call (`npm install face-age-checker`)
- **`<script>` embed** — a single drop-in script tag that renders a verification widget on any page via a custom HTML element, with zero build step required

---

## Privacy

- No images are stored at any point
- Processing is entirely in-memory: the photo comes in, the result goes out, pixels are discarded
- No database, no image logs, no third-party services

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| API | [FastAPI](https://fastapi.tiangolo.com) |
| Age estimation | [ViT](https://huggingface.co/nateraw/vit-age-classifier) via HuggingFace Transformers |
| Inference backend | PyTorch (CPU) |
| Face detection | OpenCV Haar cascade |
| Frontend | React 18 (CDN) + Tailwind CSS (Play CDN) |
| Icons | Lucide-style inline SVG |
| Package / runtime | [uv](https://github.com/astral-sh/uv) |

---

## Project structure

```
face-age-checker/
├── main.py       # FastAPI app + uv inline script metadata
└── index.html    # Landing page + Playground (React + Tailwind)
```

---

Made by [Mateus Schverz (linkedin)](https://www.linkedin.com/in/mateus-schverz/)
