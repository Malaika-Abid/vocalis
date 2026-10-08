// -------------------------------------------------------------
// Streamlit Component Bridge & Ready Handshake
// -------------------------------------------------------------
const inIframe = window.parent !== window;

function sendToStreamlit(type, payload = {}) {
  if (inIframe) {
    window.parent.postMessage(
      {
        isStreamlitMessage: true,
        type: type,
        ...payload,
      },
      "*"
    );
  }
}

function updateFrameHeight() {
  const height = Math.max(
    document.documentElement.scrollHeight || 0,
    document.body.scrollHeight || 0,
    window.innerHeight || 0,
    1150
  );
  sendToStreamlit("streamlit:setFrameHeight", { height: height });
}

// Notify Streamlit that component is mounted
sendToStreamlit("streamlit:componentReady", { apiVersion: 1 });
window.addEventListener("load", () => {
  updateFrameHeight();
  setTimeout(updateFrameHeight, 300);
});
window.addEventListener("resize", updateFrameHeight);
setInterval(updateFrameHeight, 1500);

// Auto-redirect 0.0.0.0 to localhost so browsers recognize it as a Secure Context for microphone access
if (window.location.hostname === "0.0.0.0") {
  window.location.href = window.location.href.replace("0.0.0.0", "localhost");
}

let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let analyserNode = null;
let isRecording = false;
let recordedBuffers = [];
let recordingStartTime = 0;
let timerInterval = null;
let currentAudioBlob = null;
let currentAudioUrl = null;
let visualizerAnimId = null;

// Tab Switching
function switchTab(tab) {
  document.getElementById("tab-record-btn").classList.toggle("active", tab === "record");
  document.getElementById("tab-upload-btn").classList.toggle("active", tab === "upload");
  document.getElementById("panel-record").classList.toggle("active", tab === "record");
  document.getElementById("panel-upload").classList.toggle("active", tab === "upload");
  setTimeout(updateFrameHeight, 100);
}

// -------------------------------------------------------------
// Live Recording via Web Audio API & In-Browser WAV Encoding
// -------------------------------------------------------------
const recordToggleBtn = document.getElementById("record-toggle-btn");
const micIcon = document.getElementById("mic-icon");
const stopIcon = document.getElementById("stop-icon");
const recordTimer = document.getElementById("record-timer");
const recordStatus = document.getElementById("record-status");
const analyzeRecordedBtn = document.getElementById("analyze-recorded-btn");
const visualizerCanvas = document.getElementById("live-visualizer");
const vCtx = visualizerCanvas.getContext("2d");

recordToggleBtn.addEventListener("click", async () => {
  if (!isRecording) {
    await startRecording();
  } else {
    stopRecording();
  }
});

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert(
      "Microphone access is blocked because the URL is not a Secure Context.\n\n" +
      "Please open the app using an HTTPS link or localhost.\n\n" +
      "(Browsers block microphone permissions on insecure origins)"
    );
    return;
  }

  try {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    audioContext = new AudioContextClass({ sampleRate: 16000 });
    
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: false,
      },
    });

    const source = audioContext.createMediaStreamSource(mediaStream);
    analyserNode = audioContext.createAnalyser();
    analyserNode.fftSize = 256;
    source.connect(analyserNode);

    // Buffer collection
    recordedBuffers = [];
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    scriptProcessor.onaudioprocess = (e) => {
      if (!isRecording) return;
      const channel = e.inputBuffer.getChannelData(0);
      recordedBuffers.push(new Float32Array(channel));
    };
    source.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    isRecording = true;
    recordingStartTime = Date.now();
    recordToggleBtn.classList.add("recording");
    micIcon.style.display = "none";
    stopIcon.style.display = "block";
    recordStatus.textContent = "Listening & recording speech... Click to finish.";
    analyzeRecordedBtn.disabled = true;

    // Timer
    timerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, "0");
      const secs = String(elapsed % 60).padStart(2, "0");
      recordTimer.textContent = `${mins}:${secs}`;
    }, 200);

    drawLiveVisualizer();
  } catch (err) {
    console.error("Microphone access error:", err);
    alert("Microphone access was denied or is unavailable. Please check browser permissions: " + err.message);
  }
}

