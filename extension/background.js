// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  // Check if the tab has finished loading and has a URL
  if (changeInfo.status === 'complete' && tab.url && (tab.url.startsWith('http://') || tab.url.startsWith('https://'))) {
    // Get page content from content script
    chrome.tabs.sendMessage(tabId, { action: "getPageContent" }, (response) => {
      if (chrome.runtime.lastError) {
        console.error(chrome.runtime.lastError.message);
        return;
      }

      if (response && response.url && response.text) {
        // Send the extracted content to the backend for analysis
        fetch('http://127.0.0.1:8000/analyze', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            url: response.url,
            text: response.text,
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
            // Send message to content script to display a warning
            chrome.tabs.sendMessage(tabId, {
              type: 'SHOW_WARNING',
              reason: analysis.reason
            });

            // Speak the warning
            chrome.tts.speak(`Alert! Aegis has detected a potential scam. ${analysis.reason}`, {
              rate: 1.0,
              pitch: 1.0
            });
          }
        })
        .catch(error => {
          console.error('Aegis-Live Analysis Error:', error);
        });
      }
    });
  }
});
