"""
Gesture detectors.

Each gesture is a function that takes a `Features` object and returns True
when the gesture is happening. Register it with @gesture(name, priority).

  * name      -> must match a key in config.GESTURE_MEMES
  * priority  -> higher wins when several gestures match at once

To add YOUR OWN gesture:
  1. Write a function `def my_thing(f): return <bool>` using f.blend(...),
     f.hands, f.face_point(...), and dist(a, b).
  2. Decorate it with @gesture("my_thing", priority=N).
  3. Add "my_thing": "my_file.gif" to config.GESTURE_MEMES.

Tips for tuning:
  * Run `python main.py --debug` to print live blendshape scores and hand
    positions so you can pick thresholds that fit your face/camera.
  * Blendshape names come from MediaPipe (jawOpen, mouthSmileLeft,
    eyeBlinkLeft, browOuterUpLeft, mouthPucker, eyeSquintLeft, ...).
  * All coordinates are 0..1. Divide pixel-ish distances by f.face_width to
    stay independent of how close you sit to the camera.
"""

from features import dist
import custom_gestures

# Registry populated by the @gesture decorator.
GESTURES = []  # list of (name, priority, fn)


def gesture(name, priority=0):
    def wrap(fn):
        GESTURES.append((name, priority, fn))
        return fn
    return wrap


def active_gesture(f):
    """Return the name of the highest-priority matching gesture, or None."""
    best = None
    best_priority = -1
    for name, priority, fn in GESTURES:
        try:
            if fn(f) and priority > best_priority:
                best, best_priority = name, priority
        except (IndexError, KeyError):
            # Missing landmark this frame — just skip the gesture.
            continue
    return best


# =========================================================================
#  EXAMPLE GESTURES  — delete/edit freely, these are just starting points.
# =========================================================================

@gesture("shock", priority=50)
def shock(f):
    """Mouth wide open (surprise/scream)."""
    return f.has_face and f.blend("jawOpen") > 0.45


@gesture("hands_up", priority=40)
def hands_up(f):
    """Both hands raised above the nose."""
    if f.num_hands < 2 or not f.has_face:
        return False
    nose_y = f.face_point(1)[1]
    return all(h.point(h.WRIST)[1] < nose_y for h in f.hands)


@gesture("shush", priority=35)
def shush(f):
    """One index fingertip pressed to the middle of the lips."""
    if not f.has_face or f.num_hands < 1:
        return False
    lips = f.face_point(13)  # upper-inner lip
    for h in f.hands:
        if dist(h.index_tip, lips) < 0.06:
            return True
    return False


@gesture("thinking", priority=30)
def thinking(f):
    """Index fingertip near the chin."""
    if not f.has_face or f.num_hands < 1:
        return False
    chin = f.face_point(152)
    for h in f.hands:
        if dist(h.index_tip, chin) < 0.09:
            return True
    return False


@gesture("wink", priority=20)
def wink(f):
    """One eye closed while the other stays open."""
    if not f.has_face:
        return False
    left = f.blend("eyeBlinkLeft")
    right = f.blend("eyeBlinkRight")
    return (left > 0.5 and right < 0.3) or (right > 0.5 and left < 0.3)


@gesture("smile", priority=10)
def smile(f):
    """Both mouth corners pulled up."""
    if not f.has_face:
        return False
    return f.blend("mouthSmileLeft") > 0.4 and f.blend("mouthSmileRight") > 0.4
