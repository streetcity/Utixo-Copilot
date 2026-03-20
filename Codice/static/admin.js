(function () {
  try {
    const path = window.location.pathname || "";
    document.querySelectorAll(".admin-nav a").forEach((a) => {
      const href = a.getAttribute("href") || "";
      if (!href.startsWith("/admin")) return;
      const isActive = href === "/admin" ? path === "/admin" : path.startsWith(href);
      if (isActive) a.setAttribute("aria-current", "page");
    });
  } catch (_) {}

  document.addEventListener("submit", (e) => {
    const form = e.target;
    if (!(form instanceof HTMLFormElement)) return;

    const btn = form.querySelector("button[type='submit']");
    if (!btn) return;

    if (!btn.classList.contains("admin-btn-primary")) return;

    btn.disabled = true;
    btn.dataset._loading = "1";
    btn.style.opacity = "0.8";
  });
})();