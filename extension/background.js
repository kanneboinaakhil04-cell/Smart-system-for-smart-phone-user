// PhoneBalance Chrome Extension Background Service Worker
const API_BASE = "http://127.0.0.1:8000/api";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "LOG_FRICTION") {
    // Send interception event to PhoneBalance backend
    fetch(`${API_BASE}/accountability/friction-rules/log-interception?domain=${encodeURIComponent(message.domain)}&action=${message.action}&intent=${encodeURIComponent(message.intent || "")}`, {
      method: "POST"
    }).catch(err => console.log("Failed to log friction to backend:", err));
  }
});

// Periodic Heartbeat every minute
chrome.alarms.create("telemetry_heartbeat", { periodInMinutes: 1 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "telemetry_heartbeat") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].url) {
        try {
          const url = new URL(tabs[0].url);
          if (url.protocol.startsWith("http")) {
            fetch(`${API_BASE}/screentime/agent-heartbeat`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                app_name: url.hostname,
                window_title: tabs[0].title || url.hostname,
                duration_seconds: 60,
                category: (url.hostname.includes("instagram") || url.hostname.includes("youtube")) ? "Social" : "Entertainment",
                source: "browser_extension"
              })
            }).catch(e => {});
          }
        } catch(e) {}
      }
    });
  }
});
