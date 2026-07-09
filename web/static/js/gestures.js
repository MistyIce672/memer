// Port of gestures.py (built-in predicates) + custom_gestures.py (recorded
// template matching), plus the "highest priority wins" merge from
// active_gesture().

import { dist, HandIdx } from "./features.js";

// =========================================================================
//  BUILT-IN GESTURES — direct port of the @gesture predicates in gestures.py.
//  Keyed by name; priorities mirror the Python decorators / seed.py.
// =========================================================================

export const BUILTIN_FNS = {
  // Mouth wide open (surprise/scream).
  shock: (f) => f.has_face && f.blend("jawOpen") > 0.45,

  // Both hands raised above the nose.
  hands_up: (f) => {
    if (f.num_hands < 2 || !f.has_face) return false;
    const noseY = f.face_point(1)[1];
    return f.hands.every((h) => h.point(HandIdx.WRIST)[1] < noseY);
  },

  // One index fingertip pressed to the middle of the lips.
  shush: (f) => {
    if (!f.has_face || f.num_hands < 1) return false;
    const lips = f.face_point(13);
    return f.hands.some((h) => dist(h.index_tip, lips) < 0.06);
  },

  // Index fingertip near the chin.
  thinking: (f) => {
    if (!f.has_face || f.num_hands < 1) return false;
    const chin = f.face_point(152);
    return f.hands.some((h) => dist(h.index_tip, chin) < 0.09);
  },

  // One eye closed while the other stays open.
  wink: (f) => {
    if (!f.has_face) return false;
    const left = f.blend("eyeBlinkLeft");
    const right = f.blend("eyeBlinkRight");
    return (left > 0.5 && right < 0.3) || (right > 0.5 && left < 0.3);
  },

  // Both mouth corners pulled up.
  smile: (f) =>
    f.has_face &&
    f.blend("mouthSmileLeft") > 0.4 &&
    f.blend("mouthSmileRight") > 0.4,
};

// =========================================================================
//  RECORDED TEMPLATE MATCHING — port of custom_gestures.py.
// =========================================================================

const PTS_PER_HAND = 21;
export const DEFAULT_PRIORITY = 100; // recorded beats the built-in examples

// Build the numeric feature vector for frame `f` given an ordered name list.
// Layout: [blendshape scores] [Left: presence + 21 (x,y)] [Right: same],
// hand points measured relative to the nose and divided by face width.
export function featureVector(f, blendNames) {
  const vec = blendNames.map((n) => f.blend(n));

  const anchor = f.has_face ? f.face_point(1) : null; // nose tip
  const scale = f.face_width;

  const byLabel = { Left: null, Right: null };
  for (const h of f.hands) byLabel[h.label] = h;

  for (const label of ["Left", "Right"]) {
    const h = byLabel[label];
    if (h === null) {
      vec.push(0.0);
      for (let i = 0; i < 2 * PTS_PER_HAND; i++) vec.push(0.0);
      continue;
    }
    vec.push(1.0);
    const [ax, ay] = anchor ? anchor : h.point(HandIdx.WRIST);
    for (const [x, y] of h.landmarks) {
      vec.push((x - ax) / scale);
      vec.push((y - ay) / scale);
    }
  }
  return vec;
}

// Per-dimension weights matching featureVector's layout.
export function featureWeights(nBlend) {
  const w = new Array(nBlend).fill(1.0);
  for (let i = 0; i < 2; i++) {
    w.push(3.0); // hand presence matters a lot
    for (let j = 0; j < 2 * PTS_PER_HAND; j++) w.push(0.5);
  }
  return w;
}

export function wdist(a, b, w) {
  let s = 0.0;
  for (let i = 0; i < a.length; i++) {
    const d = a[i] - b[i];
    s += w[i] * d * d;
  }
  return Math.sqrt(s);
}

// =========================================================================
//  MATCHER — picks the highest-priority matching gesture for a frame.
//  Built with the subset of gestures "in play" for a session.
// =========================================================================

export class GestureMatcher {
  // `gestures` is an array of DB gesture docs: {id, name, kind, priority,
  // template}. Recorded docs carry template = {mean, threshold, blend_names}.
  constructor(gestures) {
    this.builtins = [];
    this.recorded = [];
    for (const g of gestures) {
      if (g.kind === "builtin") {
        const fn = BUILTIN_FNS[g.name];
        if (fn) this.builtins.push({ id: g.id, priority: g.priority, fn });
      } else if (g.template && g.template.mean) {
        this.recorded.push({
          id: g.id,
          priority: g.priority ?? g.template.priority ?? DEFAULT_PRIORITY,
          mean: g.template.mean,
          threshold: g.template.threshold,
          blendNames: g.template.blend_names,
          weights: featureWeights(g.template.blend_names.length),
        });
      }
    }
  }

  // Return the id of the winning gesture for frame `f`, or null.
  activeGesture(f) {
    let bestId = null;
    let bestPriority = -1;

    for (const b of this.builtins) {
      try {
        if (b.fn(f) && b.priority > bestPriority) {
          bestId = b.id;
          bestPriority = b.priority;
        }
      } catch {
        // Missing landmark this frame — just skip the gesture.
      }
    }

    // Closest recorded template within its threshold (custom_gestures.best_custom),
    // then folded into the same priority contest.
    let bestDist = Infinity;
    let recWinner = null;
    for (const r of this.recorded) {
      const vec = featureVector(f, r.blendNames);
      const d = wdist(vec, r.mean, r.weights);
      if (d <= r.threshold && d < bestDist) {
        bestDist = d;
        recWinner = r;
      }
    }
    if (recWinner && recWinner.priority > bestPriority) {
      bestId = recWinner.id;
      bestPriority = recWinner.priority;
    }

    return bestId;
  }

  // For tuning/debug: nearest recorded template as {id, dist, threshold}[].
  recordedScores(f) {
    return this.recorded
      .map((r) => ({
        id: r.id,
        dist: wdist(featureVector(f, r.blendNames), r.mean, r.weights),
        threshold: r.threshold,
      }))
      .sort((a, b) => a.dist - b.dist);
  }
}
