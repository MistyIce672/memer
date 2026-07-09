// Small shared UI helpers.

let toastTimer = null;

export function toast(message, isError = false) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = message;
  el.classList.toggle("error", isError);
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
}

// "peace_sign" -> "peace sign" for display.
export function prettyName(name) {
  return (name || "").replace(/_/g, " ");
}

// localStorage key holding the meme ids selected for a play session.
export const SESSION_KEY = "gesturememe.session";

export function loadSession() {
  try {
    return JSON.parse(localStorage.getItem(SESSION_KEY)) || [];
  } catch {
    return [];
  }
}

export function saveSession(ids) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(ids));
}
