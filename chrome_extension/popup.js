/**
 * VoiceQA Popup — Automated Auth + Session Management
 * =====================================================
 * Flow:
 *   1. Agent enters email/password -> Login & Start
 *   2. Popup calls POST /api/auth/login -> gets access_token
 *   3. Calls POST /api/live/session/start -> gets session_id + reconnect_token
 *   4. Triggers background.js to start tab capture + WebSocket
 *   5. Shows LIVE indicator with timer
 */

const API_BASE = 'http://localhost:8000';

// ---------------------------------------------------------------------------
// DOM Elements
// ---------------------------------------------------------------------------
const screens = {
  login: document.getElementById('screen-login'),
  start: document.getElementById('screen-start'),
  live:  document.getElementById('screen-live')
};

const els = {
  email:          document.getElementById('email'),
  password:       document.getElementById('password'),
  btnLogin:       document.getElementById('btn-login'),
  loginStatus:    document.getElementById('login-status'),
  userName:       document.getElementById('user-name'),
  btnLogout:      document.getElementById('btn-logout'),
  campaignSelect: document.getElementById('campaign-select'),
  btnStart:       document.getElementById('btn-start'),
  startStatus:    document.getElementById('start-status'),
  timer:          document.getElementById('timer'),
  liveSessionId:  document.getElementById('live-session-id'),
  btnStop:        document.getElementById('btn-stop'),
  liveStatus:     document.getElementById('live-status')
};

let timerInterval = null;
let sessionStart  = null;


// ---------------------------------------------------------------------------
// Screen Management
// ---------------------------------------------------------------------------

function showScreen(name) {
  Object.values(screens).forEach(s => s.classList.remove('active'));
  screens[name].classList.add('active');
}

function setStatus(el, msg, type) {
  el.textContent = msg;
  el.className = `status-bar show status-${type}`;
}

function clearStatus(el) {
  el.className = 'status-bar';
  el.textContent = '';
}


// ---------------------------------------------------------------------------
// Initialization — Check for existing token
// ---------------------------------------------------------------------------

chrome.storage.local.get(['access_token', 'user_name', 'is_recording', 'session_start'], (data) => {
  if (data.is_recording && data.session_start) {
    // Already recording — show live screen
    showScreen('live');
    sessionStart = data.session_start;
    startTimer();
    chrome.storage.local.get(['current_session_id'], (d) => {
      els.liveSessionId.textContent = `Session: ${d.current_session_id || '?'}`;
    });
  } else if (data.access_token) {
    // Token exists — verify it, then show start screen
    verifyToken(data.access_token).then(valid => {
      if (valid) {
        els.userName.textContent = data.user_name || 'Agent';
        loadCampaigns(data.access_token);
        showScreen('start');
      } else {
        // Token expired or invalid
        chrome.storage.local.remove(['access_token', 'user_name']);
        showScreen('login');
      }
    });
  } else {
    showScreen('login');
  }
});


// ---------------------------------------------------------------------------
// Step A: Login
// ---------------------------------------------------------------------------

els.btnLogin.addEventListener('click', async () => {
  const email    = els.email.value.trim();
  const password = els.password.value.trim();

  if (!email || !password) {
    setStatus(els.loginStatus, 'Email and password are required.', 'err');
    return;
  }

  els.btnLogin.disabled = true;
  els.btnLogin.innerHTML = '<span class="spinner"></span> Authenticating...';
  clearStatus(els.loginStatus);

  try {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    if (res.status === 401) {
      setStatus(els.loginStatus, 'Invalid email or password.', 'err');
      resetLoginBtn();
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Server error' }));
      setStatus(els.loginStatus, err.detail || `Error ${res.status}`, 'err');
      resetLoginBtn();
      return;
    }

    const data = await res.json();
    const token    = data.access_token;
    const userName = data.user?.name || email;

    // Save token
    await chrome.storage.local.set({
      access_token: token,
      user_name: userName
    });

    console.log('[Popup] Login successful for:', userName);
    setStatus(els.loginStatus, 'Login OK. Starting session...', 'ok');

    // Immediately start session
    await startSession(token);

  } catch (err) {
    console.error('[Popup] Login error:', err);
    setStatus(els.loginStatus, 'Cannot reach backend. Is it running?', 'err');
    resetLoginBtn();
  }
});

