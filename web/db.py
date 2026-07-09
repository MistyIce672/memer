"""
MongoDB storage for the web app.

Two collections:
  * gestures — the shared library of gestures. `kind` is 'builtin' (a coded
    predicate implemented in static/js/gestures.js, no template) or 'recorded'
    (a template captured in the browser, stored as a subdocument).
  * memes — uploaded meme files, each optionally paired with one gesture.

Connection is configured with the MONGO_URI env var (default local mongod) and
MONGO_DB (default 'meme_app'). Uploaded meme files live on disk under
web/storage/memes/ (gitignored); Mongo only stores their metadata.

Public helpers take the collection (via `gestures()` / `memes()`) so the API
layer stays thin. Documents are returned with a string `id` (the ObjectId).
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, MongoClient

ROOT = Path(__file__).parent
STORAGE_DIR = ROOT / "storage"
MEDIA_DIR = STORAGE_DIR / "memes"

MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.environ.get("MONGO_DB", "meme_app")

_client = None
_db = None


def connect():
    """Open the client (idempotent) and ensure indexes exist."""
    global _client, _db
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _db = _client[MONGO_DB]
    return _db


def init():
    db = connect()
    db.gestures.create_index([("name", ASCENDING)], unique=True)
    db.memes.create_index([("filename", ASCENDING)], unique=True)
    db.memes.create_index([("created_at", DESCENDING)])


def gestures():
    return connect().gestures


def memes():
    return connect().memes


def _now():
    return datetime.now(timezone.utc)


def _oid(value):
    """Parse a client-supplied id into an ObjectId, or None if malformed."""
    if value is None:
        return None
    if isinstance(value, ObjectId):
        return value
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


# --- Gestures ------------------------------------------------------------

def list_gestures():
    return [_gesture_dict(d) for d in
            gestures().find().sort([("kind", ASCENDING), ("name", ASCENDING)])]


def create_recorded_gesture(name, template, priority):
    doc = {
        "name": name,
        "kind": "recorded",
        "template": template,
        "priority": priority,
        "created_at": _now(),
    }
    res = gestures().insert_one(doc)
    doc["_id"] = res.inserted_id
    return _gesture_dict(doc)


def get_gesture(gesture_id):
    oid = _oid(gesture_id)
    if oid is None:
        return None
    doc = gestures().find_one({"_id": oid})
    return _gesture_dict(doc) if doc else None


def delete_gesture(gesture_id):
    """Delete a recorded gesture. Returns False for missing/builtin.

    Also unpairs any memes that referenced it.
    """
    oid = _oid(gesture_id)
    if oid is None:
        return False
    doc = gestures().find_one({"_id": oid})
    if doc is None or doc.get("kind") == "builtin":
        return False
    gestures().delete_one({"_id": oid})
    memes().update_many({"gesture_id": oid}, {"$set": {"gesture_id": None}})
    return True


def _gesture_dict(doc):
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "kind": doc["kind"],
        "template": doc.get("template"),
        "priority": doc.get("priority", 0),
        "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
    }


# --- Memes ---------------------------------------------------------------

def list_memes():
    docs = list(memes().find().sort([("created_at", DESCENDING)]))
    return [_meme_dict(d, _gesture_names(docs)) for d in docs]


def _gesture_names(meme_docs):
    """Resolve gesture_id -> name for a batch of memes in one query."""
    ids = {d["gesture_id"] for d in meme_docs if d.get("gesture_id")}
    if not ids:
        return {}
    return {g["_id"]: g["name"]
            for g in gestures().find({"_id": {"$in": list(ids)}}, {"name": 1})}


def create_meme(name, filename, content_type, gesture_id):
    oid = _oid(gesture_id)
    doc = {
        "name": name,
        "filename": filename,
        "content_type": content_type,
        "gesture_id": oid,
        "created_at": _now(),
    }
    res = memes().insert_one(doc)
    return get_meme(res.inserted_id)


def get_meme(meme_id):
    oid = _oid(meme_id)
    if oid is None:
        return None
    doc = memes().find_one({"_id": oid})
    return _meme_dict(doc, _gesture_names([doc])) if doc else None


def update_meme(meme_id, name=None, gesture_id=...):
    """Patch a meme. Pass gesture_id=None to unpair; omit to leave unchanged."""
    oid = _oid(meme_id)
    if oid is None:
        return None
    update = {}
    if name is not None:
        update["name"] = name
    if gesture_id is not ...:
        update["gesture_id"] = _oid(gesture_id)  # None clears the pairing
    if update:
        memes().update_one({"_id": oid}, {"$set": update})
    return get_meme(oid)


def delete_meme(meme_id):
    """Delete a meme; returns its filename (to remove from disk) or None."""
    oid = _oid(meme_id)
    if oid is None:
        return None
    doc = memes().find_one_and_delete({"_id": oid})
    return doc["filename"] if doc else None


def _meme_dict(doc, gesture_names):
    gid = doc.get("gesture_id")
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "filename": doc["filename"],
        "content_type": doc["content_type"],
        "url": f"/media/{doc['filename']}",
        "gesture_id": str(gid) if gid else None,
        "gesture_name": gesture_names.get(gid),
        "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
    }
