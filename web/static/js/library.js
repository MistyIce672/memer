// Library page: upload memes, browse/record gestures, pair them, and pick a
// set of memes for a play session.

import { api } from "./api.js";
import { toast, prettyName, loadSession, saveSession } from "./util.js";
import { initRecorder } from "./record.js";

let memes = [];
let gestures = [];
let selected = new Set(loadSession());

const el = (id) => document.getElementById(id);

async function refresh() {
  [memes, gestures] = await Promise.all([api.listMemes(), api.listGestures()]);
  // Drop selections for memes that no longer exist.
  const ids = new Set(memes.map((m) => m.id));
  selected = new Set([...selected].filter((id) => ids.has(id)));
  renderGestureOptions();
  renderGestureList();
  renderMemes();
  renderSession();
}

// --- Gesture <select> options (upload form + each card) ------------------

function gestureOptionsHtml(selectedId) {
  const opts = ['<option value="">— no gesture —</option>'];
  for (const g of gestures) {
    const sel = g.id === selectedId ? " selected" : "";
    const kind = g.kind === "recorded" ? "•" : "";
    opts.push(`<option value="${g.id}"${sel}>${prettyName(g.name)} ${kind}</option>`);
  }
  return opts.join("");
}

function renderGestureOptions() {
  el("up-gesture").innerHTML = gestureOptionsHtml("");
}

// --- Gesture chips -------------------------------------------------------

function renderGestureList() {
  const box = el("gesture-list");
  box.innerHTML = "";
  if (!gestures.length) {
    box.innerHTML = '<span class="muted">No gestures yet.</span>';
    return;
  }
  for (const g of gestures) {
    const chip = document.createElement("span");
    chip.className = "chip";
    const tag = g.kind === "recorded" ? "recorded" : "built-in";
    chip.innerHTML = `<strong>${prettyName(g.name)}</strong>
      <span class="tag ${g.kind}">${tag}</span>`;
    if (g.kind === "recorded") {
      const del = document.createElement("button");
      del.title = "Delete gesture";
      del.textContent = "✕";
      del.addEventListener("click", () => deleteGesture(g));
      chip.appendChild(del);
    }
    box.appendChild(chip);
  }
}

async function deleteGesture(g) {
  if (!confirm(`Delete gesture “${prettyName(g.name)}”? Memes using it become unpaired.`))
    return;
  try {
    await api.deleteGesture(g.id);
    toast(`Deleted “${prettyName(g.name)}”.`);
    await refresh();
  } catch (err) {
    toast(err.message, true);
  }
}

// --- Meme cards ----------------------------------------------------------

function renderMemes() {
  const grid = el("meme-grid");
  grid.innerHTML = "";
  el("meme-empty").hidden = memes.length > 0;

  for (const m of memes) {
    const card = document.createElement("div");
    card.className = "card" + (selected.has(m.id) ? " selected" : "");

    const media = m.content_type.startsWith("video/")
      ? `<video src="${m.url}" muted loop playsinline></video>`
      : `<img src="${m.url}" alt="${m.name}" />`;

    card.innerHTML = `
      <div class="thumb">${media}</div>
      <div class="body">
        <div class="name">${m.name}</div>
        <select class="pair">${gestureOptionsHtml(m.gesture_id)}</select>
        <div class="actions">
          <label class="pick">
            <input type="checkbox" class="sel" ${selected.has(m.id) ? "checked" : ""} />
            session
          </label>
          <button class="btn-sm btn-danger del">Delete</button>
        </div>
      </div>`;

    card.querySelector(".pair").addEventListener("change", (e) =>
      pairMeme(m, e.target.value)
    );
    card.querySelector(".sel").addEventListener("change", (e) =>
      toggleSelect(m.id, e.target.checked)
    );
    card.querySelector(".del").addEventListener("click", () => deleteMeme(m));

    grid.appendChild(card);
  }
}

async function pairMeme(m, gestureId) {
  try {
    const updated = await api.patchMeme(m.id, { gesture_id: gestureId || null });
    Object.assign(m, updated);
    renderSession();
  } catch (err) {
    toast(err.message, true);
  }
}

async function deleteMeme(m) {
  if (!confirm(`Delete meme “${m.name}”?`)) return;
  try {
    await api.deleteMeme(m.id);
    selected.delete(m.id);
    saveSession([...selected]);
    await refresh();
  } catch (err) {
    toast(err.message, true);
  }
}

function toggleSelect(id, on) {
  if (on) selected.add(id);
  else selected.delete(id);
  saveSession([...selected]);
  renderMemes();
  renderSession();
}

// --- Session bar ---------------------------------------------------------

function renderSession() {
  const chosen = memes.filter((m) => selected.has(m.id));
  const withGesture = chosen.filter((m) => m.gesture_id);
  const countEl = el("session-count");
  const link = el("start-session");

  if (chosen.length === 0) {
    countEl.textContent = "Pick memes to start";
  } else {
    const missing = chosen.length - withGesture.length;
    countEl.textContent =
      `${withGesture.length} ready` + (missing ? ` · ${missing} need a gesture` : "");
  }
  link.classList.toggle("disabled", withGesture.length === 0);
}

el("start-session").addEventListener("click", (e) => {
  const chosen = memes.filter((m) => selected.has(m.id) && m.gesture_id);
  if (chosen.length === 0) {
    e.preventDefault();
    toast("Select at least one meme that's paired with a gesture.", true);
    return;
  }
  // Warn (but allow) if two selected memes share the same gesture — only the
  // first will show for that gesture.
  const seen = new Map();
  const dupes = chosen.filter((m) => {
    if (seen.has(m.gesture_id)) return true;
    seen.set(m.gesture_id, m);
    return false;
  });
  if (dupes.length) {
    toast("Heads up: two memes share a gesture; only one will show for it.");
  }
  saveSession(chosen.map((m) => m.id));
});

// --- Upload --------------------------------------------------------------

el("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = el("up-file").files[0];
  if (!file) return;
  const name = el("up-name").value.trim();
  const gestureId = el("up-gesture").value;
  try {
    await api.uploadMeme(file, name, gestureId);
    e.target.reset();
    toast("Meme uploaded.");
    await refresh();
  } catch (err) {
    toast(err.message, true);
  }
});

// --- Boot ----------------------------------------------------------------

initRecorder(() => refresh());
refresh().catch((err) => toast(err.message || "Failed to load library.", true));
