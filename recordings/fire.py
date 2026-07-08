# Recorded gesture: fire
# samples=5 baseline=5
#
# 1) Paste this function into gestures.py:

@gesture("fire", priority=25)
def fire(f):
    """Recorded gesture."""
    return (
        f.num_hands >= 2
    )

# 2) Add this line to GESTURE_MEMES in config.py
#    (drop matching art into memes/ first):
#    "fire": "fire.gif",
#
# Notes:
#   - This pose uses hands. If the meme depends on *where* the hand is (e.g. fingertip near chin), add a distance check by hand, e.g.  dist(f.hands[0].index_tip, f.face_point(152)) < 0.09
