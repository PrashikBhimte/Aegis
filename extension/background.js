// Aegis-Live Guardian - Background Script
// Handles page analysis and audio alerts with mute support

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    // Check if the tab has finished loading and has a valid URL
    if (changeInfo.status === 'complete' && tab.url && 
        (tab.url.startsWith('http://') || tab.url.startsWith('https://'))) {
        
        console.log('Aegis: Analyzing page -', tab.url);
        
        // Get page content from content script
        chrome.tabs.sendMessage(tabId, { action: "getPageContent" }, (response) => {
            if (chrome.runtime.lastError) {
                console.error('Aegis: Content script error:', chrome.runtime.lastError.message);
                return;
            }

            if (response && response.url && response.text) {
                // Send the extracted content to the backend for analysis
                analyzePage(tabId, response.url, response.text);
            }
        });
    }
});

// Analyze page content via backend API
function analyzePage(tabId, url, text) {
    fetch('http://127.0.0.1:8000/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url: url,
            text: text,
        }),
    })
    .then(res => {
        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }
        return res.json();
    })
    .then(analysis => {
        if (analysis.is_scam) {
            console.log('Aegis: Threat detected -', analysis.reason);
            
            // Send message to content script to display a warning banner
            chrome.tabs.sendMessage(tabId, {
                type: 'SHOW_WARNING',
                reason: analysis.reason,
                url: url
            });

            // Speak the warning (only if not muted)
            speakWarning(analysis.reason);
        } else {
            console.log('Aegis: Page verified safe');
        }
    })
    .catch(error => {
        console.error('Aegis: Analysis error:', error.message);
    });
}

// Speak warning with mute state check
function speakWarning(reason) {
    // Check mute state from chrome.storage.local
    chrome.storage.local.get(['muteState'], (result) => {
        const isMuted = result.muteState === true;
        
        if (!isMuted) {
            // Audio alerts enabled - speak the warning
            chrome.tts.speak(`Alert! Aegis has detected a potential scam. ${reason}`, {
                rate: 1.0,
                pitch: 1.0,
                volume: 1.0,
                onError: (error) => {
                    console.error('Aegis: TTS error:', error);
                }
            });
            console.log('Aegis: Audio alert spoken');
        } else {
            console.log('Aegis: Audio alerts muted - no speech');
        }
    });
}

console.log('Aegis-Live Guardian: Background service initialized');
