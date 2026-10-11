// PhoneBalance One-Sec Mindful Interceptor Content Script
(function() {
  const currentDomain = window.location.hostname;
  const sessionPassed = sessionStorage.getItem('pb_interceptor_passed');
  
  if (sessionPassed) return;

  // Create Interstitial Overlay
  const overlay = document.createElement('div');
  overlay.id = 'pb-friction-overlay';
  overlay.innerHTML = `
    <div class="pb-card">
      <div class="pb-pulse-ring">
        <div class="pb-timer" id="pb-timer-count">7</div>
      </div>
      <h2 class="pb-title">Take a Mindful Breath</h2>
      <p class="pb-subtitle">You are opening <strong>${currentDomain}</strong>. Pause for 7 seconds to check in with your attention.</p>
      
      <div class="pb-intents" id="pb-intents" style="display: none;">
        <p class="pb-label">Why are you opening this right now?</p>
        <div class="pb-btn-grid">
          <button class="pb-intent-btn" data-intent="Boredom">🥱 Boredom / Habit</button>
          <button class="pb-intent-btn" data-intent="Tutorial">📚 Tutorial / Work</button>
          <button class="pb-intent-btn" data-intent="Message">💬 Reply to Message</button>
          <button class="pb-intent-btn" data-intent="Short Break">☕ 5-Min Intentional Break</button>
        </div>
      </div>

      <div class="pb-actions">
        <button id="pb-leave-btn" class="pb-btn-secondary">Close This Tab</button>
        <button id="pb-proceed-btn" class="pb-btn-primary" disabled>Wait (7s)...</button>
      </div>
    </div>
  `;

  document.documentElement.appendChild(overlay);

  let secondsLeft = 7;
  const timerElem = document.getElementById('pb-timer-count');
  const proceedBtn = document.getElementById('pb-proceed-btn');
  const intentsBlock = document.getElementById('pb-intents');
  const leaveBtn = document.getElementById('pb-leave-btn');

  const interval = setInterval(() => {
    secondsLeft--;
    if (timerElem) timerElem.textContent = secondsLeft;
    if (proceedBtn) proceedBtn.textContent = `Wait (${secondsLeft}s)...`;

    if (secondsLeft <= 0) {
      clearInterval(interval);
      if (proceedBtn) {
        proceedBtn.disabled = false;
        proceedBtn.textContent = "Proceed to Website";
      }
      if (intentsBlock) intentsBlock.style.display = 'block';
    }
  }, 1000);

  leaveBtn.addEventListener('click', () => {
    // Notify background
    chrome.runtime.sendMessage({
      type: "LOG_FRICTION",
      domain: currentDomain,
      action: "aborted"
    });
    window.location.href = "about:blank";
  });

  proceedBtn.addEventListener('click', () => {
    const selectedBtn = document.querySelector('.pb-intent-btn.active');
    const intent = selectedBtn ? selectedBtn.getAttribute('data-intent') : "Default";

    chrome.runtime.sendMessage({
      type: "LOG_FRICTION",
      domain: currentDomain,
      action: "proceeded",
      intent: intent
    });

    sessionStorage.setItem('pb_interceptor_passed', 'true');
    overlay.classList.add('pb-fade-out');
    setTimeout(() => overlay.remove(), 400);
  });

  document.querySelectorAll('.pb-intent-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.pb-intent-btn').forEach(b => b.classList.remove('active'));
      e.target.classList.add('active');
    });
  });
})();
