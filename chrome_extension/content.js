// content.js — injected into the CRM/dialer page
let isCallActive = false;

const observer = new MutationObserver(() => {
  // Adapt these selectors to match the actual dialer UI
  const callTimer  = document.querySelector('.call-timer, [data-testid="call-duration"]');
  const hangupBtn  = document.querySelector('[data-testid="hangup-btn"], [aria-label="End call"], .end-call-btn');

  const callOngoing = !!(callTimer || hangupBtn);

  if (callOngoing && !isCallActive) {
    isCallActive = true;
    chrome.runtime.sendMessage({ type: 'CALL_STARTED' });
  } else if (!callOngoing && isCallActive) {
    isCallActive = false;
    chrome.runtime.sendMessage({ type: 'CALL_ENDED' });
  }
});

observer.observe(document.body, { childList: true, subtree: true, attributes: true });
