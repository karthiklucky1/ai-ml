// extension/background.js
const API_BASE = "http://127.0.0.1:8000";

async function postJSON(path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
    const data = await res.json();
    return data;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
    (async () => {
        try {
            if (msg?.type === "SPE_POST") {
                const data = await postJSON(msg.path, msg.body);
                sendResponse({ ok: true, data });
                return;
            }
            sendResponse({ ok: false, error: "Unknown message type" });
        } catch (e) {
            sendResponse({ ok: false, error: String(e) });
        }
    })();

    // IMPORTANT: keep the message channel open for async response
    return true;
});
