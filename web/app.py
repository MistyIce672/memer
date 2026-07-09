"""
FastAPI backend for the gesture-to-meme website.

Run it from inside this folder so the flat imports resolve:

    cd web
    uvicorn app:app --reload

Then open http://localhost:8000.

The browser does all the camera + MediaPipe work; this server only stores the
shared library (memes + gestures) in MongoDB, serves uploaded files, and hands
out the static frontend.
"""

import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import db
import seed

ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"

# Upload limits / accepted types.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_PREFIXES = ("image/", "video/")
EXT_BY_TYPE = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp",
    "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
}

app = FastAPI(title="Gesture Meme")


@app.on_event("startup")
def _startup():
    try:
        seed.seed()
    except Exception as exc:  # pragma: no cover - surfaced at request time too
        # Don't crash the server if Mongo is unreachable at boot; the API
        # endpoints will report the failure clearly when called.
        print(f"[startup] seeding skipped: {exc}")


# --- Gestures API --------------------------------------------------------

class GestureIn(BaseModel):
    name: str
    mean: list[float]
    threshold: float
    blend_names: list[str]
    priority: int = 100


@app.get("/api/gestures")
def api_list_gestures():
    return db.list_gestures()


@app.post("/api/gestures", status_code=201)
def api_create_gesture(body: GestureIn):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "Gesture name is required.")
    if not body.mean or not body.blend_names:
        raise HTTPException(400, "Gesture template is empty.")
    template = {
        "mean": body.mean,
        "threshold": body.threshold,
        "blend_names": body.blend_names,
        "priority": body.priority,
    }
    try:
        return db.create_recorded_gesture(name, template, body.priority)
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            raise HTTPException(409, f"A gesture named '{name}' already exists.")
        raise


@app.delete("/api/gestures/{gesture_id}", status_code=204)
def api_delete_gesture(gesture_id: str):
    if not db.delete_gesture(gesture_id):
        raise HTTPException(404, "Recorded gesture not found (built-ins can't be deleted).")


# --- Memes API -----------------------------------------------------------

class MemePatch(BaseModel):
    name: str | None = None
    # Sentinel "__keep__" means "leave unchanged"; null clears the pairing.
    gesture_id: str | None = "__keep__"


@app.get("/api/memes")
def api_list_memes():
    return db.list_memes()


@app.post("/api/memes", status_code=201)
async def api_create_meme(
    file: UploadFile = File(...),
    name: str = Form(...),
    gesture_id: str | None = Form(None),
):
    content_type = (file.content_type or "").lower()
    if not content_type.startswith(ALLOWED_PREFIXES):
        raise HTTPException(400, "Only image or video files are allowed.")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 25 MB).")
    if not data:
        raise HTTPException(400, "Empty file.")

    ext = EXT_BY_TYPE.get(content_type) or Path(file.filename or "").suffix.lower() or ".bin"
    filename = f"{uuid.uuid4().hex}{ext}"
    (db.MEDIA_DIR / filename).write_bytes(data)

    display = name.strip() or Path(file.filename or "meme").stem
    gid = gesture_id or None
    return db.create_meme(display, filename, content_type, gid)


@app.patch("/api/memes/{meme_id}")
def api_update_meme(meme_id: str, body: MemePatch):
    kwargs = {}
    if body.name is not None:
        kwargs["name"] = body.name.strip()
    if body.gesture_id != "__keep__":
        kwargs["gesture_id"] = body.gesture_id  # None unpairs
    meme = db.update_meme(meme_id, **kwargs)
    if meme is None:
        raise HTTPException(404, "Meme not found.")
    return meme


@app.delete("/api/memes/{meme_id}", status_code=204)
def api_delete_meme(meme_id: str):
    filename = db.delete_meme(meme_id)
    if filename is None:
        raise HTTPException(404, "Meme not found.")
    path = db.MEDIA_DIR / filename
    # Don't remove seeded files that other rows might reference; unique names
    # mean uploads are safe to delete.
    if path.exists() and not filename.startswith("seed_"):
        path.unlink()


# --- Pages + static ------------------------------------------------------

@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/play")
def play():
    return FileResponse(STATIC_DIR / "play.html")


# Uploaded meme files, then the JS/CSS assets. Ensure the upload dir exists
# before mounting (StaticFiles validates the path at construction time).
db.MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=db.MEDIA_DIR), name="media")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
