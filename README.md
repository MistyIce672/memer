# emote-meme (your edition)

Point your webcam at yourself; make a face or a hand gesture; the matching
meme pops up next to your video feed in real time. Powered by MediaPipe face
+ hand landmarks and OpenCV.

Inspired by [razancodes/emote-meme](https://github.com/razancodes/emote-meme),
rebuilt to be modular so you can plug in **your own gestures and memes**.

There are two ways to run it:

- **Desktop app** (`python main.py`) — the original OpenCV split-screen loop
  configured by editing `config.py` / `gestures.py`.
- **Website** (`web/`) — upload memes, record gestures in the browser, pair
  them, and run a camera session. All detection runs client-side in the
  browser; see [Run the website](#run-the-website).

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

## Run the website

The website (`web/`) turns the desktop tool into something anyone can use from
a browser: **upload memes**, **record a gesture** (or pick an existing one) and
**pair** them, then **select memes and start a camera session** where doing the
gestures shows the memes. Gesture recognition runs entirely in the browser via
MediaPipe's WebAssembly build — the webcam never leaves your machine.

### Prerequisites

- A running **MongoDB** (metadata store). Point at it with `MONGO_URI`
  (default `mongodb://localhost:27017`); start one locally with e.g.
  `podman run -d -p 27017:27017 --name mongo mongo:7`.

### Start it

```bash
pip install -r web/requirements.txt
cd web
uvicorn app:app --reload
```

Open http://localhost:8000. On first run the library is seeded with the sample
memes from `memes/` and the six built-in gestures (smile, shock, wink, thinking,
shush, hands_up). Uploaded files land in `web/storage/` (gitignored).

### How the pieces map to the desktop app

| Desktop (Python)                    | Website (browser JS)                    |
| ----------------------------------- | --------------------------------------- |
| `detectors.py` MediaPipe setup      | `web/static/js/mediapipe.js`            |
| `features.py`                       | `web/static/js/features.js`             |
| `gestures.py` built-ins             | built-in predicates in `gestures.js`    |
| `custom_gestures.py` template match | template matching in `gestures.js`      |
| the (missing) `recorder.py`         | `web/static/js/record.js` (in-browser)  |
| `main.py` loop + `meme_player.py`   | `web/static/js/play.js` + `play.html`   |
| `config.GESTURE_MEMES` mapping      | per-meme pairing stored in MongoDB      |

### Deploy

`.github/workflows/deploy.yml` builds the `Dockerfile` and (re)starts the
container over SSH on push to `main`. It expects repo secrets `HOST`,
`USERNAME`, `SSH_PRIVATE_KEY`, a checkout at `~/prod/gesture-meme/` on the host,
and a `~/prod/gesture-meme/.env` file supplying `MONGO_URI` (pointing at a
reachable MongoDB). Uploads persist via the `~/prod/gesture-meme/storage`
volume.

## Troubleshooting

- **Camera won't open** → try `python main.py --camera 1`, or check the OS
  camera permission for your terminal.
- **`pip install mediapipe` fails on Python 3.13** → use a 3.11/3.12 venv.
- **A meme shows a grey placeholder** → the file named in `config.py` isn't in
  `memes/` yet (or the extension differs).
- **Gestures never trigger** → run with `--debug` and lower the thresholds.
