"""
First-run seeding.

Populates the shared library so it isn't empty on a fresh database:
  * The 6 built-in gestures (names + priorities mirror gestures.py; the actual
    detection logic lives in static/js/gestures.js).
  * The meme image files already shipped in the repo's top-level memes/ folder,
    copied into storage/memes/ as unpaired memes.

Safe to call on every startup: it only inserts what's missing.
"""

import mimetypes
import shutil
from pathlib import Path

import db

# name -> priority, matching the @gesture decorators in gestures.py.
BUILTIN_GESTURES = [
    ("shock", 50),
    ("hands_up", 40),
    ("shush", 35),
    ("thinking", 30),
    ("wink", 20),
    ("smile", 10),
]

# Ship the repo's existing sample memes into the library.
REPO_MEMES_DIR = Path(__file__).parent.parent / "memes"
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


def seed():
    db.init()
    _seed_builtin_gestures()
    _seed_sample_memes()


def _seed_builtin_gestures():
    coll = db.gestures()
    for name, priority in BUILTIN_GESTURES:
        coll.update_one(
            {"name": name},
            {"$setOnInsert": {
                "name": name,
                "kind": "builtin",
                "template": None,
                "priority": priority,
                "created_at": db._now(),
            }},
            upsert=True,
        )


def _seed_sample_memes():
    if not REPO_MEMES_DIR.exists():
        return
    for src in sorted(REPO_MEMES_DIR.iterdir()):
        if src.suffix.lower() not in IMAGE_EXT:
            continue
        # Prefix so a seeded file never collides with a user upload.
        filename = f"seed_{src.name}"
        if db.memes().find_one({"filename": filename}):
            continue
        dest = db.MEDIA_DIR / filename
        if not dest.exists():
            shutil.copy2(src, dest)
        content_type = mimetypes.guess_type(str(src))[0] or "application/octet-stream"
        db.create_meme(
            name=src.stem,
            filename=filename,
            content_type=content_type,
            gesture_id=None,
        )


if __name__ == "__main__":
    seed()
    print("Seeded gestures and sample memes.")
