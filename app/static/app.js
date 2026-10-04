const API = {
  trajectories: "/api/trajectories",
  start: "/api/session/start",
  status: "/api/status",
};

const state = {
  selectedTrajectory: null,
  currentSessionId: null,
  busy: false,
  resultShown: false,
  pollTimer: null,
  resetTimer: null,
  qrCountdownTimer: null,
  pendingCountdownTimer: null,
  pendingCountdownDeadline: null,
};

const modeSelector = document.getElementById("modeSelector");
const captureButton = document.getElementById("captureButton");
const startCountdown = document.getElementById("startCountdown");
const saveStatus = document.getElementById("saveStatus");
const saveStatusText = document.getElementById("saveStatusText");
const qrOverlay = document.getElementById("qrOverlay");
const qrImage = document.getElementById("qrImage");
const qrCountdown = document.getElementById("qrCountdown");
const newVideoButton = document.getElementById("newVideoButton");
const toast = document.getElementById("toast");
const appHiddenWarning = document.getElementById("appHiddenWarning");
const dismissHiddenWarning = document.getElementById("dismissHiddenWarning");
const canvas = document.getElementById("cameraFeed");
const ctx = canvas.getContext("2d", { alpha: false });

let cameraSocket = null;
let reconnectTimer = null;
let cameraPaused = false;

function resizeCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  const w = Math.max(1, Math.round(window.innerWidth * dpr));
  const h = Math.max(1, Math.round(window.innerHeight * dpr));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
}

function drawCover(image, sourceWidth, sourceHeight) {
  resizeCanvas();
  const tw = canvas.width, th = canvas.height;
  const sa = sourceWidth / sourceHeight, ta = tw / th;
  let sx = 0, sy = 0, sw = sourceWidth, sh = sourceHeight;
  if (sa > ta) { sw = sourceHeight * ta; sx = (sourceWidth - sw) / 2; }
  else { sh = sourceWidth / ta; sy = (sourceHeight - sh) / 2; }
  ctx.drawImage(image, sx, sy, sw, sh, 0, 0, tw, th);
}

async function drawJpeg(arrayBuffer) {
  const blob = new Blob([arrayBuffer], { type: "image/jpeg" });
  if ("createImageBitmap" in window) {
    const bitmap = await createImageBitmap(blob);
    try { drawCover(bitmap, bitmap.width, bitmap.height); }
    finally { bitmap.close(); }
    return;
  }
  await new Promise((resolve, reject) => {
    const url = URL.createObjectURL(blob);
    const image = new Image();
    image.onload = () => { try { drawCover(image, image.naturalWidth, image.naturalHeight); resolve(); } finally { URL.revokeObjectURL(url); } };
    image.onerror = () => { URL.revokeObjectURL(url); reject(new Error("JPEG decode failed")); };
    image.src = url;
  });
}

function requestNextCameraFrame() {
  if (!cameraPaused && cameraSocket && cameraSocket.readyState === WebSocket.OPEN) cameraSocket.send("next");
}

function pauseCamera() {
  cameraPaused = true;
  clearTimeout(reconnectTimer);
  if (cameraSocket) { try { cameraSocket.close(); } catch (_) {} cameraSocket = null; }
}

function connectCamera() {
  if (cameraPaused || document.hidden) return;
  clearTimeout(reconnectTimer);
  if (cameraSocket) { try { cameraSocket.close(); } catch (_) {} }
  const scheme = window.location.protocol === "https:" ? "wss" : "ws";
  cameraSocket = new WebSocket(`${scheme}://${window.location.host}/ws/camera`);
  cameraSocket.binaryType = "arraybuffer";
  cameraSocket.onopen = requestNextCameraFrame;
  cameraSocket.onmessage = async (event) => {
    try { if (event.data instanceof ArrayBuffer) await drawJpeg(event.data); }
    catch (error) { console.error("camera frame:", error); }
    finally { requestNextCameraFrame(); }
  };
  cameraSocket.onerror = () => { try { cameraSocket.close(); } catch (_) {} };
  cameraSocket.onclose = () => {
    cameraSocket = null;
    if (!cameraPaused && !document.hidden) reconnectTimer = setTimeout(connectCamera, 1000);
  };
}

