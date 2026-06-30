const messagesEl = document.getElementById("messages");
const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const newChatBtn = document.getElementById("new-chat");

function getSessionId() {
  let id = localStorage.getItem("session_id");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("session_id", id);
  }
  return id;
}

function addMessage(role, text) {
  const el = document.createElement("div");
  el.className = `message ${role}`;
  el.textContent = text;
  messagesEl.appendChild(el);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return el;
}

function addProperties(properties) {
  if (!properties.length) return;

  const wrap = document.createElement("div");
  wrap.className = "properties";

  for (const p of properties) {
    const card = document.createElement("div");
    card.className = "property-card";
    card.innerHTML = `
      <strong>$${p.price.toLocaleString()} · ${p.beds}bd / ${p.baths}ba</strong>
      ${p.address}, ${p.city}, ${p.state}<br>
      ${p.neighborhood} · ${p.property_type}
    `;
    wrap.appendChild(card);
  }

  messagesEl.appendChild(wrap);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

async function streamChat(message) {
  const response = await fetch("/chat/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: getSessionId(), message }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Error ${response.status}`);
  }

  const assistantEl = addMessage("assistant", "Thinking...");
  assistantEl.classList.add("status");
  let hasText = false;
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6));

      if (event.type === "status") {
        assistantEl.textContent = event.content;
        assistantEl.classList.add("status");
        messagesEl.scrollTop = messagesEl.scrollHeight;
      } else if (event.type === "text") {
        if (!hasText) {
          assistantEl.textContent = "";
          assistantEl.classList.remove("status");
          hasText = true;
        }
        assistantEl.textContent += event.content;
        messagesEl.scrollTop = messagesEl.scrollHeight;
      } else if (event.type === "properties") {
        addProperties(event.properties);
      } else if (event.type === "error") {
        throw new Error(event.message);
      }
    }
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  input.value = "";
  input.disabled = true;
  form.querySelector("button").disabled = true;

  addMessage("user", message);

  try {
    await streamChat(message);
  } catch (err) {
    addMessage("assistant", err.message || "Something went wrong.");
  } finally {
    input.disabled = false;
    form.querySelector("button").disabled = false;
    input.focus();
  }
});

newChatBtn.addEventListener("click", () => {
  localStorage.setItem("session_id", crypto.randomUUID());
  messagesEl.innerHTML = "";
  input.focus();
});

input.focus();
