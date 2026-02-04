// extension/background.js
const API_BASES = [
    "http://127.0.0.1:8000",
    "https://smart-prompt-engine.onrender.com",
];
const USER_KEY = "spe_user_id";

async function getUserId() {
    const data = await chrome.storage.local.get([USER_KEY]);
    if (data[USER_KEY]) return data[USER_KEY];

    const id = crypto.randomUUID();
    await chrome.storage.local.set({ [USER_KEY]: id });
    return id;
}

chrome.runtime.onInstalled.addListener(async () => {
    await getUserId();
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type !== "SPE_POST") return;

    (async () => {
        try {
            const userId = await getUserId();
            let lastError = null;

            for (const apiBase of API_BASES) {
                try {
                    const res = await fetch(`${apiBase}${msg.path}`, {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json",
                            "X-SPE-User": userId,
                        },
                        body: JSON.stringify(msg.body || {}),
                    });

                    const data = await res.json().catch(() => ({}));
                    if (res.ok) {
                        sendResponse({ ok: true, status: res.status, data, error: null });
                        return;
                    }
                    lastError = data?.error || `HTTP ${res.status}`;
                } catch (e) {
                    lastError = String(e);
                }
            }
            sendResponse({ ok: false, error: lastError || "All backends failed", data: null });
        } catch (e) {
            sendResponse({ ok: false, error: String(e), data: null });
        }
    })();

    return true;
});
