// Small client-side helpers. HTMX does the heavy lifting.

// Mobile nav toggle
document.addEventListener("click", (e) => {
  const btn = e.target.closest("[data-nav-toggle]");
  if (!btn) return;
  const menu = document.getElementById("mobile-menu");
  if (menu) menu.classList.toggle("hidden");
});

// Confirmation dialogs for destructive HTMX actions (hx-confirm already covers most;
// this is a fallback for elements using data-confirm).
document.body.addEventListener("htmx:confirm", (evt) => {
  const msg = evt.detail.elt.getAttribute("data-confirm");
  if (!msg) return;
  evt.preventDefault();
  if (window.confirm(msg)) evt.detail.issueRequest();
});

// Show a friendly message when the server is rate-limiting or the session expired.
document.body.addEventListener("htmx:responseError", (evt) => {
  const status = evt.detail.xhr.status;
  if (status === 429) {
    alert("Too many requests. Please wait a moment and try again.");
  } else if (status === 401) {
    window.location.href = "/login";
  }
});
