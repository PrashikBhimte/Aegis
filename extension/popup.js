// Aegis-Live Threat Vault - Popup Script
// Handles mute toggle state and threat history display

// Initialize mute toggle on load
document.addEventListener('DOMContentLoaded', () => {
    initializeMuteToggle();
    fetchHistory();
});

// Initialize mute toggle with chrome.storage.local
function initializeMuteToggle() {
    const muteToggle = document.getElementById('mute-toggle');
    const muteStatus = document.getElementById('mute-status');
    
    // Load saved mute state from chrome.storage.local
    chrome.storage.local.get(['muteState'], (result) => {
        const isMuted = result.muteState === true;
        muteToggle.checked = isMuted;
        updateMuteStatus(isMuted);
    });
    
    // Listen for toggle changes
    muteToggle.addEventListener('change', (e) => {
        const isMuted = e.target.checked;
        
        // Save state to chrome.storage.local
        chrome.storage.local.set({ muteState: isMuted }, () => {
            if (chrome.runtime.lastError) {
                console.error('Aegis: Failed to save mute state:', chrome.runtime.lastError);
            } else {
                console.log('Aegis: Mute state updated to:', isMuted ? 'MUTED' : 'ACTIVE');
            }
        });
        
        updateMuteStatus(isMuted);
    });
}

// Update mute status display
function updateMuteStatus(isMuted) {
    const muteStatus = document.getElementById('mute-status');
    if (isMuted) {
        muteStatus.textContent = 'OFF';
        muteStatus.classList.add('muted');
    } else {
        muteStatus.textContent = 'ON';
        muteStatus.classList.remove('muted');
    }
}

// Function to calculate time since the event
function timeSince(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) {
        return Math.floor(interval) + " years ago";
    }
    interval = seconds / 2592000;
    if (interval > 1) {
        return Math.floor(interval) + " months ago";
    }
    interval = seconds / 86400;
    if (interval > 1) {
        return Math.floor(interval) + " days ago";
    }
    interval = seconds / 3600;
    if (interval > 1) {
        return Math.floor(interval) + " hours ago";
    }
    interval = seconds / 60;
    if (interval > 1) {
        return Math.floor(interval) + " minutes ago";
    }
    return Math.floor(seconds) + " seconds ago";
}

// Function to render history cards
function renderHistory(historyData) {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = ''; // Clear existing list

    if (!historyData || historyData.length === 0) {
        historyList.innerHTML = '<div class="empty-state">No threats detected recently. Stay safe! 🛡️</div>';
        return;
    }

    historyData.forEach(report => {
        const card = document.createElement('div');
        card.className = 'card';

        const url = document.createElement('div');
        url.className = 'url';
        // Truncate URL for display
        url.textContent = report.url.length > 45 ? report.url.substring(0, 42) + '...' : report.url;
        url.title = report.url; // Show full URL on hover

        const reason = document.createElement('div');
        reason.className = 'reason';
        reason.textContent = `Reason: ${report.reason}`;

        const time = document.createElement('div');
        time.className = 'time';
        const reportDate = new Date(report.timestamp);
        time.textContent = timeSince(reportDate);

        card.appendChild(url);
        card.appendChild(reason);
        card.appendChild(time);
        historyList.appendChild(card);
    });
}

// Fetch history when the popup is opened
function fetchHistory() {
    fetch('http://127.0.0.1:8000/history')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server returned: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Aegis: Threat history loaded successfully');
            renderHistory(data);
        })
        .catch(error => {
            console.error('Aegis: Failed to fetch threat history:', error);
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = `<div class="error-state">⚠️ Connection Error: Could not reach Aegis backend.</div>`;
        });
}
