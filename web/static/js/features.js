// Port of features.py — turns raw MediaPipe results into a friendly Features
// object that the gesture code reads. All coordinates are normalized (0..1),
// so thresholds are resolution-independent.

// MediaPipe hand landmark indices (see the hand model diagram).
export const HandIdx = {
  WRIST: 0,
  THUMB_TIP: 4,
  INDEX_MCP: 5,
  INDEX_TIP: 8,
  MIDDLE_MCP: 9,
  MIDDLE_TIP: 12,
  RING_TIP: 16,
  PINKY_TIP: 20,
};

export function dist(a, b) {
  return Math.hypot(a[0] - b[0], a[1] - b[1]);
}

class Hand {
  constructor(landmarks, label) {
    this.landmarks = landmarks; // [[x, y, z], ...]
    this.label = label; // "Left" | "Right"
    this.WRIST = HandIdx.WRIST;
  }
  point(idx) {
    return this.landmarks[idx];
  }
  get index_tip() {
    return this.landmarks[HandIdx.INDEX_TIP];
  }
}

class Features {
  constructor() {
    this.blendshapes = {}; // name -> score
    this.face = []; // [[x, y, z], ...] or []
    this.hands = []; // Hand[]
  }
  get has_face() {
    return this.face.length > 0;
  }
  get num_hands() {
    return this.hands.length;
  }
  blend(name, def = 0.0) {
    const v = this.blendshapes[name];
    return v === undefined ? def : v;
  }
  face_point(idx) {
    return this.face[idx];
  }
  // Rough normalized face width (cheek to cheek), used to scale distances so
  // they don't depend on how close the user sits to the camera.
  get face_width() {
    if (this.face.length === 0) return 0.15;
    const left = this.face[234];
    const right = this.face[454];
    return Math.max(Math.abs(left[0] - right[0]), 1e-3);
  }
}

// Assemble a Features object from MediaPipe Tasks results (mirrors
// build_features in features.py).
export function buildFeatures(faceResult, handResult) {
  const f = new Features();

  const faceLandmarks = faceResult?.faceLandmarks;
  if (faceLandmarks && faceLandmarks.length) {
    f.face = faceLandmarks[0].map((p) => [p.x, p.y, p.z]);
  }

  const blendshapes = faceResult?.faceBlendshapes;
  if (blendshapes && blendshapes.length) {
    for (const cat of blendshapes[0].categories) {
      f.blendshapes[cat.categoryName] = cat.score;
    }
  }

  const handLandmarks = handResult?.landmarks;
  if (handLandmarks && handLandmarks.length) {
    // The plural key changed across MediaPipe versions; accept either.
    const handedness = handResult.handednesses || handResult.handedness || [];
    handLandmarks.forEach((lm, i) => {
      let label = "Right";
      if (handedness[i] && handedness[i][0]) {
        label = handedness[i][0].categoryName;
      }
      f.hands.push(new Hand(lm.map((p) => [p.x, p.y, p.z]), label));
    });
  }

  return f;
}

export { Features, Hand };