function stopRecording() {
  if (!isRecording) return;
  isRecording = false;

  clearInterval(timerInterval);
  cancelAnimationFrame(visualizerAnimId);

  recordToggleBtn.classList.remove("recording");
  micIcon.style.display = "block";
  stopIcon.style.display = "none";
  recordStatus.textContent = "Recording ready! Click Analyze below.";

  // Stop media tracks
  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }
  if (scriptProcessor) {
    scriptProcessor.disconnect();
  }

  // Encode to 16-bit PCM WAV
  const wavBlob = encodePCM16Wav(recordedBuffers, audioContext.sampleRate || 16000);
  currentAudioBlob = wavBlob;
  
  if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
  currentAudioUrl = URL.createObjectURL(wavBlob);

  analyzeRecordedBtn.disabled = false;
  drawFlatVisualizer();
}

function drawLiveVisualizer() {
  if (!isRecording || !analyserNode) return;
  visualizerAnimId = requestAnimationFrame(drawLiveVisualizer);

  const bufferLength = analyserNode.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  analyserNode.getByteFrequencyData(dataArray);

  vCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
  const barWidth = (visualizerCanvas.width / bufferLength) * 2.2;
  let x = 0;

  for (let i = 0; i < bufferLength; i++) {
    const barHeight = (dataArray[i] / 255) * visualizerCanvas.height;
    const gradient = vCtx.createLinearGradient(0, visualizerCanvas.height, 0, 0);
    gradient.addColorStop(0, "#3b82f6");
    gradient.addColorStop(1, "#8b5cf6");

    vCtx.fillStyle = gradient;
    vCtx.fillRect(x, visualizerCanvas.height - barHeight, barWidth - 1, barHeight);
    x += barWidth;
  }
}

function drawFlatVisualizer() {
  vCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
  vCtx.strokeStyle = "rgba(59, 130, 246, 0.4)";
  vCtx.lineWidth = 2;
  vCtx.beginPath();
  vCtx.moveTo(0, visualizerCanvas.height / 2);
  vCtx.lineTo(visualizerCanvas.width, visualizerCanvas.height / 2);
  vCtx.stroke();
}

// Standard 16-bit PCM WAV Encoder
function encodePCM16Wav(buffers, sampleRate) {
  let totalLength = 0;
  for (const b of buffers) totalLength += b.length;

  const merged = new Float32Array(totalLength);
  let offset = 0;
  for (const b of buffers) {
    merged.set(b, offset);
    offset += b.length;
  }

  const buffer = new ArrayBuffer(44 + totalLength * 2);
  const view = new DataView(buffer);

  function writeStr(offset, str) {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  }

  writeStr(0, "RIFF");
  view.setUint32(4, 36 + totalLength * 2, true);
  writeStr(8, "WAVE");
  writeStr(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeStr(36, "data");
  view.setUint32(40, totalLength * 2, true);

  let p = 44;
  for (let i = 0; i < totalLength; i++) {
    const s = Math.max(-1, Math.min(1, merged[i]));
    view.setInt16(p, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    p += 2;
  }

  return new Blob([view], { type: "audio/wav" });
}

// Helper: Blob to Base64
function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const parts = reader.result.split(",");
      resolve(parts[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

// -------------------------------------------------------------
// File Upload Dropzone
// -------------------------------------------------------------
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("audio-file-input");
const fileSelectedInfo = document.getElementById("file-selected-info");
const analyzeUploadBtn = document.getElementById("analyze-upload-btn");
let uploadedFile = null;

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => {
  if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("dragover");
});

dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));

dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("dragover");
  if (e.dataTransfer.files.length > 0) handleFile(e.dataTransfer.files[0]);
});

