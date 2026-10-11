document.getElementById('open-dashboard').addEventListener('click', () => {
  chrome.tabs.create({ url: "http://127.0.0.1:5173/dashboard" });
});
