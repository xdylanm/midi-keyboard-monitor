(() => {
  const statusEl = document.getElementById('status');
  const velEl = document.getElementById('velocity');
  const barFill = document.getElementById('bar-fill');
  const recentEl = document.getElementById('recent');

  let history = [];

  function updateUI(v) {
    velEl.textContent = v;
    const pct = Math.min(100, Math.round((v / 127) * 100));
    barFill.style.width = pct + '%';
    history.unshift(v);
    if (history.length > 10) history.pop();
    recentEl.textContent = history.join(', ');
  }

  // WebSocket with automatic reconnect (exponential backoff + jitter)
  const wsProto = (location.protocol === 'https:') ? 'wss' : 'ws';
  const wsUrl = `${wsProto}://${location.host}/ws`;
  let ws = null;
  let backoff = 1000; // start 1s
  const MAX_BACKOFF = 60000; // 60s

  function connectWS() {
    statusEl.textContent = 'Connecting...';
    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      backoff = 1000;
      statusEl.textContent = 'WebSocket connected';
    };

    ws.onmessage = (ev) => {
      try {
        const obj = JSON.parse(ev.data);
        if (obj.type === 'note' && obj.event === 'note_on') {
          updateUI(obj.velocity);
        }
      } catch (e) { }
    };

    ws.onclose = () => {
      statusEl.textContent = 'Disconnected — reconnecting...';
      scheduleReconnect();
    };

    ws.onerror = () => {
      // ensure connection closed so onclose handles reconnect
      try { ws.close(); } catch (e) {}
    };
  }

  function scheduleReconnect() {
    const jitter = Math.random() * 500;
    setTimeout(() => connectWS(), backoff + jitter);
    backoff = Math.min(MAX_BACKOFF, backoff * 2);
  }

  // Start
  connectWS();
})();