function resetLoginBtn() {
  els.btnLogin.disabled = false;
  els.btnLogin.innerHTML = 'Login & Start Session';
}


// ---------------------------------------------------------------------------
// Step B-E: Start Session
// ---------------------------------------------------------------------------

async function startSession(token) {
  const campaignId = parseInt(els.campaignSelect?.value || '1');
  await chrome.storage.local.set({ selected_campaign_id: campaignId });

  setStatus(els.loginStatus.className.includes('show') ? els.loginStatus : els.startStatus,
    'Creating session...', 'load');

  try {
    // Step C: Create live session
    const res = await fetch(`${API_BASE}/api/live/session/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ campaign_id: campaignId })
    });

    if (res.status === 401 || res.status === 403) {
      const err = await res.json().catch(() => ({}));
      if (res.status === 401) {
        // Token expired — clear and go back to login
        chrome.storage.local.remove(['access_token', 'user_name']);
        setStatus(els.loginStatus, 'Session expired. Please login again.', 'err');
        showScreen('login');
        resetLoginBtn();
        return;
      }
      // 403 = LIVE_PIPELINE_ENABLED=False
      setStatus(els.startStatus, err.detail || 'Live pipeline is disabled on server.', 'warn');
      showScreen('start');
      chrome.storage.local.get(['user_name'], d => {
        els.userName.textContent = d.user_name || 'Agent';
      });
      resetLoginBtn();
      return;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      setStatus(els.startStatus, err.detail || `Error ${res.status}`, 'err');
      showScreen('start');
      resetLoginBtn();
      return;
    }

    const session = await res.json();
    console.log('[Popup] Session created:', session.session_id);

    // Step D: Save session info
    await chrome.storage.local.set({
      current_session_id: session.session_id,
      current_token: session.reconnect_token,
      current_ws_url: `ws://localhost:8000`
    });

    // Step E: Pre-request mic permission (Permission Bridge)
    let micGranted = false;
    try {
      // Query permission state first
      const permResult = await navigator.permissions.query({ name: 'microphone' });
      
      if (permResult.state === 'denied') {
        setStatus(els.startStatus, 'Microphone blocked. Enable it in Chrome settings.', 'err');
        resetLoginBtn();
        return;
      }
      
      // Whether granted or prompt — try to open it
      const micTest = await navigator.mediaDevices.getUserMedia({ audio: true });
      micTest.getTracks().forEach(t => t.stop());
      micGranted = true;
      console.log('[Popup] Mic permission granted.');
      
    } catch (e) {
      console.warn('[Popup] Mic error:', e.name, e.message);
      
      if (e.name === 'NotAllowedError') {
        setStatus(els.startStatus, 
          'Click the 🔒 icon in Chrome address bar and allow Microphone.', 'err');
      } else if (e.name === 'NotFoundError') {
        setStatus(els.startStatus, 'No microphone found on this device.', 'err');
      } else {
        setStatus(els.startStatus, `Mic error: ${e.message}`, 'err');
      }
      resetLoginBtn();
      return;
    }

    // Tell background to start capture
    chrome.runtime.sendMessage({
      type: 'START_FROM_POPUP',
      data: {
        session_id: session.session_id,
        reconnect_token: session.reconnect_token,
        apiUrl: 'ws://localhost:8000',
        micGranted: micGranted
      }
    }, (response) => {
      if (chrome.runtime.lastError) {
        console.error('[Popup] BG error:', chrome.runtime.lastError.message);
        setStatus(els.startStatus, 'Background service error.', 'err');
        showScreen('start');
        els.btnStart.disabled = false;
        els.btnStart.innerHTML = 'Start New Session';
        return;
      }

      if (response && response.success) {
        // Switch to LIVE screen
        sessionStart = Date.now();
        chrome.storage.local.set({
          is_recording: true,
          session_start: sessionStart
        });
        showScreen('live');
        els.liveSessionId.textContent = `Session: ${session.session_id.substring(0, 18)}...`;
        startTimer();
        setStatus(els.liveStatus, 'Connected to backend.', 'ok');
      } else {
        // Show specific error from background
        const msg = response?.error || 'Capture failed.';
        setStatus(els.startStatus, msg, 'err');
        showScreen('start');
        els.btnStart.disabled = false;
        els.btnStart.innerHTML = 'Start New Session';
      }
    });

  } catch (err) {
    console.error('[Popup] Session start error:', err);
    setStatus(els.startStatus, 'Cannot reach backend.', 'err');
    showScreen('start');
    resetLoginBtn();
  }
}


