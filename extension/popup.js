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
        historyList.innerHTML = '<div style="text-align: center; color: #94a3b8;">No threats detected recently.</div>';
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
document.addEventListener('DOMContentLoaded', () => {
    fetch('http://127.0.0.1:8000/history')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            renderHistory(data);
        })
        .catch(error => {
            console.error('Failed to fetch threat history:', error);
            const historyList = document.getElementById('history-list');
            historyList.innerHTML = `<div style="text-align: center; color: #ef4444;">Error: Could not connect to Aegis backend.</div>`;
        });
});
