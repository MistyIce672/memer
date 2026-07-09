"""
Shared MediaPipe setup, used by both main.py and recorder.py.

`Vision.process(bgr_frame)` runs the face + hand models and returns a
Features object (see features.py).
"""

import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import config
from features import build_features

MODELS = {
    "face_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
        "face_landmarker/float16/1/face_landmarker.task",
    "hand_landmarker.task":
        "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
        "hand_landmarker/float16/1/hand_landmarker.task",
}


def ensure_models():
    config.MODELS_DIR.mkdir(exist_ok=True)
    for name, url in MODELS.items():
        dest = config.MODELS_DIR / name
        if not dest.exists():
            print(f"Downloading {name} ...", flush=True)
            urllib.request.urlretrieve(url, dest)
    return config.MODELS_DIR


class Vision:
    def __init__(self):
        models_dir = ensure_models()
        self.face = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=str(models_dir / "face_landmarker.task")),
                output_face_blendshapes=True,
                num_faces=1,
                running_mode=vision.RunningMode.IMAGE,
            ))
        self.hand = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(
                    model_asset_path=str(models_dir / "hand_landmarker.task")),
                num_hands=2,
                running_mode=vision.RunningMode.IMAGE,
            ))

    def process(self, bgr_frame):
        rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        return build_features(self.face.detect(mp_image),
                              self.hand.detect(mp_image))
