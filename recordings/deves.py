# Recorded gesture: deves
# samples=5 baseline=5
#
# 1) Paste this function into gestures.py:

@gesture("deves", priority=25)
def deves(f):
    """Recorded gesture."""
    return (
        f.has_face
        and f.blend("mouthSmileRight") > 0.45
        and f.blend("mouthSmileLeft") > 0.35
        and f.blend("mouthLowerDownRight") > 0.32
        and f.num_hands >= 1
    )

# 2) Add this line to GESTURE_MEMES in config.py
#    (drop matching art into memes/ first):
#    "deves": "deves.gif",
#
# Notes:
#   - This pose uses hands. If the meme depends on *where* the hand is (e.g. fingertip near chin), add a distance check by hand, e.g.  dist(f.hands[0].index_tip, f.face_point(152)) < 0.09
