/**
 * VoiceQA Background Service Worker (Manifest V3)
 * 
 * Responsibilities:
 * - Manages the offscreen document lifecycle.
 * - Captures the tab's MediaStream ID (requires user gesture context).
 * - Bridges messages between Popup <-> Offscreen Document.
 * - Does NOT directly access audio or microphone (MV3 restriction).
 */

let isRecording = false;

// ---------------------------------------------------------------------------
// Content Script Router: Auto-start on call detected
// ---------------------------------------------------------------------------
const API_BASE = 'http://localhost:8000';

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'CALL_STARTED' && !isRecording) {
    console.log('[BG] CALL_STARTED detected. Automating session creation...');
    autoStartSession();
  }
  if (message.type === 'CALL_ENDED' && isRecording) {
    console.log('[BG] CALL_ENDED detected. Stopping recording...');
    handleStop();
  }
});

async function autoStartSession() {
  try {
    const data = await chrome.storage.local.get(['access_token', 'selected_campaign_id']);
    if (!data.access_token) {
      console.warn('[BG] Cannot auto-start: No access token. Agent must login first.');
      return;
    }

    // 1. Get Employee Campaign (Fallback)
    const meRes = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { 'Authorization': `Bearer ${data.access_token}` }
    });
    if (!meRes.ok) throw new Error('Failed to fetch employee details');
    const meData = await meRes.json();
    
    // Prioritize explicitly selected campaign, otherwise use default
    const finalCampaignId = data.selected_campaign_id || meData.campaign_id;

    // 2. Start Live Session
    const startRes = await fetch(`${API_BASE}/api/live/session/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${data.access_token}`
      },
      body: JSON.stringify({ campaign_id: finalCampaignId })
    });
    if (!startRes.ok) throw new Error('Failed to create live session on server');
    
    const sessionData = await startRes.json();
    
    // 3. Save to storage
    await chrome.storage.local.set({
      current_session_id: sessionData.session_id,
      current_token: sessionData.reconnect_token,
      current_ws_url: `ws://localhost:8000`
    });

    // 4. Start recording using existing flow
    // Pass micGranted=true assuming they granted it during initial login
    const startData = {
      session_id: sessionData.session_id,
      reconnect_token: sessionData.reconnect_token,
      apiUrl: 'ws://localhost:8000',
      micGranted: true 
    };

    handleStart(startData).catch(e => console.error('[BG] handleStart failed:', e));

  } catch (e) {
    console.error('[BG] Auto-start sequence failed:', e.message);
  }
}

// ---------------------------------------------------------------------------
// Message Router: Popup -> Background -> Offscreen
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log('[BG] Message received:', message.type);

  if (message.type === 'START_FROM_POPUP') {
    handleStart(message.data)
      .then(() => sendResponse({ success: true }))
      .catch((err) => {
        console.error('[BG] Start failed:', err);
        sendResponse({ success: false, error: err.message || String(err) });
      });
    return true; // Keep the message channel open for async sendResponse
  }

  if (message.type === 'STOP_FROM_POPUP') {
    handleStop();
    sendResponse({ success: true });
  }

  // Forward status messages from offscreen to popup (if popup is open)
  if (message.type === 'WS_STATUS') {
    console.log('[BG] WebSocket status from offscreen:', message.data);
  }
});


// ---------------------------------------------------------------------------
// Start Recording Flow
// ---------------------------------------------------------------------------

async function handleStart(data) {
  console.log('[BG] Starting capture for session:', data.session_id);

  // Step 1: Get the active CRM tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

  if (!tab) {
    console.error('[BG] No active tab found');
    throw new Error('No active tab found.');
  }

  // Step 2: Block Chrome internal pages
  if (
    !tab.url ||
    tab.url.startsWith('chrome://') ||
    tab.url.startsWith('chrome-extension://') ||
    tab.url.startsWith('edge://') ||
    tab.url === 'about:blank' ||
    tab.url === 'about:newtab'
  ) {
    console.warn('[BG] Capture disabled on internal browser page:', tab.url);
    throw new Error('Capture is not allowed on Chrome internal pages. Please switch to your CRM tab.');
  }

  // Step 3: Get streamId — must be done in background, NOT offscreen
  // The streamId expires in ~5 seconds, so send to offscreen IMMEDIATELY after
  let streamId;
  try {
    streamId = await new Promise((resolve, reject) => {
      chrome.tabCapture.getMediaStreamId(
        { targetTabId: tab.id },
        (id) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else {
            resolve(id);
          }
        }
      );
    });
  } catch (err) {
    console.error('[BG] tabCapture.getMediaStreamId failed:', err.message);
    throw new Error(`Tab capture failed: ${err.message}`);
  }

  if (!streamId) throw new Error('Failed to get tab capture stream ID');
  console.log('[BG] Got streamId for tab:', tab.id, tab.url);

  // Step 4: Ensure offscreen document exists
  const hasOffscreen = await chrome.offscreen.hasDocument();
  if (!hasOffscreen) {
    console.log('[BG] Creating offscreen document...');
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA'],
      justification: 'Capture tab audio and agent microphone for quality assurance'
    });
    console.log('[BG] Offscreen document created.');
  }

  // Step 5: Send streamId + session data to offscreen (no delay after getMediaStreamId)
  // Set state AFTER successful streamId acquisition
  isRecording = true;
  chrome.action.setBadgeText({ text: 'REC' });
  chrome.action.setBadgeBackgroundColor({ color: '#FF0000' });
  chrome.storage.local.set({ is_recording: true });

  chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'START_RECORDING',
    data: {
      streamId,
      session_id: data.session_id,
      reconnect_token: data.reconnect_token,
      apiUrl: data.apiUrl,
      micGranted: data.micGranted ?? true
    }
  });

  console.log('[BG] START_RECORDING sent to offscreen document.');
}


// ---------------------------------------------------------------------------
// Stop Recording Flow
// ---------------------------------------------------------------------------

async function handleStop() {
  console.log('[BG] Stopping capture...');
  isRecording = false;
  chrome.action.setBadgeText({ text: '' });
  chrome.storage.local.set({ is_recording: false });

  chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'STOP_RECORDING'
  });

  // Give the offscreen document time to upload agent audio before closing
  setTimeout(async () => {
    const hasOffscreen = await chrome.offscreen.hasDocument();
    if (hasOffscreen) {
      await chrome.offscreen.closeDocument();
      console.log('[BG] Offscreen document closed.');
    }
  }, 5000); // 5 second grace period for upload
}


// ---------------------------------------------------------------------------
// Fallback: Extension icon click (no popup)
// ---------------------------------------------------------------------------

// This is a backup if the popup doesn't load for some reason
chrome.action.onClicked.addListener(async (tab) => {
  console.log('[BG] Action clicked (fallback) — use the popup instead.');
});
