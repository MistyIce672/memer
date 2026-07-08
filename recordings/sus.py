# Recorded gesture: sus
# samples=6 baseline=6
#
# 1) Paste this function into gestures.py:

@gesture("sus", priority=25)
def sus(f):
    """Recorded gesture."""
    return (
        f.has_face
        and f.blend("eyeLookInLeft") > 0.38
        and f.blend("eyeLookOutRight") > 0.36
    )

# 2) Add this line to GESTURE_MEMES in config.py
#    (drop matching art into memes/ first):
#    "sus": "sus.gif",
