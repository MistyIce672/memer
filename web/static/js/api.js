// Thin fetch wrappers around the FastAPI backend.

async function req(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  listMemes: () => req("/api/memes"),

  uploadMeme: (file, name, gestureId) => {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("name", name);
    if (gestureId) fd.append("gesture_id", gestureId);
    return req("/api/memes", { method: "POST", body: fd });
  },

  // pairing: pass {gesture_id: id|null} to set/clear, {name} to rename.
  patchMeme: (id, patch) =>
    req(`/api/memes/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }),

  deleteMeme: (id) => req(`/api/memes/${id}`, { method: "DELETE" }),

  listGestures: () => req("/api/gestures"),

  createGesture: (payload) =>
    req("/api/gestures", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),

  deleteGesture: (id) => req(`/api/gestures/${id}`, { method: "DELETE" }),
};
