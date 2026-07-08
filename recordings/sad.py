# Recorded gesture: sad
# samples=6 baseline=5
#
# 1) Paste this function into gestures.py:

@gesture("sad", priority=25)
def sad(f):
    """Recorded gesture."""
    return (
        f.has_face
        and f.blend("eyeSquintRight") > 0.27
        and f.blend("browInnerUp") < 0.40
        and f.blend("eyeSquintLeft") > 0.33
        and f.num_hands >= 1
    )

# 2) Add this line to GESTURE_MEMES in config.py
#    (drop matching art into memes/ first):
#    "sad": "sad.gif",
#
# Notes:
#   - This pose uses hands. If the meme depends on *where* the hand is (e.g. fingertip near chin), add a distance check by hand, e.g.  dist(f.hands[0].index_tip, f.face_point(152)) < 0.09
