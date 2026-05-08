let audioContext;
let scriptProcessor;
let mediaStream;
let webSocket;
let audioBuffer = [];
const TARGET_SAMPLE_RATE = 16000;
const CHUNK_DURATION_MS = 500;
const SAMPLES_PER_CHUNK = (TARGET_SAMPLE_RATE * CHUNK_DURATION_MS) / 1000;

let micStream;
let micRecorder;
let micChunks = [];
let currentSessionId;
let currentApiUrl;

chrome.runtime.onMessage.addListener(async (message) => {
  if (message.target !== 'offscreen') return;

  if (message.type === 'START_RECORDING') {
    try {
      currentSessionId = message.data.session_id;
      currentApiUrl = message.data.apiUrl;
      await startCapture(message.data);
      await startMicCapture();
    } catch (err) {
      console.error('Failed to start capture:', err);
    }
  } else if (message.type === 'STOP_RECORDING') {
    stopCapture();
    stopMicCapture();
  }
});

async function startCapture({ streamId, session_id, reconnect_token, apiUrl }) {
  // 1. Get the media stream from tabCapture
  mediaStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: {
        chromeMediaSource: 'tab',
        chromeMediaSourceId: streamId
      }
    }
  });

  // 2. Setup AudioContext at 16kHz
  // This handles the downsampling if the tab audio is at a higher rate (usually 44.1 or 48kHz)
  audioContext = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  const source = audioContext.createMediaStreamSource(mediaStream);

  // 3. Setup ScriptProcessor for PCM conversion
  // Buffer size 4096 (approx 256ms at 16kHz)
  scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);

  scriptProcessor.onaudioprocess = (event) => {
    const inputData = event.inputBuffer.getChannelData(0); // Mono channel
    for (let i = 0; i < inputData.length; i++) {
      audioBuffer.push(inputData[i]);
    }

    // When we have enough samples for 500ms, send the chunk
    if (audioBuffer.length >= SAMPLES_PER_CHUNK) {
      const samples = audioBuffer.splice(0, SAMPLES_PER_CHUNK);
      sendPcmChunk(samples);
    }
  };

  source.connect(scriptProcessor);
  scriptProcessor.connect(audioContext.destination);

  // 4. Setup WebSocket to stream PCM data
  // The URL matches our backend route: /api/live/ws/live/{session_id}?token={token}
  const wsUrl = `${apiUrl}/api/live/ws/live/${session_id}?token=${reconnect_token}`;
  webSocket = new WebSocket(wsUrl);
  webSocket.binaryType = 'arraybuffer';

  webSocket.onopen = () => console.log('WebSocket connected to VoiceQA Backend');
  webSocket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event === 'connected') {
        console.log('Handshake successful. Backend expected format:', data.expected_format);
      }
    } catch (e) {
      // Ignore non-JSON messages if any
    }
  };
  
  webSocket.onerror = (err) => console.error('WebSocket Error:', err);
  webSocket.onclose = () => console.log('WebSocket closed');
}

function sendPcmChunk(samples) {
  if (!webSocket || webSocket.readyState !== WebSocket.OPEN) return;

  // Convert Float32 samples [-1.0, 1.0] to 16-bit Signed PCM [ -32768, 32767 ]
  const buffer = new ArrayBuffer(samples.length * 2);
  const view = new DataView(buffer);

  for (let i = 0; i < samples.length; i++) {
    let s = Math.max(-1, Math.min(1, samples[i]));
    // 0x8000 is 32768, 0x7FFF is 32767
    const val = s < 0 ? s * 0x8000 : s * 0x7FFF;
    view.setInt16(i * 2, val, true); // true for Little-endian (standard for PCM)
  }

  webSocket.send(buffer);
  console.log(`[VoiceQA] Chunk Sent: ${samples.length} samples at ${new Date().toLocaleTimeString()}`);
}

function stopCapture() {
  console.log('Stopping capture...');
  if (scriptProcessor) {
    scriptProcessor.disconnect();
    scriptProcessor = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  if (webSocket) {
    webSocket.close();
    webSocket = null;
  }
  audioBuffer = [];
}

async function startMicCapture() {
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micRecorder = new MediaRecorder(micStream);
    micChunks = [];
    micRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) micChunks.push(e.data);
    };
    micRecorder.start();
    console.log('Microphone capture started locally.');
  } catch (err) {
    console.error('Microphone capture failed:', err);
  }
}

async function stopMicCapture() {
  if (micRecorder && micRecorder.state !== 'inactive') {
    micRecorder.onstop = async () => {
      const blob = new Blob(micChunks, { type: 'audio/webm' });
      await uploadAgentAudio(blob);
    };
    micRecorder.stop();
  }
  if (micStream) {
    micStream.getTracks().forEach(track => track.stop());
    micStream = null;
  }
}

async function uploadAgentAudio(blob) {
  if (!currentSessionId || !currentApiUrl) return;
  
  const formData = new FormData();
  formData.append('file', blob, 'agent_mic.webm');
  
  console.log('Uploading agent microphone recording...');
  try {
    const response = await fetch(`${currentApiUrl}/api/live/session/${currentSessionId}/upload_agent_audio`, {
      method: 'POST',
      body: formData
    });
    if (response.ok) {
      console.log('Agent audio upload complete.');
    } else {
      console.error('Upload failed with status:', response.status);
    }
  } catch (err) {
    console.error('Error uploading agent audio:', err);
  }
}
