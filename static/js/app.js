// Simple client to test login + realtime via Socket.IO
let API_BASE = "";

// Login form handler
async function doLogin(evt) {
  evt.preventDefault();
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({email, password})
  });
  const data = await res.json();
  if (res.ok) {
    localStorage.setItem("token", data.access_token);
    document.getElementById("loginStatus").textContent = "Login OK";
  } else {
    document.getElementById("loginStatus").textContent = "Falhou: " + (data.error || "erro");
  }
}

// Connect Socket.IO and listen to events
function connectSocket() {
  const token = localStorage.getItem("token");
  const socket = io({transports: ["websocket"]});
  window._socket = socket;

  socket.on("connect", () => {
    console.log("socket connected", socket.id);
    addLog("Socket conectado: " + socket.id);
  });

  // Join a process room
  document.getElementById("joinBtn").onclick = () => {
    const procId = document.getElementById("procId").value;
    socket.emit("join_procurement", {procurement_id: parseInt(procId)});
    addLog("Entrou na sala do processo " + procId);
  };

  // Common events
  ["procurement.created","invite.sent","tr.saved","tr.submitted","proposal.tech.received","proposal.comm.received"]
    .forEach(ev => socket.on(ev, (payload) => addLog(ev + " → " + JSON.stringify(payload))));
}

function addLog(text) {
  const ul = document.getElementById("log");
  const li = document.createElement("li");
  li.textContent = text;
  ul.prepend(li);
}

window.addEventListener("DOMContentLoaded", () => {
  document.getElementById("loginForm").addEventListener("submit", doLogin);
  connectSocket();
});
