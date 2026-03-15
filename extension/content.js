// Aegis-Live Guardian - Content Script
// Injected into active tabs to analyze content and display warnings

console.log('Aegis-Live: Content script initialized');

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "getPageContent") {
        const pageContent = {
            url: window.location.href,
            text: document.body.innerText,
        };
        console.log('Aegis: Page content extracted for analysis');
        sendResponse(pageContent);
        return true; // Keep the message channel open for async response
    }

    if (request.type === "SHOW_WARNING") {
        displayWarningBanner(request.reason, request.url);
    }
});

// Display warning banner with Report Scammer button
function displayWarningBanner(reason, url) {
    // Prevent multiple banners
    if (document.getElementById('aegis-banner')) {
        return;
    }

    const banner = document.createElement('div');
    banner.id = 'aegis-banner';
    banner.style.position = 'fixed';
    banner.style.top = '0';
    banner.style.left = '0';
    banner.style.width = '100%';
    banner.style.backgroundColor = '#ef4444';
    banner.style.color = 'white';
    banner.style.padding = '12px 20px';
    banner.style.textAlign = 'center';
    banner.style.zIndex = '999999';
    banner.style.fontSize = '15px';
    banner.style.fontWeight = 'bold';
    banner.style.fontFamily = 'Segoe UI, sans-serif';
    banner.style.display = 'flex';
    banner.style.justifyContent = 'center';
    banner.style.alignItems = 'center';
    banner.style.gap = '15px';
    banner.style.boxShadow = '0 4px 20px rgba(239, 68, 68, 0.5)';

    // Warning message
    const message = document.createElement('span');
    message.innerHTML = `⚠️ <strong>AEGIS ALERT:</strong> Potential phishing detected! ${reason}`;

    // Report Scammer button
    const reportBtn = document.createElement('button');
    reportBtn.id = 'aegis-report-btn';
    reportBtn.innerHTML = '🚨 Report Scammer';
    reportBtn.style.backgroundColor = '#ffffff';
    reportBtn.style.color = '#ef4444';
    reportBtn.style.border = 'none';
    reportBtn.style.padding = '8px 16px';
    reportBtn.style.borderRadius = '4px';
    reportBtn.style.fontWeight = 'bold';
    reportBtn.style.cursor = 'pointer';
    reportBtn.style.fontSize = '13px';
    reportBtn.style.fontFamily = 'Segoe UI, sans-serif';
    reportBtn.style.whiteSpace = 'nowrap';
    reportBtn.style.transition = 'all 0.2s ease';
    reportBtn.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.2)';

    // Hover effect
    reportBtn.onmouseover = function() {
        this.style.backgroundColor = '#fee2e2';
        this.style.transform = 'scale(1.05)';
    };
    reportBtn.onmouseout = function() {
        this.style.backgroundColor = '#ffffff';
        this.style.transform = 'scale(1)';
    };

    // Click handler for reporting
    reportBtn.onclick = function() {
        reportScammer(url, reason, reportBtn);
    };

    banner.appendChild(message);
    banner.appendChild(reportBtn);

    // Insert at top of body
    if (document.body.firstChild) {
        document.body.insertBefore(banner, document.body.firstChild);
    } else {
        document.body.appendChild(banner);
    }

    console.log('Aegis: Warning banner displayed');
}

// Report scammer to backend
function reportScammer(url, reason, buttonElement) {
    // Disable button to prevent double submission
    buttonElement.disabled = true;
    buttonElement.innerHTML = '⏳ Reporting...';
    buttonElement.style.opacity = '0.7';

    fetch('http://127.0.0.1:8000/scout/add', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: url,
            reason: reason || 'Manually reported by user',
            source: 'user_report'
        }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Aegis: Scammer reported successfully');
        
        // Update button to show success
        buttonElement.innerHTML = '✅ Reported!';
        buttonElement.style.backgroundColor = '#22c55e';
        buttonElement.style.color = 'white';
        
        // Show success message in banner
        const banner = document.getElementById('aegis-banner');
        if (banner) {
            banner.style.backgroundColor = '#22c55e';
        }
        
        setTimeout(() => {
            alert('Thank you! This scammer has been reported to Aegis threat intelligence.');
        }, 500);
    })
    .catch(error => {
        console.error('Aegis: Failed to report scammer:', error);
        
        // Re-enable button on error
        buttonElement.disabled = false;
        buttonElement.innerHTML = '🚨 Report Scammer';
        buttonElement.style.opacity = '1';
        
        alert('Failed to report scammer. Please try again.');
    });
}
