const API_BASES = [
    "http://127.0.0.1:8000",
    "https://smart-prompt-engine.onrender.com",
];

const promptInput = document.getElementById("promptInput");
const scoreValue = document.getElementById("scoreValue");
const scoreBar = document.getElementById("scoreBar");
const intentText = document.getElementById("intentText");
const optimizeBtn = document.getElementById("optimizeBtn");
const optimizedOutput = document.getElementById("optimizedOutput");
const llmRewriteCardsDiv = document.getElementById("llmRewriteCards");
const llmMissingDiv = document.getElementById("llmMissing");

const compressBtn = document.getElementById("compressBtn");
const compressStatus = document.getElementById("compressStatus");
const compressPreview = document.getElementById("compressPreview");
const useCompressedBtn = document.getElementById("useCompressedBtn");
const useFullBtn = document.getElementById("useFullBtn");


let debounceTimer = null;
let lastPrompt = "";
let lastScoreResult = null;
let inFlightScore = false;
let llmTimer = null;
let llmCache = new Map(); // prompt -> result

let lastCompression = null;
let lastFullText = "";

async function postWithFallback(path, payload) {
    let lastError = null;
    for (const apiBase of API_BASES) {
        try {
            const res = await fetch(`${apiBase}${path}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload || {})
            });
            if (!res.ok) {
                const text = await res.text();
                lastError = `${res.status} ${text}`;
                continue;
            }
            return await res.json();
        } catch (e) {
            lastError = String(e);
        }
    }
    throw new Error(`All backends failed: ${lastError || "unknown error"}`);
}

function setLoadingUI() {
    scoreValue.textContent = "...";
    intentText.textContent = "Intent: ...";
}

function setEmptyUI() {
    scoreValue.textContent = "--";
    intentText.textContent = "Intent: --";
    scoreBar.style.width = "0%";

    if (llmRewriteCardsDiv) llmRewriteCardsDiv.innerHTML = "";
    if (llmMissingDiv) llmMissingDiv.textContent = "--";

    optimizeBtn.disabled = true;
    optimizedOutput.textContent = "(Click Optimize)";
    lastScoreResult = null;
}


function escapeHtml(str) {
    return String(str)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function renderScore(result) {
    lastScoreResult = result;

    const score = typeof result.score === "number" ? result.score : 0;
    const intent = result.intent || "other";

    scoreValue.textContent = `${score}/100`;
    scoreBar.style.width = `${Math.max(0, Math.min(100, score))}%`;
    intentText.textContent = `Intent: ${intent}`;

    // enable optimize only if weak (optional)
    optimizeBtn.disabled = score >= 75;

    // Call LLM suggestions only when needed
    clearTimeout(llmTimer);

    if (score < 65) {
        const prompt = promptInput.value.trim();
        llmTimer = setTimeout(async () => {
            try {
                const data = await callRewriteSuggestions(prompt);
                renderLLMRewrite(data);
            } catch (e) {
                if (llmMissingDiv) llmMissingDiv.textContent = "LLM call failed.";
                console.error(e);
            }
        }, 900);
    } else {
        if (llmRewriteCardsDiv) llmRewriteCardsDiv.innerHTML = "";
        if (llmMissingDiv) llmMissingDiv.textContent = "--";
    }
}


async function callScoreAPI(prompt) {
    if (inFlightScore) return;
    inFlightScore = true;

    try {
        const result = await postWithFallback("/score", { prompt });
        renderScore(result);
    } catch (err) {
        scoreValue.textContent = "ERR";
        intentText.textContent = "Intent: --";
        if (llmMissingDiv) {
            llmMissingDiv.textContent =
                "Could not reach backend. Tried local (127.0.0.1:8000) and Render.";
        }
        console.error(err);
        optimizeBtn.disabled = true;
    } finally {
        inFlightScore = false;
    }
}

function scheduleScore(prompt) {
    clearTimeout(debounceTimer);

    debounceTimer = setTimeout(async () => {
        if (prompt.trim() === "") {
            setEmptyUI();
            return;
        }

        if (prompt === lastPrompt) return;
        lastPrompt = prompt;

        setLoadingUI();
        await callScoreAPI(prompt);
    }, 450);
}

async function callOptimizeAPI(prompt) {
    optimizedOutput.textContent = "Optimizing...";

    try {
        const result = await postWithFallback("/optimize", { prompt });

        // Your backend returns either:
        // { optimized_prompt: "..."} OR { optimized_prompt: "...", needs_improvement: true, intent: "..."}
        const opt = result.optimized_prompt || "(No optimized prompt returned)";
        optimizedOutput.textContent = opt;

        // (Optional) replace the textbox with the optimized prompt
        // promptInput.value = opt;

    } catch (err) {
        optimizedOutput.textContent = "Optimize failed. Check backend logs.";
        console.error(err);
    }
}

// Init
setEmptyUI();

promptInput.addEventListener("input", (e) => {
    scheduleScore(e.target.value);
});

// Optimize button click
optimizeBtn.addEventListener("click", async () => {
    const prompt = promptInput.value.trim();
    if (!prompt) return;
    await callOptimizeAPI(prompt);
});


compressBtn.addEventListener("click", async () => {
    const text = (promptInput.value || "").trim();
    if (!text) {
        compressStatus.textContent = "Nothing to compress.";
        return;
    }

    compressStatus.textContent = "Compressing...";
    useCompressedBtn.disabled = true;
    useFullBtn.disabled = true;
    compressPreview.textContent = "(Working...)";

    try {
        lastFullText = text;
        const data = await callCompress(text);
        lastCompression = data;

        const stats = data.stats || {};
        const inChars = stats.chars_in ?? text.length;
        const outChars = stats.chars_out ?? (data.compressed || "").length;
        const saved = inChars > 0 ? Math.round(100 * (1 - (outChars / inChars))) : 0;

        compressStatus.textContent =
            `Detected: ${data.detected_type}. Chars: ${inChars} → ${outChars} (save ~${saved}%).`;

        compressPreview.textContent = data.compressed || "(Empty result)";

        useCompressedBtn.disabled = false;
        useFullBtn.disabled = false;
    } catch (e) {
        console.error(e);
        compressStatus.textContent = "Compression failed.";
        compressPreview.textContent = "(Error)";
    }
});

useCompressedBtn.addEventListener("click", () => {
    if (!lastCompression || !lastCompression.compressed) return;
    promptInput.value = lastCompression.compressed;
    scheduleScore(promptInput.value);
});

useFullBtn.addEventListener("click", () => {
    if (!lastFullText) return;
    promptInput.value = lastFullText;
    scheduleScore(promptInput.value);
});


async function callRewriteSuggestions(prompt) {
    // cache
    if (llmCache.has(prompt)) return llmCache.get(prompt);

    const data = await postWithFallback("/rewrite_suggestions", { prompt });
    llmCache.set(prompt, data);
    return data;
}

function renderLLMRewrite(data) {

    if (typeof data.score === "number") {
        const s = Math.max(0, Math.min(100, data.score));
        scoreValue.textContent = `${s}/100`;
        scoreBar.style.width = `${s}%`;
    }

    if (!llmRewriteCardsDiv || !llmMissingDiv) return;

    llmRewriteCardsDiv.innerHTML = "";
    llmMissingDiv.textContent = "--";

    if (data.error) {
        llmMissingDiv.textContent = `LLM not available: ${data.error}`;
        return;
    }

    const missing = Array.isArray(data.missing_info) ? data.missing_info : [];
    const cards = Array.isArray(data.rewrite_cards) ? data.rewrite_cards : [];

    if (missing.length) {
        llmMissingDiv.textContent =
            "Missing: " + missing.slice(0, 6).map(x => x.field).join(", ");
    } else {
        llmMissingDiv.textContent = "No major missing info ✅";
    }

    cards.slice(0, 3).forEach((text, idx) => {
        const btn = document.createElement("button");
        btn.textContent = `Use LLM Suggestion ${idx + 1}`;
        btn.style.marginTop = "6px";
        btn.style.padding = "8px";
        btn.style.width = "100%";
        btn.onclick = () => {
            promptInput.value = text;
            scheduleScore(text);

            postWithFallback("/feedback", {
                    type: "rewrite_click",
                    prompt: text,
                    intent: data.intent || "other",
                    card_index: idx,
                    card_text: text
                })
                .then(() => { })
                .catch(e => console.warn("feedback failed", e));
        };

        llmRewriteCardsDiv.appendChild(btn);
    });

    if (cards.length === 0) {
        llmRewriteCardsDiv.innerHTML = `<span class="muted">No LLM rewrite cards returned.</span>`;
    }

}


async function callCompress(text) {
    return await postWithFallback("/compress", { text });
}
