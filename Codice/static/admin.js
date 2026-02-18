(function () {
  const modal = document.getElementById("editModal");
  const closeBtn = document.getElementById("closeModal");
  const editForm = document.getElementById("editForm");

  function openModal() {
    if (!modal) return;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
  }

  function closeModal() {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
  }

  async function loadFaq(id) {
    const res = await fetch(`/admin/faqs/${id}`, { credentials: "same-origin" });
    if (!res.ok) throw new Error("FAQ load failed");
    const data = await res.json();
    return data.faq;
  }

  function fillForm(faq) {
    document.getElementById("edit_id").value = faq.id;
    document.getElementById("edit_categoria").value = faq.categoria || "generale";
    document.getElementById("edit_domanda").value = faq.domanda || "";
    document.getElementById("edit_risposta1").value = faq.risposta1 || "";
    document.getElementById("edit_risposta2").value = faq.risposta2 || "";
    document.getElementById("edit_risposta3").value = faq.risposta3 || "";
  }

  if (closeBtn) closeBtn.addEventListener("click", (e) => { e.preventDefault(); closeModal(); });
  if (modal) modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  document.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-edit]");
    if (!btn) return;

    const id = btn.getAttribute("data-edit");
    if (!id) return;

    try {
      btn.disabled = true;
      const faq = await loadFaq(id);
      fillForm(faq);
      if (editForm) editForm.setAttribute("action", "/admin/faqs/update");
      openModal();
    } catch (err) {
      alert("Impossibile caricare la FAQ.");
      console.error(err);
    } finally {
      btn.disabled = false;
    }
  });
})();