/**
 * AdSynth AI Chatbot Widget
 *
 * Self-contained widget injected into document.body (outside #app) so it
 * persists across hash route changes. Communicates with POST /chat/session
 * and POST /chat/message (SSE stream) using the same JWT auth as the rest of
 * the app.
 */

import { getToken } from "./api.js";

// ── State ─────────────────────────────────────────────────────────────────────

let sessionId = localStorage.getItem("chatbot_session_id") || null;
let isOpen = false;
let isStreaming = false;

// ── DOM injection ─────────────────────────────────────────────────────────────

function injectWidget() {
  const widget = document.createElement("div");
  widget.id = "chatbot-widget";
  widget.innerHTML = `
    <div id="chatbot-bubble" title="AdSynth Assistant" aria-label="Open AI Assistant">💬</div>
    <div id="chatbot-panel" class="chatbot-hidden" role="dialog" aria-label="AI Assistant">
      <div id="chatbot-header">
        <span>AdSynth Assistant</span>
        <button id="chatbot-clear" title="Clear history">Clear</button>
        <button id="chatbot-close" aria-label="Close">✕</button>
      </div>
      <div id="chatbot-context-badge" class="chatbot-hidden"></div>
      <div id="chatbot-messages">
        <div id="chatbot-empty">
          Ask me anything about AdSynth — how-tos, what the AI agents do, or what your results mean.
        </div>
      </div>
      <div id="chatbot-input-row">
        <textarea id="chatbot-input" maxlength="2000" placeholder="Ask about AdSynth…" rows="1"></textarea>
        <button id="chatbot-send">Send</button>
      </div>
    </div>
  `;
  document.body.appendChild(widget);
}

// ── Element helpers ───────────────────────────────────────────────────────────

const el = (id) => document.getElementById(id);

function togglePanel(open) {
  isOpen = open;
  el("chatbot-panel").classList.toggle("chatbot-hidden", !open);
  if (open) el("chatbot-input").focus();
}

// ── Advertisement ID detection ────────────────────────────────────────────────

function getCurrentAdvertisementId() {
  // Hash format: #generate/:campaignId/:adId
  const match = window.location.hash.match(/^#generate\/[^/]+\/([a-f0-9-]{36})/);
  return match ? match[1] : null;
}

// ── Session management ────────────────────────────────────────────────────────

async function ensureSession() {
  if (sessionId) return sessionId;
  const token = getToken();
  if (!token) return null;
  try {
    const res = await fetch("/chat/session", {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` },
    });
    if (!res.ok) return null;
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem("chatbot_session_id", sessionId);
    return sessionId;
  } catch {
    return null;
  }
}

async function clearHistory() {
  const token = getToken();
  if (!token || !sessionId) return;
  try {
    await fetch("/chat/session", {
      method: "DELETE",
      headers: { "Authorization": `Bearer ${token}` },
    });
  } catch { /* ignore */ }
  el("chatbot-messages").innerHTML = `
    <div id="chatbot-empty">History cleared. Ask me anything about AdSynth.</div>
  `;
  updateContextBadge(null);
}

// ── Context badge ─────────────────────────────────────────────────────────────

function updateContextBadge(adId) {
  const badge = el("chatbot-context-badge");
  if (adId) {
    badge.textContent = "📊 Using current ad pipeline as context";
    badge.classList.remove("chatbot-hidden");
  } else {
    badge.classList.add("chatbot-hidden");
  }
}

// ── Message rendering ─────────────────────────────────────────────────────────

function removeEmpty() {
  const empty = document.getElementById("chatbot-empty");
  if (empty) empty.remove();
}

function appendMessage(role, text) {
  removeEmpty();
  const div = document.createElement("div");
  div.className = `chatbot-msg chatbot-msg-${role}`;
  div.textContent = text;
  el("chatbot-messages").appendChild(div);
  scrollToBottom();
  return div;
}

function appendTypingIndicator() {
  removeEmpty();
  const div = document.createElement("div");
  div.className = "chatbot-typing";
  div.id = "chatbot-typing";
  div.innerHTML = "<span></span><span></span><span></span>";
  el("chatbot-messages").appendChild(div);
  scrollToBottom();
  return div;
}

function scrollToBottom() {
  const msgs = el("chatbot-messages");
  msgs.scrollTop = msgs.scrollHeight;
}

// ── Auto-grow textarea ────────────────────────────────────────────────────────

function autoGrow(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = Math.min(textarea.scrollHeight, 96) + "px";
}

// ── Send message ──────────────────────────────────────────────────────────────

async function sendMessage() {
  if (isStreaming) return;
  const input = el("chatbot-input");
  const message = input.value.trim();
  if (!message) return;

  const token = getToken();
  if (!token) {
    appendMessage("error", "Please log in to use the assistant.");
    return;
  }

  const sid = await ensureSession();
  if (!sid) {
    appendMessage("error", "Could not connect to the assistant. Please try again.");
    return;
  }

  const adId = getCurrentAdvertisementId();
  updateContextBadge(adId);

  // Clear input and show user message
  input.value = "";
  input.style.height = "auto";
  appendMessage("user", message);

  // Show typing indicator
  const typing = appendTypingIndicator();
  isStreaming = true;
  el("chatbot-send").disabled = true;

  // Create assistant bubble (filled during streaming)
  let assistantDiv = null;
  let fullText = "";

  try {
    const res = await fetch("/chat/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify({ message, session_id: sid, advertisement_id: adId }),
    });

    if (!res.ok) {
      typing.remove();
      appendMessage("error", `Error ${res.status}: ${res.statusText}`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let evt;
        try { evt = JSON.parse(line.slice(6)); } catch { continue; }

        if (evt.event === "token" && evt.token) {
          if (!assistantDiv) {
            typing.remove();
            assistantDiv = appendMessage("assistant", "");
          }
          fullText += evt.token;
          assistantDiv.textContent = fullText;
          scrollToBottom();
        } else if (evt.event === "error") {
          typing.remove();
          if (assistantDiv) assistantDiv.remove();
          appendMessage("error", evt.message || "An error occurred. Please try again.");
        } else if (evt.event === "done") {
          typing.remove();
          if (!assistantDiv && !fullText) {
            appendMessage("error", "No response received. Please try again.");
          }
        }
      }
    }
  } catch (err) {
    typing.remove();
    if (assistantDiv) assistantDiv.remove();
    appendMessage("error", "Connection error. Please check your network and try again.");
  } finally {
    isStreaming = false;
    el("chatbot-send").disabled = false;
    el("chatbot-input").focus();
  }
}

// ── Event binding ─────────────────────────────────────────────────────────────

function bindEvents() {
  el("chatbot-bubble").addEventListener("click", () => togglePanel(!isOpen));
  el("chatbot-close").addEventListener("click", () => togglePanel(false));
  el("chatbot-clear").addEventListener("click", clearHistory);
  el("chatbot-send").addEventListener("click", sendMessage);

  el("chatbot-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  el("chatbot-input").addEventListener("input", (e) => autoGrow(e.target));
}

// ── Hide widget on auth pages ─────────────────────────────────────────────────

function syncVisibility() {
  const hash = window.location.hash;
  const isAuthPage = hash === "#login" || hash === "#register" || hash === "";
  el("chatbot-widget").style.display = isAuthPage ? "none" : "";
  if (!isAuthPage && getCurrentAdvertisementId()) {
    updateContextBadge(getCurrentAdvertisementId());
  } else if (!isAuthPage) {
    updateContextBadge(null);
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  injectWidget();
  bindEvents();
  syncVisibility();
  window.addEventListener("hashchange", syncVisibility);
});
