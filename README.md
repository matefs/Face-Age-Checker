# Face Age Checker

<img width="1915" height="1026" alt="Face Age Checker landing page" src="https://github.com/user-attachments/assets/3055ad08-dbd6-4473-aab0-db4002c1c1ef" />

An open-source facial age verification API built with FastAPI and DeepFace — designed to help digital platforms comply with Brazil's **Estatuto da Criança e do Adolescente (ECA, Law nº 8.069/90)**, which restricts minors from accessing certain content and services.

---

## How it works

1. The client captures a photo and encodes it as **base64**
2. Sends a `POST /verify-age` request with the JSON payload
3. **DeepFace** detects the face and estimates the age via a pre-trained neural network
4. The API returns the estimated age and an `is_adult` flag the application can act on

```
is_adult: true  → grant access
is_adult: false → deny access
```

No images are stored. Processing happens entirely in memory.

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

**Error responses**

| Status | Detail |
|--------|--------|
| `400`  | Invalid or corrupted image |
| `404`  | No face detected in the image |
| `500`  | Internal processing error |

The `confidence` field is always `1.0` — DeepFace's age model is a regression network, not a softmax classifier.

---

## Self-hosted setup with `uv`

The project uses [uv](https://github.com/astral-sh/uv) inline script metadata (`# /// script`) so you can run it with **zero manual dependency management**.

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

# uv reads the dependencies from the # /// script block at the top of main.py
# and creates an isolated virtual environment automatically
uv run main.py
```

The server starts at `http://localhost:8000`.

### Dependencies (managed by uv)

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `deepface` | Facial analysis (age estimation) |
| `tensorflow` + `tf-keras` | Neural network backend for DeepFace |
| `opencv-python-headless` | Image decoding |
| `pydantic` | Request validation |

> On first run, DeepFace downloads its pre-trained models (~500 MB). Subsequent runs are instant. The TensorFlow import is **lazy** — it only loads when the first `/verify-age` request is made, so the server starts in under a second.

---

## Test with curl

```bash
curl -X POST http://localhost:8000/verify-age \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "<your_base64_image>"}'
```

Interactive Swagger docs are available at `http://localhost:8000/docs`.

---

## Local network access (mobile testing)

The server binds to `0.0.0.0` by default, so it is reachable from any device on the same network.

1. Find your machine's local IP (e.g. `192.168.1.105`)
2. Open a firewall rule for port 8000 (Windows — run as Administrator):

```powershell
New-NetFirewallRule -DisplayName "Face Age Checker dev (8000)" `
  -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
```

3. Access from your phone: `http://192.168.1.105:8000`

> **Camera on mobile requires HTTPS.** Browsers block `getUserMedia` on non-localhost origins over plain HTTP. Use [ngrok](https://ngrok.com) for a quick HTTPS tunnel:
> ```bash
> ngrok http 8000
> ```

---

## Playground

The landing page at `/` includes an interactive **Playground** — a four-step wizard that lets you test the API directly from the browser:

| Step | Description |
|------|-------------|
| Introduction | Overview of the flow |
| Camera | Live webcam capture via the browser's native `getUserMedia` API |
| Confirm | Review the photo before sending |
| Result | Estimated age, adult status, and raw API response |

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
| Face analysis | [DeepFace](https://github.com/serengil/deepface) |
| Neural network backend | TensorFlow / Keras |
| Image processing | OpenCV |
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
