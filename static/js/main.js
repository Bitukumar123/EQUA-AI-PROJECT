// Generic floating chatbot widget.
// Expects on the page: #bot-toggle, #bot-panel, #bot-log, #bot-form, #bot-input
// and a global CHATBOT_URL string set per-dashboard.
document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.getElementById("bot-toggle");
  const panel = document.getElementById("bot-panel");
  const form = document.getElementById("bot-form");
  const input = document.getElementById("bot-input");
  const log = document.getElementById("bot-log");

  if (!toggle || !panel) return;

  toggle.addEventListener("click", () => panel.classList.toggle("open"));

  if (!form) return;

  function addMsg(role, text) {
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    log.appendChild(div);
    log.scrollTop = log.scrollHeight;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    addMsg("user", message);
    input.value = "";

    try {
      const res = await fetch(window.CHATBOT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const data = await res.json();
      addMsg("assistant", data.reply || "Sorry, something went wrong.");
    } catch (err) {
      addMsg("assistant", "Network error — please try again.");
    }
  });
});
