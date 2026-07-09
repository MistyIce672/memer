// Play session — the browser port of main.py's webcam loop.
//
// Reads the memes picked on the library page, runs the camera through
// MediaPipe, picks the highest-priority matching gesture each frame, debounces
// the switch (GESTURE_SWITCH_DELAY, like config.py), and shows the paired meme.

import { loadLandmarkers, detect } from "./mediapipe.js";
import { buildFeatures } from "./features.js";
import { GestureMatcher } from "./gestures.js";
import { api } from "./api.js";
import { toast, prettyName, loadSession } from "./util.js";

const GESTURE_SWITCH_DELAY = 150; // ms — mirrors config.GESTURE_SWITCH_DELAY (0.15s)

const el = (id) => document.getElementById(id);

let landmarkers = null;
let stream = null;
let running = false;
let matcher = null;

let memesByGesture = new Map(); // gestureId -> meme
let gestureName = new Map(); // gestureId -> display name
let memeEls = new Map(); // gestureId -> media element (pre-created, hidden)

// Debounce state (see main.py).
let shownGesture = undefined;
let candidate = null;
let candidateSince = 0;

async function boot() {
  const wantIds = new Set(loadSession());
  if (wantIds.size === 0) {
    el("status").textContent = "No memes selected.";
    toast("Pick some memes in the library first.", true);
    return;
  }

  let memes, gestures;
  try {
    [memes, gestures] = await Promise.all([api.listMemes(), api.listGestures()]);
  } catch (err) {
    el("status").textContent = "Failed to load.";
    toast(err.message, true);
    return;
  }

  const gestureById = new Map(gestures.map((g) => [g.id, g]));
  const chosen = memes.filter((m) => wantIds.has(m.id) && m.gesture_id);

  for (const m of chosen) {
    if (memesByGesture.has(m.gesture_id)) continue; // first meme wins per gesture
    memesByGesture.set(m.gesture_id, m);
    const g = gestureById.get(m.gesture_id);
    gestureName.set(m.gesture_id, g ? prettyName(g.name) : "?");
  }

  if (memesByGesture.size === 0) {
    el("status").textContent = "Selected memes have no gestures.";
    toast("None of the selected memes are paired with a gesture.", true);
    return;
  }

  // Only the gestures actually in play need matching.
  const inPlay = [...memesByGesture.keys()]
    .map((id) => gestureById.get(id))
    .filter(Boolean);
  matcher = new GestureMatcher(inPlay);

  buildMemeElements();
  buildTray();
  el("status").textContent = "Ready.";
  el("start-btn").disabled = false;
  el("start-btn").addEventListener("click", start);
}

function buildMemeElements() {
  const pane = el("meme-pane");
  for (const [gid, m] of memesByGesture) {
    let node;
    if (m.content_type.startsWith("video/")) {
      node = document.createElement("video");
      node.src = m.url;
      node.loop = true;
      node.muted = true;
      node.playsInline = true;
    } else {
      node = document.createElement("img");
      node.src = m.url;
      node.alt = m.name;
    }
    node.style.display = "none";
    memeEls.set(gid, node);
    pane.appendChild(node);
  }
}

function buildTray() {
  const tray = el("tray");
  tray.innerHTML = "";
  for (const [gid, m] of memesByGesture) {
    const mini = document.createElement("span");
    mini.className = "mini";
    mini.dataset.gid = gid;
    mini.textContent = `${gestureName.get(gid)} → ${m.name}`;
    tray.appendChild(mini);
  }
}

async function start() {
  const btn = el("start-btn");
  btn.disabled = true;
  el("status").textContent = "Starting camera…";
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
      audio: false,
    });
    el("cam").srcObject = stream;
    await el("cam").play();
  } catch {
    el("status").textContent = "Camera permission denied.";
    toast("Could not access the camera.", true);
    btn.disabled = false;
    return;
  }

  if (!landmarkers) {
    landmarkers = await loadLandmarkers((s) => (el("status").textContent = s));
  }
  el("status").textContent = "Running — make a gesture!";
  running = true;
  requestAnimationFrame(loop);
}

function loop(ts) {
  if (!running) return;
  const cam = el("cam");
  if (cam.readyState >= 2) {
    const { faceResult, handResult } = detect(landmarkers, cam, ts);
    const f = buildFeatures(faceResult, handResult);
    const detected = matcher.activeGesture(f); // gesture id or null

    // Debounce: a new candidate must persist before we swap the meme.
    if (detected !== candidate) {
      candidate = detected;
      candidateSince = ts;
    }
    if (detected !== shownGesture && ts - candidateSince >= GESTURE_SWITCH_DELAY) {
      showGesture(detected);
    }
  }
  requestAnimationFrame(loop);
}

function showGesture(gid) {
  shownGesture = gid;

  for (const [id, node] of memeEls) {
    const on = id === gid;
    node.style.display = on ? "" : "none";
    if (on && node.tagName === "VIDEO") node.play().catch(() => {});
    else if (node.tagName === "VIDEO") node.pause();
  }

  el("idle-text").style.display = gid ? "none" : "";
  el("gesture-label").textContent = gid ? gestureName.get(gid) : "—";

  for (const mini of el("tray").children) {
    mini.classList.toggle("active", mini.dataset.gid === gid);
  }
}

window.addEventListener("beforeunload", () => {
  running = false;
  if (stream) stream.getTracks().forEach((t) => t.stop());
});

boot();