function handleFile(file) {
  uploadedFile = file;
  fileSelectedInfo.style.display = "flex";
  fileSelectedInfo.textContent = `Selected: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
  analyzeUploadBtn.disabled = false;

  if (currentAudioUrl) URL.revokeObjectURL(currentAudioUrl);
  currentAudioUrl = URL.createObjectURL(file);
}

// -------------------------------------------------------------
// Analysis Requests
// -------------------------------------------------------------
analyzeRecordedBtn.addEventListener("click", () => {
  if (currentAudioBlob) {
    sendAudioForAnalysis(currentAudioBlob, "recording.wav");
  }
});

analyzeUploadBtn.addEventListener("click", () => {
  if (uploadedFile) {
    sendAudioForAnalysis(uploadedFile, uploadedFile.name);
  }
});

document.getElementById("try-sample-btn").addEventListener("click", async () => {
  showLoading();
  if (inIframe) {
    sendToStreamlit("streamlit:setComponentValue", {
      value: {
        action: "sample",
        req_id: Date.now() + Math.random(),
      },
      apiVersion: 1,
    });
  } else {
    try {
      const res = await fetch("/api/sample");
      if (!res.ok) throw new Error("Sample analysis failed");
      const data = await res.json();
      currentAudioUrl = "sample_test.wav";
      renderResults(data);
    } catch (err) {
      console.error(err);
      alert("Failed to analyze sample: " + err.message);
      hideLoading();
    }
  }
});

async function sendAudioForAnalysis(blobOrFile, filename) {
  showLoading();
  try {
    if (inIframe) {
      const b64 = await blobToBase64(blobOrFile);
      sendToStreamlit("streamlit:setComponentValue", {
        value: {
          action: "analyze",
          audio_b64: b64,
          filename: filename,
          req_id: Date.now() + Math.random(),
        },
        apiVersion: 1,
      });
    } else {
      const formData = new FormData();
      formData.append("file", blobOrFile, filename);

      const res = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Server returned ${res.status}`);
      }

      const data = await res.json();
      renderResults(data);
    }
  } catch (err) {
    console.error("Analysis error:", err);
    alert("Analysis failed: " + err.message);
    hideLoading();
  }
}

// -------------------------------------------------------------
// Streamlit Inbound Message Listener
// -------------------------------------------------------------
window.addEventListener("message", (event) => {
  if (!event.data) return;
  if (event.data.type === "streamlit:render") {
    const args = event.data.args;
    if (!args) return;

    if (args.error) {
      alert("Analysis error: " + args.error);
      hideLoading();
      return;
    }

    if (args.result) {
      if (args.audio_b64) {
        currentAudioUrl = "data:audio/wav;base64," + args.audio_b64;
      }
      renderResults(args.result);
      setTimeout(updateFrameHeight, 200);
    }
  }
});

// -------------------------------------------------------------
// Render Results
// -------------------------------------------------------------
const emptyState = document.getElementById("empty-state");
const loadingState = document.getElementById("loading-state");
const resultsContent = document.getElementById("results-content");
const audioPlayer = document.getElementById("audio-player");

function showLoading() {
  emptyState.style.display = "none";
  resultsContent.style.display = "none";
  loadingState.style.display = "flex";
  updateFrameHeight();
}

function hideLoading() {
  loadingState.style.display = "none";
  updateFrameHeight();
}

function renderResults(data) {
  loadingState.style.display = "none";
  emptyState.style.display = "none";
  resultsContent.style.display = "flex";

  const c = data.characteristics;

  // 1. Plain ASCII Card
  document.getElementById("ascii-card-text").textContent = data.formatted_card;

  // 2. Coaching & Style
  document.getElementById("coach-style-badge").textContent = c.style;
  document.getElementById("coach-style-desc").textContent = c.style_description;

  // 3. Metric Badges
  document.getElementById("m-speaking-rate").textContent = c.speaking_rate.toFixed(1);
  const rateStatus = document.getElementById("m-speaking-rate-status");
  if (c.speaking_rate < 3.3) {
    rateStatus.textContent = "Slow tempo";
    rateStatus.className = "metric-status status-moderate";
  } else if (c.speaking_rate > 4.5) {
    rateStatus.textContent = "Fast tempo";
    rateStatus.className = "metric-status status-moderate";
  } else {
    rateStatus.textContent = "Optimal pace (3.5 - 4.5)";
    rateStatus.className = "metric-status status-optimal";
  }

  document.getElementById("m-articulation-rate").textContent = c.articulation_rate.toFixed(1);
  document.getElementById("m-pause-ratio").textContent = Math.round(c.pause_ratio) + "%";
  document.getElementById("m-avg-pause").textContent = Math.round(c.avg_pause_ms);

  document.getElementById("m-pitch-label").textContent = c.pitch_variation_label;
  document.getElementById("m-pitch-sd").textContent = `±${c.pitch_variation_semitones} semitones SD`;

  document.getElementById("m-energy-label").textContent = c.energy_variation_label;
  document.getElementById("m-energy-sd").textContent = `±${c.energy_variation_db} dB SD`;

  // 4. Setup Audio Player
  if (currentAudioUrl) {
    audioPlayer.src = currentAudioUrl;
    audioPlayer.load();
  }

  // 5. Draw Acoustic Timeline
  if (data.timeline) {
    drawTimeline(data.timeline, data.duration_seconds);
  }

  updateFrameHeight();
}

