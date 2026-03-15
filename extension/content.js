// Aegis-Live Guardian - Content Script

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getPageContent") {
        sendResponse({ url: window.location.href, text: document.body.innerText });
        return true;
    }

    if (request.type === "SHOW_WARNING") {
        displayWarningBanner(request.reason, request.url);
    }
});

function displayWarningBanner(reason, url) {
    if (document.getElementById('aegis-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'aegis-banner';
    banner.style.cssText = 'position:fixed;top:0;left:0;width:100%;background:#ef4444;color:white;padding:12px 20px;text-align:center;z-index:999999;font-size:15px;font-weight:bold;font-family:Segoe UI,sans-serif;display:flex;justify-content:center;align-items:center;gap:15px;box-shadow:0 4px 20px rgba(239,68,68,0.5)';

    const message = document.createElement('span');
    message.innerHTML = `⚠️ <strong>AEGIS ALERT:</strong> Potential phishing detected! ${reason}`;

    const reportBtn = document.createElement('button');
    reportBtn.id = 'aegis-report-btn';
    reportBtn.innerHTML = '🚨 Report Scammer';
    reportBtn.style.cssText = 'background:#ffffff;color:#ef4444;border:none;padding:8px 16px;border-radius:4px;font-weight:bold;cursor:pointer;font-size:13px;white-space:nowrap;transition:all 0.2s ease;box-shadow:0 2px 8px rgba(0,0,0,0.2)';

    reportBtn.onmouseover = function() { this.style.backgroundColor = '#fee2e2'; };
    reportBtn.onmouseout = function() { this.style.backgroundColor = '#ffffff'; };
    reportBtn.onclick = function() { reportScammer(url, reason, reportBtn); };

    banner.appendChild(message);
    banner.appendChild(reportBtn);

    if (document.body.firstChild) {
        document.body.insertBefore(banner, document.body.firstChild);
    } else {
        document.body.appendChild(banner);
    }
}

function reportScammer(url, reason, buttonElement) {
    buttonElement.disabled = true;
    buttonElement.innerHTML = '⏳ Reporting...';
    buttonElement.style.opacity = '0.7';

    fetch(CONFIG.BASE_URL + CONFIG.ENDPOINTS.SCOUT_ADD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, reason: reason || 'Manually reported', source: 'user_report' }),
    })
    .then(res => res.json())
    .then(() => {
        buttonElement.innerHTML = '✅ Reported!';
        buttonElement.style.backgroundColor = '#22c55e';
        buttonElement.style.color = 'white';
        const banner = document.getElementById('aegis-banner');
        if (banner) banner.style.backgroundColor = '#22c55e';
    })
    .catch(() => {
        buttonElement.disabled = false;
        buttonElement.innerHTML = '🚨 Report Scammer';
        buttonElement.style.opacity = '1';
    });
}
