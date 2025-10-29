let sessionId = null;
const chatBox = document.getElementById("chatBox");
const input = document.getElementById("questionInput");
const askBtn = document.getElementById("askBtn");
const uploadForm = document.getElementById("uploadForm");
const uploadStatus = document.getElementById("uploadStatus");

function appendMessage(role, text) {
  const div = document.createElement("div");
  div.style.marginBottom = "10px";
  if (role === "user") {
    div.innerHTML = `<div style="text-align:right;"><b>You:</b> ${text}</div>`;
  } else {
    div.innerHTML = `<div style="text-align:left;"><b>HR Bot:</b> ${text}</div>`;
  }
  chatBox.appendChild(div);
  chatBox.scrollTop = chatBox.scrollHeight;
}

askBtn.addEventListener("click", async () => {
  const q = input.value.trim();
  if (!q) return;
  appendMessage("user", q);
  input.value = "";
  const useOpenAI = document.getElementById("useOpenAI").checked;
  const payload = { question: q, session_id: sessionId, use_openai: useOpenAI };
  appendMessage("assistant", "Thinking...");
  // send
  const res = await fetch("/chatbot/chat/query", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const j = await res.json();
  // remove previous 'Thinking...' (last assistant message)
  const items = chatBox.querySelectorAll("div");
  if (items.length) {
    const last = items[items.length - 1];
    if (last.innerText.includes("Thinking")) last.remove();
  }
  if (j.ok) {
    sessionId = j.session_id;
    appendMessage("assistant", j.answer);
  } else {
    appendMessage("assistant", "Error: " + (j.error || "unknown"));
  }
});

uploadForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("fileInput");
  if (!fileInput.files.length) {
    uploadStatus.innerText = "Select a file first.";
    return;
  }
  const f = fileInput.files[0];
  const form = new FormData();
  form.append("file", f);
  form.append("uploader", uploadForm.elements["uploader"].value || "anonymous");
  uploadStatus.innerText = "Uploading...";
  const res = await fetch("/chatbot/chat/upload", {
    method: "POST",
    body: form
  });
  const j = await res.json();
  if (j.ok) {
    uploadStatus.innerText = `Indexed ${j.chunks_indexed} chunks from ${j.source}`;
  } else {
    uploadStatus.innerText = `Upload failed: ${j.error || JSON.stringify(j)}`;
  }
});
