// Gesture recording flow — the browser version of the recorder.py that the
// README described but was never built.
//
// You hold a pose; we capture ~30 valid frames, average their feature vectors
// into a template `mean`, derive a `threshold` from how much the samples spread,
// and POST it as a recorded gesture (see custom_gestures.py for the matching
// side).

import { loadLandmarkers, detect } from "./mediapipe.js";
import { buildFeatures } from "./features.js";
import {
  featureVector,
  featureWeights,
  wdist,
  DEFAULT_PRIORITY,
} from "./gestures.js";
import { api } from "./api.js";
import { toast } from "./util.js";

const TARGET_SAMPLES = 30;

// Singleton state for the modal.
let landmarkers = null;
let stream = null;
let running = false;
let capturing = false;
let samples = [];
let blendNames = null;
let template = null; // {mean, threshold, blend_names}
let onSavedCb = null;

const els = {};

function bind() {
  els.modal = document.getElementById("record-modal");
  els.video = document.getElementById("rec-video");
  els.name = document.getElementById("rec-name");
  els.status = document.getElementById("rec-status");
  els.progress = document.getElementById("rec-progress");
  els.capture = document.getElementById("rec-capture");
  els.save = document.getElementById("rec-save");
  els.cancel = document.getElementById("rec-cancel");

  els.cancel.addEventListener("click", close);
  els.capture.addEventListener("click", startCapture);
  els.save.addEventListener("click", save);
}

export function initRecorder(onSaved) {
  onSavedCb = onSaved;
  bind();
  document.getElementById("record-btn").addEventListener("click", open);
}

async function open() {
  els.modal.classList.add("open");
  els.name.value = "";
  resetCaptureState();
  els.status.textContent = "Starting camera…";
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
      audio: false,
    });
    els.video.srcObject = stream;
    await els.video.play();
  } catch (err) {
    els.status.textContent = "Camera permission denied.";
    toast("Could not access the camera.", true);
    return;
  }

  if (!landmarkers) {
    landmarkers = await loadLandmarkers((s) => (els.status.textContent = s));
  }
  els.status.textContent = "Ready — strike your pose, then capture.";
  els.capture.disabled = false;
  running = true;
  requestAnimationFrame(loop);
}

function resetCaptureState() {
  capturing = false;
  samples = [];
  blendNames = null;
  template = null;
  els.progress.style.width = "0%";
  els.capture.disabled = true;
  els.save.disabled = true;
}

function startCapture() {
  const name = els.name.value.trim();
  if (!name) {
    toast("Give the gesture a name first.", true);
    els.name.focus();
    return;
  }
  samples = [];
  blendNames = null;
  template = null;
  els.save.disabled = true;
  els.progress.style.width = "0%";
  capturing = true;
  els.capture.disabled = true;
  els.status.textContent = "Hold still…";
}

function loop(ts) {
  if (!running) return;
  if (els.video.readyState >= 2) {
    const { faceResult, handResult } = detect(landmarkers, els.video, ts);
    const f = buildFeatures(faceResult, handResult);

    if (capturing) {
      // Skip frames with nothing to record (no face and no hands).
      if (f.has_face || f.num_hands > 0) {
        if (!blendNames) blendNames = Object.keys(f.blendshapes);
        samples.push(featureVector(f, blendNames));
        const pct = Math.min(100, (samples.length / TARGET_SAMPLES) * 100);
        els.progress.style.width = pct + "%";
        if (samples.length >= TARGET_SAMPLES) finishCapture();
      }
    }
  }
  requestAnimationFrame(loop);
}

function finishCapture() {
  capturing = false;
  const n = samples.length;
  const dim = samples[0].length;
  const mean = new Array(dim).fill(0);
  for (const s of samples) for (let i = 0; i < dim; i++) mean[i] += s[i];
  for (let i = 0; i < dim; i++) mean[i] /= n;

  const weights = featureWeights(blendNames.length);
  let maxSpread = 0;
  for (const s of samples) maxSpread = Math.max(maxSpread, wdist(s, mean, weights));
  // Slack so matching isn't impossibly tight, with a small floor.
  const threshold = maxSpread * 1.4 + 0.5;

  template = { mean, threshold, blend_names: blendNames };
  els.status.textContent = `Captured ${n} frames. Save, or capture again to redo.`;
  els.capture.disabled = false;
  els.save.disabled = false;
}

async function save() {
  if (!template) return;
  const name = els.name.value.trim();
  try {
    const gesture = await api.createGesture({
      name,
      mean: template.mean,
      threshold: template.threshold,
      blend_names: template.blend_names,
      priority: DEFAULT_PRIORITY,
    });
    toast(`Saved gesture “${name}”.`);
    close();
    if (onSavedCb) onSavedCb(gesture);
  } catch (err) {
    toast(err.message || "Could not save gesture.", true);
  }
}

function close() {
  running = false;
  capturing = false;
  els.modal.classList.remove("open");
  if (stream) {
    stream.getTracks().forEach((t) => t.stop());
    stream = null;
  }
  els.video.srcObject = null;
}
