// =========================
// Utixo Copilot UI (drawer)
// + Auth + Conversations
// =========================

const body = document.body;

// Drawer elements
const backdrop = document.getElementById("backdrop");
const floatingBtn = document.getElementById("floatingChatButton");
const closeBtn = document.getElementById("closeChatDrawer");
const openChatButtons = document.querySelectorAll(".openChatBtn");

// Chat elements
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const inputEl = document.getElementById("userInput");

// Tools / conversations
const newChatBtn = document.getElementById("newChatBtn");
const openTicketBtn = document.getElementById("openTicketBtn");
const conversationsPane = document.getElementById("conversationsPane");
const conversationsList = document.getElementById("conversationsList");
const chatLoginHint = document.getElementById("chatLoginHint");
const chatLayout = document.querySelector(".chat-layout");

// Auth UI
const loginBtn = document.getElementById("loginBtn");
const registerBtn = document.getElementById("registerBtn");
const userMenu = document.getElementById("userMenu");
const userMenuBtn = document.getElementById("userMenuBtn");
const userMenuDropdown = document.getElementById("userMenuDropdown");
const usernameLabel = document.getElementById("usernameLabel");
const openChatsBtn = document.getElementById("openChatsBtn");
const logoutBtn = document.getElementById("logoutBtn");

// Modals
const modalBackdrop = document.getElementById("modalBackdrop");
const loginModal = document.getElementById("loginModal");
const registerModal = document.getElementById("registerModal");
const loginForm = document.getElementById("loginForm");
const registerForm = document.getElementById("registerForm");
const loginError = document.getElementById("loginError");
const registerError = document.getElementById("registerError");

let currentUser = null;              // {id, username}
let currentConversationId = null;    // number | null

function openChat() {
  body.classList.add("chat-open");
  setTimeout(() => inputEl?.focus(), 50);

  if (currentUser) {
    showConversationsPane(true);
    refreshConversations().catch(() => {});
  } else {
    showConversationsPane(false);
  }
}

function closeChat() {
  body.classList.remove("chat-open");
  userMenuDropdown?.classList.add("hidden");
}

if (floatingBtn) floatingBtn.addEventListener("click", openChat);
if (closeBtn) closeBtn.addEventListener("click", closeChat);
if (backdrop) backdrop.addEventListener("click", closeChat);

openChatButtons.forEach((btn) => {
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    openChat();
  });
});

// Dark mode toggle
const themeToggle = document.getElementById("themeToggle");
if (themeToggle) {
  themeToggle.addEventListener("click", () => {
    body.classList.toggle("dark");
  });
}

// =========================
// Utilities
// =========================
function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function appendBubble(text, who = "bot", extraClass = "") {
  if (!messagesEl) return null;
  const div = document.createElement("div");
  div.className = `chat-bubble ${who} ${extraClass}`.trim();
  div.innerHTML = escapeHtml(text).replaceAll("\n", "<br>");
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return div;
}

function appendBotMessage(text, meta = {}) {
  const div = appendBubble(text, "bot");
  if (!div) return null;

  // Suggestions (quick replies) for clarification
  const suggestions = Array.isArray(meta.suggestions) ? meta.suggestions : [];
  if (meta.need_clarification && suggestions.length > 0) {
    const sWrap = document.createElement("div");
    sWrap.className = "bubble-actions bubble-suggestions";

    suggestions.slice(0, 3).forEach((s, idx) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "action-btn suggestion-btn";

      const num = document.createElement("span");
      num.className = "suggestion-num";
      num.textContent = `${idx + 1}`;

      const label = document.createElement("span");
      label.className = "suggestion-label";
      const raw = (s.domanda || "").trim();
      const truncated = raw.length > 64 ? raw.slice(0, 61) + "…" : raw;
      label.textContent = truncated || "Opzione";

      btn.appendChild(num);
      btn.appendChild(label);

      btn.addEventListener("click", () => {
        // invia il testo della FAQ suggerita (più robusto del solo numero)
        sendMessage((s.domanda || "").trim());
      });
      sWrap.appendChild(btn);
    });

    div.appendChild(sWrap);
  }

  // Feedback buttons
  if (meta.log_id) {
    const fWrap = document.createElement("div");
    fWrap.className = "bubble-actions bubble-feedback";

    const up = document.createElement("button");
    up.type = "button";
    up.className = "action-btn";
    up.textContent = "Utile";
    up.title = "Utile";

    const down = document.createElement("button");
    down.type = "button";
    down.className = "action-btn";
    down.textContent = "Non utile";
    down.title = "Non utile";

    const lock = () => {
      up.disabled = true;
      down.disabled = true;
      up.classList.add("disabled");
      down.classList.add("disabled");
    };

    const sendFb = async (value) => {
      try {
        await apiFetchJson("/feedback", {
          method: "POST",
          body: JSON.stringify({ log_id: meta.log_id, value }),
        });
        lock();
      } catch (_) {
        // non bloccare UI per errori feedback
        lock();
      }
    };

    up.addEventListener("click", () => sendFb(1));
    down.addEventListener("click", () => sendFb(-1));

    fWrap.appendChild(up);
    fWrap.appendChild(down);
    div.appendChild(fWrap);
  }

  return div;
}

