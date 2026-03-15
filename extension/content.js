// This script is injected into the active tab.

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getPageContent") {
    const pageContent = {
      url: window.location.href,
      text: document.body.innerText,
    };
    sendResponse(pageContent);
    return true; // Keep the message channel open for the response
  }

  if (request.type === "SHOW_WARNING") {
    displayWarningBanner(request.reason);
  }
});

function displayWarningBanner(reason) {
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
  banner.style.backgroundColor = 'red';
  banner.style.color = 'white';
  banner.style.padding = '10px';
  banner.style.textAlign = 'center';
  banner.style.zIndex = '999999';
  banner.style.fontSize = '16px';
  banner.style.fontWeight = 'bold';
  banner.style.fontFamily = 'sans-serif';

  banner.innerHTML = `⚠️ AEGIS WARNING: Potential Phishing Detected! Reason: ${reason}`;

  document.body.prepend(banner);
}
