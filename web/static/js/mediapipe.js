// MediaPipe Tasks Vision setup — the browser equivalent of detectors.py.
//
// Loads the FaceLandmarker (with blendshapes) and HandLandmarker in VIDEO mode
// straight from the CDN — no build step. The .task model files come from the
// same Google Storage URLs the Python app uses.

import {
  FilesetResolver,
  FaceLandmarker,
  HandLandmarker,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/vision_bundle.mjs";

const WASM_URL =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.18/wasm";

const FACE_MODEL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/" +
  "face_landmarker/float16/1/face_landmarker.task";
const HAND_MODEL =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/" +
  "hand_landmarker/float16/1/hand_landmarker.task";

// Load both landmarkers. `onStatus` (optional) receives short progress strings.
export async function loadLandmarkers(onStatus = () => {}) {
  onStatus("Loading MediaPipe runtime…");
  const fileset = await FilesetResolver.forVisionTasks(WASM_URL);

  onStatus("Loading face model…");
  const face = await FaceLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: FACE_MODEL },
    outputFaceBlendshapes: true,
    numFaces: 1,
    runningMode: "VIDEO",
  });

  onStatus("Loading hand model…");
  const hand = await HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: HAND_MODEL },
    numHands: 2,
    runningMode: "VIDEO",
  });

  onStatus("Ready.");
  return { face, hand };
}

// Run both models on one video frame. `timestampMs` must strictly increase.
export function detect(landmarkers, video, timestampMs) {
  const faceResult = landmarkers.face.detectForVideo(video, timestampMs);
  const handResult = landmarkers.hand.detectForVideo(video, timestampMs);
  return { faceResult, handResult };
}