function clearMessages() {
  messagesEl && (messagesEl.innerHTML = "");
}

function showGreeting() {
  if (!messagesEl) return;
  if (messagesEl.childElementCount === 0) {
    appendBubble("Ciao! Sono l’Utixo Copilot. Come posso aiutarti?", "bot");
  }
}

function setError(el, msg) {
  if (!el) return;
  if (!msg) {
    el.textContent = "";
    el.classList.add("hidden");
    return;
  }
  el.textContent = msg;
  el.classList.remove("hidden");
}

async function apiFetchJson(url, opts = {}) {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(opts.headers || {}) },
    ...opts,
  });

  let data = null;
  try { data = await res.json(); } catch (_) {}

  if (!res.ok) {
    const errMsg =
      (data && (data.error || data.message)) ? (data.error || data.message)
      : `Errore HTTP ${res.status}`;
    const err = new Error(errMsg);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}



// =========================
// Ticket (WHMCS)
// =========================
const TICKET_URL = (window.UTIXO_TICKET_URL || "").trim();

// Apri il form ticket senza pre-compilare nulla con i contenuti della chat.
openTicketBtn?.addEventListener("click", () => {
  if (!TICKET_URL) {
    alert("Ticket URL non configurato.");
    return;
  }
  window.open(TICKET_URL, "_blank", "noopener");
});

// =========================
// Auth + UI
// =========================
function updateChatLayout() {
  if (!chatLayout) return;
  const noConversations = conversationsPane?.classList.contains("hidden") || !currentUser;
  chatLayout.classList.toggle("no-conversations", !!noConversations);
}

function showConversationsPane(show) {
  if (!conversationsPane) return;
  conversationsPane.classList.toggle("hidden", !show);
  updateChatLayout();
}

function setAuthUI(user) {
  currentUser = user || null;
  const isLogged = !!currentUser;

  loginBtn?.classList.toggle("hidden", isLogged);
  registerBtn?.classList.toggle("hidden", isLogged);

  userMenu?.classList.toggle("hidden", !isLogged);
  if (usernameLabel) usernameLabel.textContent = isLogged ? (currentUser.username || "utente") : "utente";

  chatLoginHint?.classList.toggle("hidden", isLogged);

  showConversationsPane(isLogged);
  updateChatLayout();
}

async function refreshMe() {
  try {
    const data = await apiFetchJson("/auth/me", { method: "GET" });
    setAuthUI(data.user || null);
  } catch (e) {
    setAuthUI(null);
  }
}

function openModal(modalEl) {
  if (!modalEl || !modalBackdrop) return;
  modalBackdrop.classList.remove("hidden");
  modalEl.classList.remove("hidden");
  modalBackdrop.setAttribute("aria-hidden", "false");
  setTimeout(() => modalEl.querySelector("input")?.focus(), 30);
}

function closeModal(modalEl) {
  if (!modalEl || !modalBackdrop) return;
  modalEl.classList.add("hidden");
  modalBackdrop.classList.add("hidden");
  modalBackdrop.setAttribute("aria-hidden", "true");
}

function closeAnyModal() {
  closeModal(loginModal);
  closeModal(registerModal);
}

modalBackdrop?.addEventListener("click", closeAnyModal);

document.querySelectorAll("[data-close-modal]").forEach((btn) => {
  btn.addEventListener("click", () => {
    const id = btn.getAttribute("data-close-modal");
    if (id === "loginModal") closeModal(loginModal);
    if (id === "registerModal") closeModal(registerModal);
  });
});

loginBtn?.addEventListener("click", () => openModal(loginModal));
registerBtn?.addEventListener("click", () => openModal(registerModal));

userMenuBtn?.addEventListener("click", (e) => {
  e.stopPropagation();
  userMenuDropdown?.classList.toggle("hidden");
});

document.addEventListener("click", () => userMenuDropdown?.classList.add("hidden"));

logoutBtn?.addEventListener("click", async () => {
  try {
    await apiFetchJson("/auth/logout", { method: "POST", body: "{}" });
  } catch (_) {}

  currentConversationId = null;
  setAuthUI(null);
  clearMessages();
  showGreeting();
});

openChatsBtn?.addEventListener("click", () => {
  openChat();
});

// Login submit
loginForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setError(loginError, "");

  const username = (document.getElementById("loginUsername")?.value || "").trim();
  const password = (document.getElementById("loginPassword")?.value || "").trim();

  try {
    const data = await apiFetchJson("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });

    closeModal(loginModal);
    setAuthUI(data.user);

    await refreshConversations();
    openChat();

    currentConversationId = null;
    clearMessages();
    showGreeting();
  } catch (err) {
    setError(loginError, err.message || "Errore login.");
  }
});

