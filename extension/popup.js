
document.addEventListener('DOMContentLoaded', () => {
    initializeMuteToggle();
    fetchHistory();
});

function initializeMuteToggle() {
    const muteToggle = document.getElementById('mute-toggle');
    const muteStatus = document.getElementById('mute-status');
    
    chrome.storage.local.get(['muteState'], (result) => {
        const isMuted = result.muteState === true;
        muteToggle.checked = isMuted;
        updateMuteStatus(isMuted);
    });
    
    muteToggle.addEventListener('change', (e) => {
        const isMuted = e.target.checked;
        chrome.storage.local.set({ muteState: isMuted }, () => {
            updateMuteStatus(isMuted);
        });
    });
}

function updateMuteStatus(isMuted) {
    const muteStatus = document.getElementById('mute-status');
    muteStatus.textContent = isMuted ? 'OFF' : 'ON';
    muteStatus.classList.toggle('muted', isMuted);
}

function timeSince(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    let interval = seconds / 31536000;
    if (interval > 1) return Math.floor(interval) + " years ago";
    interval = seconds / 2592000;
    if (interval > 1) return Math.floor(interval) + " months ago";
    interval = seconds / 86400;
    if (interval > 1) return Math.floor(interval) + " days ago";
    interval = seconds / 3600;
    if (interval > 1) return Math.floor(interval) + " hours ago";
    interval = seconds / 60;
    if (interval > 1) return Math.floor(interval) + " minutes ago";
    return Math.floor(seconds) + " seconds ago";
}

function renderHistory(historyData) {
    const historyList = document.getElementById('history-list');
    historyList.innerHTML = '';

    if (!historyData || historyData.length === 0) {
        historyList.innerHTML = '<div class="empty-state">No threats detected recently.</div>';
        return;
    }

    historyData.forEach(report => {
        const card = document.createElement('div');
        card.className = 'card';

        const url = document.createElement('div');
        url.className = 'url';
        url.textContent = report.url.length > 45 ? report.url.substring(0, 42) + '...' : report.url;
        url.title = report.url;

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

function fetchHistory() {
    fetch(CONFIG.BASE_URL + CONFIG.ENDPOINTS.HISTORY)
        .then(res => res.json())
        .then(data => renderHistory(data))
        .catch(() => {
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = '<div class="error-state">Connection error</div>';
        });
}
