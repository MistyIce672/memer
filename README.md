# emote-meme (your edition)

Point your webcam at yourself; make a face or a hand gesture; the matching
meme pops up next to your video feed in real time. Powered by MediaPipe face
+ hand landmarks and OpenCV.

Inspired by [razancodes/emote-meme](https://github.com/razancodes/emote-meme),
rebuilt to be modular so you can plug in **your own gestures and memes**.

```
.
├── main.py          # webcam loop + split screen (run this)
├── config.py        # gesture -> meme map + thresholds  ← edit me
├── gestures.py      # gesture detectors (a registry)     ← add gestures here
├── features.py      # MediaPipe results -> easy Features object
├── meme_player.py   # image / gif / video rendering
└── memes/           # your meme files                    ← drop art here
```

## Setup

Python 3.11 or 3.12 is recommended (MediaPipe wheels are most reliable there).

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

First run downloads two small MediaPipe model files into `models/`.
Press `q` or `Esc` to quit.

## Make it yours — the 3-step loop

1. **Add art.** Drop an image/gif/video into `memes/`.
2. **Add a gesture.** In `gestures.py`, write a small detector and register it:

   ```python
   @gesture("tongue_out", priority=25)
   def tongue_out(f):
       return f.blend("jawOpen") > 0.3 and f.blend("mouthPucker") < 0.1
   ```

3. **Map them.** In `config.py`, add `"tongue_out": "tongue.gif"` to
   `GESTURE_MEMES`.

That's it — restart the app.

## Record a custom gesture (no eyeballing)

Don't want to guess thresholds? Let the app watch you and write the detector:

```bash
python main.py --record tongue_out
```

Then, in the window:

- **SPACE** — capture a sample while striking the pose (tap a few times).
- **B** — capture a *neutral/relaxed* baseline frame (tap a few times). Optional
  but recommended: it lets the recorder tell what actually changed vs. resting.
- **C** — clear and start over.
- **S** — analyze and save a ready-to-paste detector to `recordings/tongue_out.py`
  (also printed to the terminal), with thresholds picked from your samples.
- **Q/Esc** — quit.

Open `recordings/tongue_out.py`, paste the function into `gestures.py`, add the
mapping line it prints to `config.py`, drop your art in `memes/`, and restart.

It records every blendshape plus hand count, so face gestures and "N hands up"
work automatically. Gestures that depend on *where* a hand is (fingertip near
chin, etc.) still need a hand-written distance check — the saved file tells you
when that applies.

## Tuning thresholds to your face/camera

```bash
python main.py --debug
```

This overlays the live blendshape scores and hand count that the detectors
read. Make the face/gesture, watch the numbers, and pick thresholds just
below/above what you see.

### What you can read inside a detector

`f` is a `Features` object:

- `f.blend("jawOpen")` — a MediaPipe blendshape score `0..1`. Useful names:
  `jawOpen`, `mouthSmileLeft/Right`, `eyeBlinkLeft/Right`,
  `browOuterUpLeft/Right`, `mouthPucker`, `mouthFunnel`, `eyeSquintLeft/Right`.
- `f.has_face`, `f.num_hands`
- `f.face_point(i)` — face landmark `i` as `(x, y, z)`, coords `0..1`
  (e.g. `1` = nose tip, `152` = chin, `13` = upper lip).
- `f.hands` — list of `Hand`; each has `h.index_tip`, `h.point(h.WRIST)`, etc.
- `dist(a, b)` from `features.py` — 2D distance between two points.
- `f.face_width` — divide distances by this to stay independent of how close
  you sit.

Higher `priority` wins when multiple gestures match the same frame.

## Troubleshooting

- **Camera won't open** → try `python main.py --camera 1`, or check the OS
  camera permission for your terminal.
- **`pip install mediapipe` fails on Python 3.13** → use a 3.11/3.12 venv.
- **A meme shows a grey placeholder** → the file named in `config.py` isn't in
  `memes/` yet (or the extension differs).
- **Gestures never trigger** → run with `--debug` and lower the thresholds.
