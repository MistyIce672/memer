"""
Webcam gesture -> meme, split-screen.

    python main.py            # run it
    python main.py --debug    # overlay live blendshape/hand values for tuning

Press  q  or  Esc  to quit.

First run downloads two small MediaPipe model files into ./models.
"""

import argparse
import sys
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

import config
from features import build_features
from gestures import active_gesture
from meme_player import MemePlayer

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


def make_detectors(models_dir):
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=str(models_dir / "face_landmarker.task")),
        output_face_blendshapes=True,
        num_faces=1,
        running_mode=vision.RunningMode.IMAGE,
    ))
    hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mp_python.BaseOptions(
            model_asset_path=str(models_dir / "hand_landmarker.task")),
        num_hands=2,
        running_mode=vision.RunningMode.IMAGE,
    ))
    return face, hand


def draw_label(img, text):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
    cv2.rectangle(img, (10, 10), (20 + tw, 30 + th), (0, 0, 0), -1)
    cv2.putText(img, text, (15, 25 + th // 2), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (0, 255, 0), 2, cv2.LINE_AA)


def draw_debug(img, f):
    """Print the values gestures.py reads, so you can tune thresholds."""
    interesting = ["jawOpen", "mouthSmileLeft", "mouthSmileRight",
                   "eyeBlinkLeft", "eyeBlinkRight", "browOuterUpLeft",
                   "mouthPucker", "eyeSquintLeft"]
    y = 60
    for name in interesting:
        cv2.putText(img, f"{name}: {f.blend(name):.2f}", (15, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1, cv2.LINE_AA)
        y += 20
    cv2.putText(img, f"hands: {f.num_hands}", (15, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 220, 255), 1, cv2.LINE_AA)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--debug", action="store_true",
                    help="overlay live blendshape/hand values for tuning")
    ap.add_argument("--camera", type=int, default=config.CAMERA_INDEX)
    args = ap.parse_args()

    models_dir = ensure_models()
    face_det, hand_det = make_detectors(models_dir)

    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    if not cap.isOpened():
        sys.exit(f"Could not open camera {args.camera}. "
                 f"Try --camera 1, or check permissions.")

    player = MemePlayer(config.FRAME_WIDTH, config.FRAME_HEIGHT)
    shown_gesture = None
    candidate = None
    candidate_since = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if config.MIRROR:
            frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (config.FRAME_WIDTH, config.FRAME_HEIGHT))

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        f = build_features(face_det.detect(mp_image), hand_det.detect(mp_image))

        detected = active_gesture(f)

        # Debounce: a new gesture must persist GESTURE_SWITCH_DELAY seconds
        # before we swap the meme.
        now = time.monotonic()
        if detected != candidate:
            candidate, candidate_since = detected, now
        if detected != shown_gesture and (now - candidate_since) >= config.GESTURE_SWITCH_DELAY:
            shown_gesture = detected
            player.set_gesture(shown_gesture)

        draw_label(frame, f"gesture: {shown_gesture or 'none'}")
        if args.debug:
            draw_debug(frame, f)

        combined = np.hstack([frame, player.frame()])
        cv2.imshow("emote-meme  (q to quit)", combined)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
