/**
 * VoiceQA Offscreen Audio Processor (Dual-Channel Multiplexed)
 * ==========================================================
 * Binary Format: 16kHz, 16-bit signed PCM, Mono, Little-Endian
 * Payload: 6400 bytes total per 100ms
 *   - [0:3200]: Customer Tab Audio
 *   - [3200:6400]: Agent Microphone Audio
 */

let audioContext    = null;
let scriptProcessor = null;
let mediaStream     = null;
let webSocket       = null;
let audioBuffer     = [];

const TARGET_SAMPLE_RATE = 16000;
const CHUNK_DURATION_MS  = 100; // 100ms window
const SAMPLES_PER_CHUNK  = (TARGET_SAMPLE_RATE * CHUNK_DURATION_MS) / 1000; // 1600

let agentAudioContext    = null;
let agentScriptProcessor = null;
let agentMediaStream     = null;
let agentBuffer          = [];

let currentSessionId = null;
let currentApiUrl    = null;
let micGranted       = false;

let chunksSent = 0;
let wsConnected = false;

// ---------------------------------------------------------------------------
// Message Handler
// ---------------------------------------------------------------------------
chrome.runtime.onMessage.addListener(async (message) => {
  if (message.target !== 'offscreen') return;

  if (message.type === 'START_RECORDING') {
    console.log('[Offscreen] START_RECORDING received');
    try {
      currentSessionId = message.data.session_id;
      currentApiUrl    = message.data.apiUrl;
      micGranted       = message.data.micGranted || false;
      chunksSent       = 0;

      await connectWebSocket(currentSessionId, message.data.reconnect_token, currentApiUrl);
      
      // Start both captures in parallel
      await Promise.all([
        startTabCapture(message.data),
        micGranted ? startAgentPcmCapture() : Promise.resolve()
      ]);
      
    } catch (err) {
      console.error('[Offscreen] CRITICAL: Failed to start capture:', err.name, err.message);
      reportStatus('error', err.message);
    }
  }

  if (message.type === 'STOP_RECORDING') {
    console.log('[Offscreen] STOP_RECORDING received');
    await stopAll();
  }
});

// ---------------------------------------------------------------------------
// Customer Capture (Tab Audio)
// ---------------------------------------------------------------------------
async function startTabCapture({ streamId }) {
  console.log('[Offscreen] Getting tab media stream...');
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      }
    });
  } catch (err) {
    console.error('[Offscreen] Tab capture failed:', err.message);
    throw err;
  }

  audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  const source = audioContext.createMediaStreamSource(mediaStream);
  scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

  scriptProcessor.onaudioprocess = (event) => {
    const inputData = event.inputBuffer.getChannelData(0);
    for (let i = 0; i < inputData.length; i++) {
      audioBuffer.push(inputData[i]);
    }

    while (audioBuffer.length >= SAMPLES_PER_CHUNK) {
      const customerSamples = audioBuffer.splice(0, SAMPLES_PER_CHUNK);
      buildAndSendMuxedPacket(customerSamples);
    }
  };

  source.connect(scriptProcessor);
  scriptProcessor.connect(audioContext.destination);
  console.log('[Offscreen] Customer tab capture connected.');
}

// ---------------------------------------------------------------------------
// Agent Capture (Microphone)
// ---------------------------------------------------------------------------
async function startAgentPcmCapture() {
  console.log('[Offscreen] Starting agent PCM capture...');
  try {
    agentMediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: TARGET_SAMPLE_RATE
      },
      video: false
    });
    agentAudioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
    const source = agentAudioContext.createMediaStreamSource(agentMediaStream);
    agentScriptProcessor = agentAudioContext.createScriptProcessor(4096, 1, 1);

    agentScriptProcessor.onaudioprocess = (event) => {
      const inputData = event.inputBuffer.getChannelData(0);
      for (let i = 0; i < inputData.length; i++) {
        agentBuffer.push(inputData[i]);
      }
    };
    source.connect(agentScriptProcessor);
    agentScriptProcessor.connect(agentAudioContext.destination);
    console.log('[Offscreen] Agent mic capture connected.');
  } catch (err) {
    console.error('[Offscreen] Agent mic capture failed:', err.name, err.message);

    if (err.name === 'NotAllowedError') {
      console.warn('[Offscreen] Mic denied — agent channel will send silence.');
      // Do NOT crash — continue with zeros for agent channel
    }
    // For any mic error, the agent buffer stays empty and
    // buildAndSendMuxedPacket() pads with silence automatically
  }
}

