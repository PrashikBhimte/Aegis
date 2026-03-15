import { CONFIG } from './config.js';

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url && 
        (tab.url.startsWith('http://') || tab.url.startsWith('https://'))) {
        
        chrome.tabs.sendMessage(tabId, { action: "getPageContent" }, (response) => {
            if (chrome.runtime.lastError) return;

            if (response && response.url && response.text) {
                analyzePage(tabId, response.url, response.text);
            }
        });
    }
});

function analyzePage(tabId, url, text) {
    fetch(CONFIG.BASE_URL + CONFIG.ENDPOINTS.ANALYZE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url, text: text }),
    })
    .then(res => res.json())
    .then(analysis => {
        if (analysis.is_scam) {
            chrome.tabs.sendMessage(tabId, {
                type: 'SHOW_WARNING',
                reason: analysis.reason,
                url: url
            });
            speakWarning(analysis.reason);
        }
    })
    .catch(() => {});
}

function speakWarning(reason) {
    chrome.storage.local.get(['muteState'], (result) => {
        if (result.muteState !== true) {
            const speakText = `Alert! Aegis has detected a potential scam. ${reason}`;
            
            chrome.tts.speak(speakText, {
                rate: 1.0,
                pitch: 1.0,
                volume: 1.0
            }, function() {
                if (chrome.runtime.lastError) {
                    console.error('TTS Error: ' + chrome.runtime.lastError.message);
                }
            });
        }
    });
}
