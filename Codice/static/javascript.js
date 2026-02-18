// =========================
// Utixo Copilot UI (drawer)
// =========================

const body = document.body;

const backdrop = document.getElementById("backdrop");
const floatingBtn = document.getElementById("floatingChatButton");
const closeBtn = document.getElementById("closeChatDrawer");
const openChatButtons = document.querySelectorAll(".openChatBtn");

function openChat() {
  body.classList.add("chat-open");
  const input = document.getElementById("userInput");
  if (input) setTimeout(() => input.focus(), 50);
}
function closeChat() {
  body.classList.remove("chat-open");
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
// Chat logic (talk to Flask)
// =========================
const messagesEl = document.getElementById("messages");
const chatForm = document.getElementById("chatForm");
const inputEl = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");

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

// Greeting (una sola volta)
if (messagesEl && messagesEl.childElementCount === 0) {
  appendBubble("Ciao! Sono l’Utixo Copilot. Come posso aiutarti?", "bot");
}

async function sendMessage(message) {
  if (!message || !message.trim()) return;

  appendBubble(message, "user");
  if (inputEl) inputEl.value = "";

  const typing = appendBubble("Sto scrivendo…", "bot", "meta");

  if (sendBtn) sendBtn.disabled = true;
  if (inputEl) inputEl.disabled = true;

  try {
    const res = await fetch("/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (typing) typing.remove();

    appendBubble(data.reply ?? "Nessuna risposta dal server.", "bot");
  } catch (err) {
    if (typing) typing.remove();
    appendBubble("Errore di connessione al server. Riprova tra poco.", "bot");
    console.error(err);
  } finally {
    if (sendBtn) sendBtn.disabled = false;
    if (inputEl) inputEl.disabled = false;
    if (inputEl) inputEl.focus();
  }
}

if (chatForm) {
  chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const msg = inputEl ? inputEl.value : "";
    sendMessage(msg);
  });
}

if (inputEl) {
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (chatForm) chatForm.requestSubmit();
      else sendMessage(inputEl.value);
    }
  });
}