function stopAgentPcmCapture() {
  if (agentScriptProcessor) agentScriptProcessor.disconnect();
  if (agentAudioContext) agentAudioContext.close();
  if (agentMediaStream) agentMediaStream.getTracks().forEach(t => t.stop());
  agentBuffer = [];
  agentScriptProcessor = null;
  agentAudioContext = null;
  agentMediaStream = null;
}

// ---------------------------------------------------------------------------
// Dual-Channel Multiplexing
// ---------------------------------------------------------------------------
function buildAndSendMuxedPacket(customerSamples) {
  if (!webSocket || webSocket.readyState !== WebSocket.OPEN) return;

  console.log('[MUX] Sending packet, agent buffer size:', agentBuffer.length);

  // Pad agent buffer with silence if behind
  while (agentBuffer.length < SAMPLES_PER_CHUNK) agentBuffer.push(0);
  const agentSamples = agentBuffer.splice(0, SAMPLES_PER_CHUNK);

  // Allocate single 6400-byte buffer (1600 samples * 2 bytes * 2 channels)
  const muxed = new ArrayBuffer(6400);
  const view  = new DataView(muxed);

  const float32ToInt16 = (f) => {
    const clamped = Math.max(-1, Math.min(1, f));
    return clamped < 0 ? clamped * 0x8000 : clamped * 0x7FFF;
  };

  // Customer PCM → offset 0 (bytes 0–3199)
  for (let i = 0; i < customerSamples.length; i++) {
    view.setInt16(i * 2, float32ToInt16(customerSamples[i]), true);
  }

  // Agent PCM → offset 3200 (bytes 3200–6399)
  for (let i = 0; i < agentSamples.length; i++) {
    view.setInt16(3200 + i * 2, float32ToInt16(agentSamples[i]), true);
  }

  webSocket.send(muxed);
  console.log('[MUX] Packet sent: 6400 bytes');
  chunksSent++;

  if (chunksSent % 50 === 0) {
    console.log(`[Offscreen] Muxed chunks sent: ${chunksSent} (${(chunksSent * 0.1).toFixed(1)}s)`);
  }
}

// ---------------------------------------------------------------------------
// WebSocket Connection
// ---------------------------------------------------------------------------
async function connectWebSocket(session_id, reconnect_token, apiUrl) {
  const wsUrl = `${apiUrl}/api/live/ws/live/${session_id}?token=${reconnect_token}`;
  console.log('[Offscreen] Connecting WebSocket:', wsUrl);

  return new Promise((resolve, reject) => {
    webSocket = new WebSocket(wsUrl);
    webSocket.binaryType = 'arraybuffer';

    webSocket.onopen = () => {
      wsConnected = true;
      console.log('[Offscreen] WebSocket CONNECTED');
      reportStatus('connected', 'WebSocket connected');
      resolve();
    };

    webSocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === 'connected') {
          console.log('[Offscreen] Handshake OK. Expected format:', data.expected_format);
        } else if (data.suggestion) {
          console.log('[Offscreen] RAG Suggestion:', data.suggestion);
        }
      } catch (e) {
        console.log('[Offscreen] Server binary/raw message received');
      }
    };

    webSocket.onerror = (event) => {
      console.error('[Offscreen] WebSocket ERROR');
      reportStatus('error', 'WebSocket connection error');
    };

    webSocket.onclose = (event) => {
      wsConnected = false;
      console.warn('[Offscreen] WebSocket CLOSED. Code:', event.code);
      reportStatus('closed', `WebSocket closed: ${event.code}`);
    };

    setTimeout(() => {
      if (!wsConnected) reject(new Error('WebSocket connection timeout'));
    }, 5000);
  });
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------
async function stopAll() {
  console.log('[Offscreen] Stopping all capture...');

  if (scriptProcessor) {
    scriptProcessor.disconnect();
    scriptProcessor = null;
  }
  if (audioContext) {
    await audioContext.close();
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  stopAgentPcmCapture();

  if (webSocket) {
    if (webSocket.readyState === WebSocket.OPEN) {
      webSocket.close(1000, 'Session ended by agent');
    }
    webSocket = null;
  }

  audioBuffer = [];
  chunksSent = 0;
  console.log('[Offscreen] All capture stopped.');
}

function reportStatus(status, message) {
  try {
    chrome.runtime.sendMessage({
      type: 'WS_STATUS',
      data: { status, message, chunksSent }
    });
  } catch (e) { }
}

console.log('[Offscreen] Offscreen document loaded and ready.');