// -------------------------------------------------------------
// Acoustic Timeline Canvas Renderer
// -------------------------------------------------------------
const timelineCanvas = document.getElementById("timeline-canvas");
const tCtx = timelineCanvas.getContext("2d");

function drawTimeline(timeline, duration) {
  timelineCanvas.width = timelineCanvas.clientWidth * window.devicePixelRatio || 800;
  timelineCanvas.height = timelineCanvas.clientHeight * window.devicePixelRatio || 200;

  const w = timelineCanvas.width;
  const h = timelineCanvas.height;
  const midY = h / 2;

  tCtx.clearRect(0, 0, w, h);

  // Background grid
  tCtx.strokeStyle = "#161d2e";
  tCtx.lineWidth = 1;
  tCtx.beginPath();
  tCtx.moveTo(0, midY);
  tCtx.lineTo(w, midY);
  tCtx.stroke();

  // 1. Draw Pause Regions (Red/Amber highlighted blocks)
  if (timeline.pauses && duration > 0) {
    tCtx.fillStyle = "rgba(239, 68, 68, 0.25)";
    for (const p of timeline.pauses) {
      const x1 = (p.start / duration) * w;
      const x2 = (p.end / duration) * w;
      const pauseW = Math.max(2, x2 - x1);
      tCtx.fillRect(x1, 0, pauseW, h);

      // Border highlight
      tCtx.strokeStyle = "rgba(239, 68, 68, 0.6)";
      tCtx.strokeRect(x1, 0, pauseW, h);
    }
  }

  // 2. Draw Waveform (Blue amplitude)
  if (timeline.waveform && timeline.waveform.length > 0) {
    tCtx.strokeStyle = "#3b82f6";
    tCtx.lineWidth = 1.8;
    tCtx.beginPath();

    const n = timeline.waveform.length;
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * w;
      const val = timeline.waveform[i];
      const y = midY - val * (h * 0.4);
      if (i === 0) tCtx.moveTo(x, y);
      else tCtx.lineTo(x, y);
    }
    tCtx.stroke();
  }

  // 3. Draw Pitch (F0) overlay (Amber dots/lines in upper half)
  if (timeline.pitch_hz && timeline.pitch_hz.length > 0) {
    const validPitches = timeline.pitch_hz.filter((p) => p !== null);
    if (validPitches.length > 0) {
      const minPitch = Math.min(...validPitches);
      const maxPitch = Math.max(...validPitches);
      const pitchRange = Math.max(40, maxPitch - minPitch);

      tCtx.strokeStyle = "#f59e0b";
      tCtx.lineWidth = 2.2;
      tCtx.beginPath();
      let started = false;

      const n = timeline.pitch_hz.length;
      for (let i = 0; i < n; i++) {
        const p = timeline.pitch_hz[i];
        const x = (i / (n - 1)) * w;
        if (p !== null) {
          const norm = (p - minPitch) / pitchRange;
          const y = h * 0.7 - norm * (h * 0.55);
          if (!started) {
            tCtx.moveTo(x, y);
            started = true;
          } else {
            tCtx.lineTo(x, y);
          }
        } else {
          started = false;
        }
      }
      tCtx.stroke();
    }
  }

  // 4. Draw Syllable Ticks (Green markers at bottom)
  if (timeline.syllable_times && duration > 0) {
    tCtx.fillStyle = "#10b981";
    for (const st of timeline.syllable_times) {
      const x = (st / duration) * w;
      tCtx.beginPath();
      tCtx.arc(x, h - 8, 3, 0, Math.PI * 2);
      tCtx.fill();
    }
  }
}

// -------------------------------------------------------------
// Copy Card Action
// -------------------------------------------------------------
function copyCardText() {
  const cardText = document.getElementById("ascii-card-text").textContent;
  navigator.clipboard.writeText(cardText).then(() => {
    const copyBtnText = document.getElementById("copy-btn-text");
    const prev = copyBtnText.textContent;
    copyBtnText.textContent = "Copied!";
    setTimeout(() => {
      copyBtnText.textContent = prev;
    }, 2000);
  });
}

