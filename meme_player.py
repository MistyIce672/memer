"""
Loads and renders memes into a fixed-size pane.

Supports static images (.jpg/.png), animated GIFs and short videos
(.gif/.mp4/.webm). GIFs/videos loop. Missing files render as a labelled
placeholder so the app runs before you've added real art.
"""

import cv2
import numpy as np

import config


def _letterbox(img, w, h):
    """Resize keeping aspect ratio, centered on a black canvas of w x h."""
    ih, iw = img.shape[:2]
    scale = min(w / iw, h / ih)
    nw, nh = max(1, int(iw * scale)), max(1, int(ih * scale))
    resized = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    x, y = (w - nw) // 2, (h - nh) // 2
    canvas[y:y + nh, x:x + nw] = resized
    return canvas


def _placeholder(text, w, h):
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    canvas[:] = (40, 40, 40)
    lines = [text, "(drop a file in memes/)"]
    for i, line in enumerate(lines):
        scale = 1.0 if i == 0 else 0.5
        (tw, th), _ = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
        x = (w - tw) // 2
        y = h // 2 + i * 40
        color = (200, 200, 200) if i == 0 else (140, 140, 140)
        cv2.putText(canvas, line, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                    scale, color, 2, cv2.LINE_AA)
    return canvas


class _Media:
    """A single meme: still image, or a looping animation/video."""
    IMAGE_EXT = {".jpg", ".jpeg", ".png", ".bmp"}

    def __init__(self, name, path, w, h):
        self.name = name
        self.w, self.h = w, h
        self.frame = None       # for stills / placeholders
        self.cap = None         # for animations

        if path is None or not path.exists():
            self.frame = _placeholder(name, w, h)
            return

        if path.suffix.lower() in self.IMAGE_EXT:
            img = cv2.imread(str(path))
            self.frame = _letterbox(img, w, h) if img is not None \
                else _placeholder(f"{name} (unreadable)", w, h)
        else:
            self.cap = cv2.VideoCapture(str(path))
            if not self.cap.isOpened():
                self.cap = None
                self.frame = _placeholder(f"{name} (unreadable)", w, h)

    def read(self):
        if self.frame is not None:
            return self.frame
        ok, frame = self.cap.read()
        if not ok:  # loop back to the start
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = self.cap.read()
        if not ok:
            return _placeholder(f"{self.name} (empty)", self.w, self.h)
        return _letterbox(frame, self.w, self.h)


class MemePlayer:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self._cache = {}
        self.current = None
        self._idle = None
        if config.IDLE_MEME:
            self._idle = _Media("idle", config.MEMES_DIR / config.IDLE_MEME, w, h)

    def _get(self, gesture_name):
        if gesture_name not in self._cache:
            filename = config.GESTURE_MEMES.get(gesture_name)
            path = (config.MEMES_DIR / filename) if filename else None
            self._cache[gesture_name] = _Media(gesture_name, path, self.w, self.h)
        return self._cache[gesture_name]

    def set_gesture(self, gesture_name):
        """Switch to the meme for `gesture_name` (None -> idle)."""
        self.current = self._get(gesture_name) if gesture_name else None

    def frame(self):
        """Current meme frame to blit into the right pane."""
        if self.current is not None:
            return self.current.read()
        if self._idle is not None:
            return self._idle.read()
        return _placeholder("waiting for a gesture...", self.w, self.h)
