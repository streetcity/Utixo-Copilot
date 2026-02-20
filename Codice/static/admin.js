// Utixo Copilot - Admin UI helpers
// (Keep this file intentionally small and decoupled from the public UI.)

(function () {
  // Highlight active nav (fallback if aria-current isn't set)
  try {
    const path = window.location.pathname || "";
    document.querySelectorAll(".admin-nav a").forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (!href.startsWith("/admin")) return;
      const isActive = href === "/admin" ? path === "/admin" : path.startsWith(href);
      if (isActive) a.setAttribute("aria-current", "page");
    });
  } catch (_) {}

  // Prevent double submit on primary actions
  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;

    const btn = form.querySelector("button[type='submit']");
    if (!btn) return;
    // Only for admin primary save/login to avoid blocking delete confirmations
    if (!btn.classList.contains("admin-btn-primary")) return;

    btn.disabled = true;
    btn.dataset._loading = "1";
    btn.style.opacity = "0.8";
    setTimeout(() => {
      // If the page doesn't navigate for some reason, re-enable
      btn.disabled = false;
      btn.style.opacity = "";
      delete btn.dataset._loading;
    }, 4000);
  });
})();