function resumeCamera() { cameraPaused = false; connectCamera(); }
window.addEventListener("resize", resizeCanvas);
window.addEventListener("orientationchange", () => setTimeout(resizeCanvas, 150));
let wasHiddenWhileBusy = false;

function handleAppHidden() {
  if (state.busy) wasHiddenWhileBusy = true;
  pauseCamera();
}

function handleAppVisible() {
  if (wasHiddenWhileBusy) {
    appHiddenWarning.classList.remove("hidden");
  }
  if (!state.resultShown) resumeCamera();
}

document.addEventListener("visibilitychange", () => {
  if (document.hidden) handleAppHidden();
  else handleAppVisible();
});
window.addEventListener("pagehide", handleAppHidden);
window.addEventListener("pageshow", () => {
  if (!document.hidden) handleAppVisible();
});

dismissHiddenWarning.addEventListener("click", () => {
  wasHiddenWhileBusy = false;
  appHiddenWarning.classList.add("hidden");
});

async function jsonFetch(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = `${response.status}`;
    try { const body = await response.json(); message = body.detail || body.message || message; }
    catch (_) { try { message = await response.text(); } catch (_) {} }
    throw new Error(message);
  }
  return response.json();
}

function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 2600);
}

async function loadTrajectories() {
  const trajectories = await jsonFetch(API.trajectories);
  modeSelector.innerHTML = "";
  if (!trajectories.length) {
    state.selectedTrajectory = null;
    captureButton.disabled = true;
    showToast("Нет траекторий");
    return;
  }

  trajectories.forEach((trajectory, index) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `mode-btn${index === 0 ? " active" : ""}`;
    button.dataset.trajectory = trajectory.file;
    button.textContent = trajectory.name || trajectory.file.replace(/\.json$/i, "");
    button.addEventListener("click", () => {
      if (state.busy) return;
      document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
      button.classList.add("active");
      state.selectedTrajectory = trajectory.file;
    });
    modeSelector.appendChild(button);
    if (index === 0) state.selectedTrajectory = trajectory.file;
  });
}

function stopPendingCountdown() {
  if (state.pendingCountdownTimer) {
    clearInterval(state.pendingCountdownTimer);
    state.pendingCountdownTimer = null;
  }
  state.pendingCountdownDeadline = null;
}

function renderPendingCountdown() {
  if (!state.pendingCountdownDeadline) return;
  const remainingMs = state.pendingCountdownDeadline - performance.now();
  const value = Math.max(1, Math.ceil(remainingMs / 1000));
  if (startCountdown.textContent !== String(value)) {
    startCountdown.textContent = String(value);
  }
  startCountdown.classList.remove("hidden");
}

function startPendingCountdown(seconds = 5) {
  stopPendingCountdown();
  state.pendingCountdownDeadline = performance.now() + seconds * 1000;
  renderPendingCountdown();
  state.pendingCountdownTimer = setInterval(renderPendingCountdown, 100);
}

function updateStartCountdown(session) {
  const isCurrent = Boolean(state.currentSessionId) && session.session_id === state.currentSessionId;

  if (isCurrent && session.phase === "countdown") {
    stopPendingCountdown();
    const value = String(Math.max(1, session.countdown_remaining || 1));
    if (startCountdown.textContent !== value) {
      startCountdown.textContent = value;
    }
    startCountdown.classList.remove("hidden");
    return;
  }

  // Пока POST /start ещё создаёт публичную папку, не даём pollStatus
  // прятать/показывать таймер каждые 250 мс — именно это давало мерцание.
  if (state.pendingCountdownDeadline && !state.currentSessionId) {
    renderPendingCountdown();
    return;
  }

  if (!isCurrent || session.phase !== "countdown") {
    startCountdown.classList.add("hidden");
  }
}

function updateSaveStatus(session) {
  const phase = session.phase;
  if (phase === "processing") {
    saveStatusText.textContent = "Видео сохраняется…";
    saveStatus.classList.remove("hidden");
    return;
  }
  if (phase === "preparing_share") {
    saveStatusText.textContent = "Генерация QR-кода…";
    saveStatus.classList.remove("hidden");
    return;
  }
  if (phase === "uploading") {
    saveStatusText.textContent = "Загрузка видео…";
    saveStatus.classList.remove("hidden");
    return;
  }
  if (phase === "waiting_upload") {
    saveStatusText.textContent = "Видео сохранено. Ожидаем интернет…";
    saveStatus.classList.remove("hidden");
    return;
  }
  saveStatus.classList.add("hidden");
}

