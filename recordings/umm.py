# Recorded gesture: umm
# samples=5 baseline=6
#
# 1) Paste this function into gestures.py:

@gesture("umm", priority=25)
def umm(f):
    """Recorded gesture."""
    return (
        f.has_face
        and f.blend("mouthPressLeft") > 0.28
        and f.blend("mouthRollLower") > 0.22
        and f.blend("mouthPressRight") > 0.21
    )

# 2) Add this line to GESTURE_MEMES in config.py
#    (drop matching art into memes/ first):
#    "umm": "umm.gif",