// Register submit
registerForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setError(registerError, "");

  const username = (document.getElementById("registerUsername")?.value || "").trim();
  const email = (document.getElementById("registerEmail")?.value || "").trim();
  const password = (document.getElementById("registerPassword")?.value || "").trim();

  try {
    const data = await apiFetchJson("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, password, email: email || null }),
    });

    closeModal(registerModal);
    setAuthUI(data.user);

    await refreshConversations();
    openChat();

    currentConversationId = null;
    clearMessages();
    showGreeting();
  } catch (err) {
    setError(registerError, err.message || "Errore registrazione.");
  }
});

// =========================
// Conversations
// =========================
function renderConversations(items) {
  if (!conversationsList) return;
  conversationsList.innerHTML = "";

  if (!items || items.length === 0) {
    const empty = document.createElement("div");
    empty.className = "conv-empty";
    empty.textContent = "Nessuna chat salvata.";
    conversationsList.appendChild(empty);
    return;
  }

  items.forEach((c) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "conv-item" + (String(c.id) === String(currentConversationId) ? " active" : "");
    btn.dataset.conversationId = c.id;
    btn.innerHTML = `
      <div class="conv-title">${escapeHtml(c.title || "Chat")}</div>
      <div class="conv-meta">${escapeHtml(String(c.updated_at || c.created_at || ""))}</div>
    `;
    btn.addEventListener("click", async () => {
      currentConversationId = Number(c.id);
      await loadConversation(currentConversationId);
      document.querySelectorAll(".conv-item").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
    });
    conversationsList.appendChild(btn);
  });
}

async function fetchConversations() {
  const data = await apiFetchJson("/api/conversations", { method: "GET" });
  return data.conversations || [];
}

async function refreshConversations() {
  if (!currentUser) return;
  const items = await fetchConversations();
  renderConversations(items);
}

async function loadConversation(conversationId) {
  if (!conversationId) return;

  // Il backend espone i messaggi su /api/conversations/<id>/messages.
  // Per compatibilità, se fallisce proviamo anche /api/conversations/<id> (che in alcune versioni include messages).
  let data = null;
  try {
    data = await apiFetchJson(`/api/conversations/${conversationId}/messages`, { method: "GET" });
  } catch (e) {
    data = await apiFetchJson(`/api/conversations/${conversationId}`, { method: "GET" });
  }

  clearMessages();
  const messages = (data && data.messages) ? data.messages : [];
  if (messages.length === 0) {
    showGreeting();
    return;
  }

  messages.forEach((m) => {
    const who = m.role === "user" ? "user" : "bot";
    appendBubble(m.content || "", who);
  });
}
async function createConversationIfNeeded() {
  if (!currentUser) return null;

  // Se non c'è conversazione corrente, la creiamo SOLO quando inviamo un messaggio (non quando clicchiamo "Nuova chat")
  if (currentConversationId) return currentConversationId;

  const data = await apiFetchJson("/api/conversations", {
    method: "POST",
    body: JSON.stringify({ title: "Nuova chat" }),
  });

  currentConversationId = data.conversation_id || null;
  await refreshConversations();
  return currentConversationId;
}

newChatBtn?.addEventListener("click", async () => {
  // non creare nel DB qui: reset UI e basta
  currentConversationId = null;
  clearMessages();
  showGreeting();

  // UI: deseleziona in lista
  document.querySelectorAll(".conv-item").forEach((x) => x.classList.remove("active"));
});

// =========================
// Chat send
// =========================
async function sendMessage(text) {
  const msg = (text || "").trim();
  if (!msg) return;

  appendBubble(msg, "user");
  inputEl && (inputEl.value = "");

  // show typing bubble
  const typing = appendBubble("…", "bot", "typing");

  try {
    let convoId = currentConversationId;

    // se loggato, crea conversazione SOLO al primo invio
    if (currentUser && !convoId) {
      convoId = await createConversationIfNeeded();
    }

    const payload = {
      message: msg,
      conversation_id: convoId || null,
    };

    const data = await apiFetchJson("/ask", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    typing && typing.remove();
    appendBotMessage(data.reply || "Nessuna risposta.", {
      log_id: data.log_id || null,
      need_clarification: !!data.need_clarification,
      suggestions: data.suggestions || [],
    });

    // se per qualche motivo il backend assegna un conversation_id (es. prima chat), prendilo
    if (!currentConversationId && data.conversation_id) {
      currentConversationId = Number(data.conversation_id);
      await refreshConversations();

      // seleziona la conversazione appena creata
      const btn = conversationsList?.querySelector(`[data-conversation-id="${currentConversationId}"]`);
      btn?.classList.add("active");
    }
  } catch (err) {
    typing && typing.remove();
    appendBubble(`Errore: ${err.message || "impossibile inviare."}`, "bot");
  }
}

chatForm?.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage(inputEl ? inputEl.value : "");
});

inputEl?.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    chatForm?.requestSubmit();
  }
});

// Init
(async function init() {
  await refreshMe();
  updateChatLayout();
  showGreeting();
  if (currentUser) {
    await refreshConversations();
  }
})();