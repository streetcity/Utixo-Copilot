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
const sendBtn = document.getElementById("sendBtn");

// Tools / conversations
const newChatBtn = document.getElementById("newChatBtn");
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
  div.innerHTML = escapeHtml(text);
  messagesEl.appendChild(div);
  messagesEl.scrollTop = messagesEl.scrollHeight;
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
  if (!currentUser) return;

  clearMessages();

  const data = await apiFetchJson(`/api/conversations/${conversationId}/messages`, { method: "GET" });
  const rows = data.messages || [];

  if (rows.length === 0) {
    showGreeting();
    return;
  }

  rows.forEach((r) => {
    if (r.messaggio_utente) appendBubble(r.messaggio_utente, "user");
    if (r.risposta_bot) appendBubble(r.risposta_bot, "bot");
  });
}

// Nuova chat (solo reset UI, NON crea record)
newChatBtn?.addEventListener("click", async () => {
  currentConversationId = null;
  clearMessages();
  showGreeting();
  document.querySelectorAll(".conv-item").forEach((x) => x.classList.remove("active"));
});

// =========================
// Chat send
// =========================
async function sendMessage(message) {
  if (!message || !message.trim()) return;

  appendBubble(message, "user");
  if (inputEl) inputEl.value = "";

  const typing = appendBubble("Sto scrivendo…", "bot", "meta");

  sendBtn && (sendBtn.disabled = true);
  inputEl && (inputEl.disabled = true);

  try {
    const payload = { message: message };
    if (currentUser) {
      payload.conversation_id = currentConversationId; // null => backend crea al primo msg
    }

    // ✅ FIX: endpoint corretto è /chat (non /message)
    const data = await apiFetchJson("/chat", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    typing && typing.remove();
    appendBubble(data.reply ?? "Nessuna risposta dal server.", "bot");

    if (currentUser) {
      if (data.conversation_id && !currentConversationId) {
        currentConversationId = Number(data.conversation_id);
      }
      await refreshConversations();

      if (currentConversationId) {
        document.querySelectorAll(".conv-item").forEach((x) => {
          x.classList.toggle("active", String(x.dataset.conversationId) === String(currentConversationId));
        });
      }
    }
  } catch (err) {
    typing && typing.remove();
    if (err?.status === 404) {
      appendBubble("Endpoint non trovato (404). Controlla che il backend esponga /chat.", "bot");
    } else {
      appendBubble("Errore di connessione al server. Riprova tra poco.", "bot");
    }
    console.error(err);
  } finally {
    sendBtn && (sendBtn.disabled = false);
    inputEl && (inputEl.disabled = false);
    inputEl && inputEl.focus();
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