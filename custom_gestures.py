"""
Recorded ("custom") gestures.

Instead of hand-writing thresholds, you strike a pose and recorder.py stores
the average of your face blendshapes + hand positions as a *template*. At
runtime we build the same feature vector from the live frame and pick the
closest template that's within its recorded threshold.

Feature vector layout (all resolution-independent):
  [ blendshape scores (one per name in BLEND order) ]
  [ Left  hand: presence(0/1), then 21 (x,y) points relative to the nose ]
  [ Right hand: presence(0/1), then 21 (x,y) points relative to the nose ]

Hand points are measured relative to the nose and divided by face width, so a
template captures *where the hand is relative to your face* and its shape —
which is exactly what distinguishes "finger on chin" from "hand above head".
"""

import json

import numpy as np

import config

# Default priority for a recorded gesture (higher beats the built-in
# examples in gestures.py). Override per-gesture with recorder.py --priority.
DEFAULT_PRIORITY = 100

_PTS_PER_HAND = 21
_HAND_SLOT = 1 + 2 * _PTS_PER_HAND  # presence + (x,y) per point


def feature_vector(f, blend_names):
    """Build the numeric vector for frame `f` given an ordered name list."""
    vec = [f.blend(n) for n in blend_names]

    anchor = f.face_point(1)[:2] if f.has_face else None  # nose tip
    scale = f.face_width

    by_label = {"Left": None, "Right": None}
    for h in f.hands:
        by_label[h.label] = h

    for label in ("Left", "Right"):
        h = by_label[label]
        if h is None:
            vec.append(0.0)
            vec.extend([0.0] * (2 * _PTS_PER_HAND))
            continue
        vec.append(1.0)
        ax, ay = anchor if anchor else h.point(h.WRIST)[:2]
        for (x, y, _z) in h.landmarks:
            vec.append((x - ax) / scale)
            vec.append((y - ay) / scale)
    return vec


def feature_weights(n_blend):
    """Per-dimension weights matching feature_vector's layout."""
    w = [1.0] * n_blend
    for _ in range(2):                    # Left, Right slots
        w.append(3.0)                     # hand presence matters a lot
        w.extend([0.5] * (2 * _PTS_PER_HAND))
    return np.array(w, dtype=np.float64)


def wdist(a, b, w):
    d = a - b
    return float(np.sqrt(np.sum(w * d * d)))


class _Templates:
    """Loaded recorded gestures + shared blendshape name order."""

    def __init__(self):
        self.blend_names = []
        self.weights = None
        self.items = {}   # name -> {"mean": np.array, "threshold", "priority"}

    def load(self):
        self.__init__()
        path = config.CUSTOM_GESTURES_FILE
        if not path.exists():
            return self
        data = json.loads(path.read_text())
        self.blend_names = data.get("blendshape_names", [])
        self.weights = feature_weights(len(self.blend_names))
        for name, t in data.get("gestures", {}).items():
            self.items[name] = {
                "mean": np.array(t["mean"], dtype=np.float64),
                "threshold": float(t["threshold"]),
                "priority": int(t.get("priority", DEFAULT_PRIORITY)),
            }
        return self


_T = _Templates().load()


def reload():
    """Re-read the JSON (called after recording)."""
    global _T
    _T = _Templates().load()
    return _T


def scores(f):
    """Distance from the live frame to every template, for tuning/debug.
    Returns list of (name, distance, threshold) sorted nearest-first."""
    if not _T.items:
        return []
    vec = np.array(feature_vector(f, _T.blend_names), dtype=np.float64)
    out = [(name, wdist(vec, t["mean"], _T.weights), t["threshold"])
           for name, t in _T.items.items()]
    out.sort(key=lambda r: r[1])
    return out


def best_custom(f):
    """Closest recorded gesture within its threshold, as (name, priority)."""
    best = None
    best_d = float("inf")
    for name, dist, thr in scores(f):
        if dist <= thr and dist < best_d:
            best, best_d = (name, _T.items[name]["priority"]), dist
    return best
