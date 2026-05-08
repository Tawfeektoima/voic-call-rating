let isRecording = false;

chrome.action.onClicked.addListener(async (tab) => {
  if (isRecording) {
    await stopRecording();
  } else {
    await startRecording(tab);
  }
});

async function startRecording(tab) {
  isRecording = true;
  chrome.action.setBadgeText({ text: 'REC' });
  chrome.action.setBadgeBackgroundColor({ color: '#FF0000' });

  // 1. Create Offscreen Document if it doesn't exist
  const hasOffscreen = await chrome.offscreen.hasDocument();
  if (!hasOffscreen) {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA'],
      justification: 'Capture tab audio for live quality analysis'
    });
  }

  // 2. Get the MediaStream ID for the current tab
  // Note: tabCapture.getMediaStreamId requires being called in response to a user gesture (action click)
  const streamId = await new Promise((resolve) => {
    chrome.tabCapture.getMediaStreamId({ targetTabId: tab.id }, resolve);
  });

  // 3. Send the streamId and session details to the offscreen document
  // For now, using mock session details. In production, these would be fetched from the backend.
  chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'START_RECORDING',
    data: {
      streamId: streamId,
      session_id: 'mock-session-id-' + Date.now(),
      reconnect_token: 'mock-reconnect-token-123456789',
      apiUrl: 'ws://localhost:8000'
    }
  });
}

async function stopRecording() {
  isRecording = false;
  chrome.action.setBadgeText({ text: '' });

  chrome.runtime.sendMessage({
    target: 'offscreen',
    type: 'STOP_RECORDING'
  });

  const hasOffscreen = await chrome.offscreen.hasDocument();
  if (hasOffscreen) {
    await chrome.offscreen.closeDocument();
  }
}