// ---------------------------------------------------------------------------
// Start Session Button (for returning users)
// ---------------------------------------------------------------------------

els.btnStart.addEventListener('click', async () => {
  els.btnStart.disabled = true;
  els.btnStart.innerHTML = '<span class="spinner"></span> Connecting...';
  clearStatus(els.startStatus);

  const data = await chrome.storage.local.get(['access_token']);
  if (!data.access_token) {
    showScreen('login');
    return;
  }

  await startSession(data.access_token);
  els.btnStart.disabled = false;
  els.btnStart.innerHTML = 'Start New Session';
});

// Save selected campaign automatically
els.campaignSelect?.addEventListener('change', () => {
  const selectedId = parseInt(els.campaignSelect.value || '1');
  chrome.storage.local.set({ selected_campaign_id: selectedId });
});


// ---------------------------------------------------------------------------
// Stop Session
// ---------------------------------------------------------------------------

els.btnStop.addEventListener('click', () => {
  chrome.runtime.sendMessage({ type: 'STOP_FROM_POPUP' });
  stopTimer();
  chrome.storage.local.set({ is_recording: false, session_start: null });
  setStatus(els.liveStatus, 'Session ended.', 'warn');

  // Go back to start screen after a brief delay
  setTimeout(() => {
    showScreen('start');
    chrome.storage.local.get(['user_name'], d => {
      els.userName.textContent = d.user_name || 'Agent';
    });
    loadCampaigns();
  }, 1500);
});


// ---------------------------------------------------------------------------
// Logout
// ---------------------------------------------------------------------------

els.btnLogout.addEventListener('click', () => {
  chrome.storage.local.remove(['access_token', 'user_name', 'is_recording', 'session_start']);
  showScreen('login');
});


// ---------------------------------------------------------------------------
// Timer
// ---------------------------------------------------------------------------

function startTimer() {
  updateTimerDisplay();
  timerInterval = setInterval(updateTimerDisplay, 1000);
}

function stopTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = null;
}

function updateTimerDisplay() {
  if (!sessionStart) return;
  const elapsed = Math.floor((Date.now() - sessionStart) / 1000);
  const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const secs = String(elapsed % 60).padStart(2, '0');
  els.timer.textContent = `${mins}:${secs}`;
}


// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function verifyToken(token) {
  try {
    // Use a lightweight endpoint to check if token is still valid
    const res = await fetch(`${API_BASE}/api/admin/employees`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function loadCampaigns(token) {
  try {
    const tkn = token || (await chrome.storage.local.get(['access_token'])).access_token;
    if (!tkn) return;

    const res = await fetch(`${API_BASE}/api/admin/campaigns`, {
      headers: { 'Authorization': `Bearer ${tkn}` }
    });

    if (res.ok) {
      const campaigns = await res.json();
      els.campaignSelect.innerHTML = '';
      if (campaigns.length === 0) {
        els.campaignSelect.innerHTML = '<option value="1">Default Campaign</option>';
      } else {
        campaigns.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = c.name;
          els.campaignSelect.appendChild(opt);
        });
      }
    }
  } catch (e) {
    console.warn('[Popup] Failed to load campaigns:', e);
  }
}