// =============================================================
// Live Animated Logo & Ambient Wave Background Engine
// =============================================================
const logoCanvas = document.getElementById("logo-live-canvas");
const lCtx = logoCanvas ? logoCanvas.getContext("2d") : null;

const ambientCanvas = document.getElementById("ambient-waves-canvas");
const aCtx = ambientCanvas ? ambientCanvas.getContext("2d") : null;

let animTime = 0;

function resizeAmbientCanvas() {
  if (!ambientCanvas) return;
  ambientCanvas.width = window.innerWidth * (window.devicePixelRatio || 1);
  ambientCanvas.height = 480 * (window.devicePixelRatio || 1);
}
window.addEventListener("resize", resizeAmbientCanvas);
resizeAmbientCanvas();

function animateVisuals() {
  animTime += 0.035;

  // 1. Draw Live Animated Logo (Equalizer Orb)
  if (lCtx && logoCanvas) {
    const w = logoCanvas.width;
    const h = logoCanvas.height;
    lCtx.clearRect(0, 0, w, h);

    // 5 dancing equalizer bars
    const numBars = 5;
    const barWidth = 3.5;
    const gap = 3.2;
    const totalW = numBars * barWidth + (numBars - 1) * gap;
    const startX = (w - totalW) / 2;

    // Get live audio data if recording
    let audioData = null;
    if (isRecording && analyserNode) {
      audioData = new Uint8Array(analyserNode.frequencyBinCount);
      analyserNode.getByteFrequencyData(audioData);
    }

    for (let i = 0; i < numBars; i++) {
      let normHeight = 0;
      if (audioData) {
        const binIndex = Math.floor((i + 1) * (audioData.length / (numBars + 2)));
        normHeight = (audioData[binIndex] || 0) / 255.0;
        normHeight = Math.max(0.2, normHeight * 1.4);
      } else {
        // Organic idle pulsation
        const freq = 1.8 + i * 0.45;
        const phase = i * 0.85;
        normHeight = 0.35 + 0.48 * Math.sin(animTime * freq + phase);
        normHeight = Math.max(0.18, Math.min(0.95, normHeight));
      }

      const barH = normHeight * (h * 0.65);
      const x = startX + i * (barWidth + gap);
      const y = (h - barH) / 2;

      // Vertical neon gradient
      const grad = lCtx.createLinearGradient(0, y, 0, y + barH);
      grad.addColorStop(0, "#38bdf8"); // Electric cyan
      grad.addColorStop(0.5, "#818cf8"); // Indigo
      grad.addColorStop(1, "#c084fc"); // Purple

      lCtx.fillStyle = grad;
      if (lCtx.roundRect) {
        lCtx.beginPath();
        lCtx.roundRect(x, y, barWidth, barH, 2);
        lCtx.fill();
      } else {
        lCtx.fillRect(x, y, barWidth, barH);
      }
    }
  }

  // 2. Draw Flowing Ambient Soundwaves
  if (aCtx && ambientCanvas) {
    const w = ambientCanvas.width;
    const h = ambientCanvas.height;
    aCtx.clearRect(0, 0, w, h);

    const waves = [
      { color: "rgba(99, 102, 241, 0.18)", freq: 0.003, speed: 1.0, amp: 32, yOffset: h * 0.45 },
      { color: "rgba(168, 85, 247, 0.12)", freq: 0.0045, speed: 0.75, amp: 42, yOffset: h * 0.48 },
      { color: "rgba(56, 189, 248, 0.11)", freq: 0.002, speed: 1.25, amp: 26, yOffset: h * 0.42 },
    ];

    const voiceBoost = isRecording ? 1.7 : 1.0;

    for (const wave of waves) {
      aCtx.beginPath();
      aCtx.moveTo(0, wave.yOffset);

      for (let x = 0; x <= w; x += 15) {
        const y =
          wave.yOffset +
          Math.sin(x * wave.freq + animTime * wave.speed) * (wave.amp * voiceBoost) +
          Math.cos(x * wave.freq * 0.5 - animTime * 0.5) * (14 * voiceBoost);
        aCtx.lineTo(x, y);
      }

      aCtx.lineTo(w, h);
      aCtx.lineTo(0, h);
      aCtx.closePath();

      aCtx.fillStyle = wave.color;
      aCtx.fill();
    }
  }

  requestAnimationFrame(animateVisuals);
}

// Start visual animation loop
requestAnimationFrame(animateVisuals);