captureButton.addEventListener("click", async () => {
  if (state.busy || !state.selectedTrajectory) return;

  state.busy = true;
  state.resultShown = false;
  state.currentSessionId = null;
  captureButton.disabled = true;
  saveStatus.classList.add("hidden");
  startPendingCountdown(5);

  try {
    const response = await jsonFetch(API.start, {
      method: "POST",
      body: JSON.stringify({ trajectory: state.selectedTrajectory }),
    });
    state.currentSessionId = response.session_id;
  } catch (error) {
    stopPendingCountdown();
    state.busy = false;
    captureButton.disabled = false;
    startCountdown.classList.add("hidden");
    showToast(error.message || "Не удалось запустить съёмку");
  }
});

function startQrCountdown() {
  clearInterval(state.qrCountdownTimer);
  clearTimeout(state.resetTimer);
  let value = 30;
  qrCountdown.textContent = String(value);
  state.qrCountdownTimer = setInterval(() => {
    value -= 1;
    qrCountdown.textContent = String(Math.max(0, value));
    if (value <= 0) { clearInterval(state.qrCountdownTimer); state.qrCountdownTimer = null; }
  }, 1000);
  state.resetTimer = setTimeout(resetUi, 30000);
}

function showQr(sessionId) {
  stopPendingCountdown();
  state.resultShown = true;
  state.busy = false;
  startCountdown.classList.add("hidden");
  saveStatus.classList.add("hidden");
  captureButton.disabled = false;
  captureButton.classList.remove("recording");
  qrOverlay.classList.remove("hidden");
  pauseCamera();

  let qrAttempts = 0;
  const loadQr = () => {
    qrAttempts += 1;
    qrImage.src = `/api/session/${encodeURIComponent(sessionId)}/qr?t=${Date.now()}`;
  };

  qrImage.onload = () => {
    qrImage.onload = null;
    qrImage.onerror = null;
    startQrCountdown();
  };

  qrImage.onerror = () => {
    if (qrAttempts < 10) {
      setTimeout(loadQr, 500);
      return;
    }
    qrImage.onload = null;
    qrImage.onerror = null;
    showToast("Не удалось загрузить QR-код");
  };

  loadQr();
}

function resetUi() {
  stopPendingCountdown();
  clearInterval(state.qrCountdownTimer);
  clearTimeout(state.resetTimer);
  state.qrCountdownTimer = null;
  state.resetTimer = null;
  state.resultShown = false;
  state.busy = false;
  state.currentSessionId = null;
  startCountdown.classList.add("hidden");
  saveStatus.classList.add("hidden");
  captureButton.disabled = !state.selectedTrajectory;
  captureButton.classList.remove("recording");
  qrOverlay.classList.add("hidden");
  qrImage.removeAttribute("src");
  resumeCamera();
}

newVideoButton.addEventListener("click", resetUi);

async function pollStatus() {
  try {
    const data = await jsonFetch(API.status);
    const session = data.session || {};

    updateStartCountdown(session);

    const isCurrent = Boolean(state.currentSessionId) && session.session_id === state.currentSessionId;
    if (!isCurrent) return;

    updateSaveStatus(session);

    const busyPhase = ["countdown", "recording", "processing", "preparing_share", "uploading", "waiting_upload"].includes(session.phase);
    if (busyPhase) {
      state.busy = true;
      captureButton.disabled = true;
      captureButton.classList.toggle("recording", session.phase === "recording");
    }

    if (session.phase === "done" && session.success && session.local_ready && session.share_url && !state.resultShown) {
      showQr(session.session_id);
      return;
    }

    if (session.phase === "error") {
      stopPendingCountdown();
      state.busy = false;
      state.currentSessionId = null;
      startCountdown.classList.add("hidden");
      saveStatus.classList.add("hidden");
      captureButton.disabled = !state.selectedTrajectory;
      captureButton.classList.remove("recording");
      showToast(session.error || "Съёмка не завершена");
    }
  } catch (error) {
    console.error(error);
  }
}

(async () => {
  resizeCanvas();
  connectCamera();
  try { await loadTrajectories(); }
  catch (error) { showToast(error.message || "Ошибка запуска интерфейса"); }
  state.pollTimer = setInterval(pollStatus, 250);
})();
