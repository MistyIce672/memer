"""
Central configuration.

This is the file you'll edit most. To add your own meme:
  1. Drop an image/gif/video into the `memes/` folder.
  2. Add or reuse a gesture name in `gestures.py`.
  3. Map the gesture name -> your file below in GESTURE_MEMES.

If a mapped file is missing, the app shows a text placeholder so it still
runs while you're collecting art.
"""

from pathlib import Path

# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).parent
MEMES_DIR = ROOT / "memes"
MODELS_DIR = ROOT / "models"

# --- Camera / window -----------------------------------------------------
CAMERA_INDEX = 0          # change if you have multiple webcams
FRAME_WIDTH = 640         # per-pane width; window is 2x this wide
FRAME_HEIGHT = 480
MIRROR = True             # flip the webcam like a mirror

# How long a gesture must "win" before we swap the meme (seconds).
# Prevents flicker when detections jump around frame-to-frame.
GESTURE_SWITCH_DELAY = 0.15

# --- Gesture -> meme file ------------------------------------------------
# Keys must match the gesture `name`s registered in gestures.py.
# Values are filenames inside memes/. Supports .jpg .png .gif .mp4 .webm
GESTURE_MEMES = {
    "smile":     "smile.jpg",
    "shock":     "shock.gif",
    "wink":      "wink.jpg",
    "thinking":  "thinking.jpg",
    "shush":     "shush.jpg",
    "umm":       "umm.jpeg",
    "sus":       "sus.jpeg",
    "sad":       "sad.jpeg",
    "fire":      "fire.jpeg",
    "deves":     "deves.jpeg",
}

# When no gesture is active, show this (or None for a blank pane).
IDLE_MEME = None
