// // 1️⃣ Find input box
// const inputBox = document.querySelector("textarea");

// // 2️⃣ Helper functions
// async function fetchScore(prompt) {
//     const res = await fetch("http://127.0.0.1:8000/score", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ prompt })
//     });
//     return await res.json();
// }

// async function fetchSuggestions(prompt) {
//     const res = await fetch("http://127.0.0.1:8000/suggest", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ prompt })
//     });
//     return await res.json();
// }

// async function fetchOptimized(prompt, answers = {}) {
//     const res = await fetch("http://127.0.0.1:8000/optimize", {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify({ prompt, answers })
//     });
//     return await res.json();
// }

// // 3️⃣ Display suggestions & score
// inputBox.addEventListener("input", async () => {
//     const prompt = inputBox.value;

//     const scoreData = await fetchScore(prompt);
//     showScore(scoreData);

//     const suggestions = await fetchSuggestions(prompt);
//     showSuggestions(suggestions.questions);
// });

// // 4️⃣ Optimize button
// let optimizeBtn = document.createElement("button");
// optimizeBtn.innerText = "Optimize Prompt";
// inputBox.parentNode.appendChild(optimizeBtn);

// optimizeBtn.addEventListener("click", async () => {
//     const answers = {
//         task: "classification",
//         output: "Python code",
//         level: "beginner-friendly"
//     };
//     const optimized = await fetchOptimized(inputBox.value, answers);
//     inputBox.value = optimized.optimized_prompt;
// });

// // 5️⃣ Helper display functions
// function showScore(data) {
//     let div = document.getElementById("scoreDiv");
//     if (!div) {
//         div = document.createElement("div");
//         div.id = "scoreDiv";
//         inputBox.parentNode.appendChild(div);
//     }
//     div.innerText = `Score: ${data.score} (${data.quality})`;
// }

// function showSuggestions(questions) {
//     let div = document.getElementById("sugDiv");
//     if (!div) {
//         div = document.createElement("div");
//         div.id = "sugDiv";
//         div.style.background = "#f9f9f9";
//         div.style.padding = "8px";
//         inputBox.parentNode.appendChild(div);
//     }
//     div.innerHTML = questions.map(q => `<p>${q}</p>`).join("");
// }

// const textarea = document.getElementById("prompt-textarea");

// textarea.addEventListener("input", async () => {
//     const prompt = textarea.value;
//     const largeText = document.getElementById("large-text-input").value;

//     if (largeText && largeText.length > 200) { // threshold
//         const response = await fetch("http://127.0.0.1:8000/optimize_context", {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({ prompt: prompt, text: largeText })
//         });
//         const data = await response.json();

//         const hintBox = document.getElementById("hint-box");
//         hintBox.innerHTML = `
//             💡 You can reduce tokens by ${data.tokens_saved}<br>
//             Suggested context:<br>${data.optimized_context}
//         `;
//     }
// });

// extension / content.js
// const API_BASE = "http://127.0.0.1:8000";

// function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// async function postJSON(path, body) {
//     const res = await fetch(`${API_BASE}${path}`, {
//         method: "POST",
//         headers: { "Content-Type": "application/json" },
//         body: JSON.stringify(body)
//     });
//     return await res.json();
// }

// function findTextarea() {
//     // ChatGPT textarea tends to be a <textarea> in the composer
//     return document.querySelector("textarea");
// }

// function createWidget() {
//     const box = document.createElement("div");
//     box.id = "spe-inline";
//     box.style.position = "fixed";
//     box.style.right = "16px";
//     box.style.bottom = "120px";
//     box.style.width = "320px";
//     box.style.zIndex = "999999";
//     box.style.background = "white";
//     box.style.border = "1px solid #ddd";
//     box.style.borderRadius = "12px";
//     box.style.padding = "10px";
//     box.style.boxShadow = "0 6px 18px rgba(0,0,0,0.12)";
//     box.style.fontFamily = "system-ui, -apple-system, Segoe UI, Roboto";

//     box.innerHTML = `
//     <div style="font-weight:700;margin-bottom:6px;">Smart Prompt Engine</div>
//     <div id="spe-score" style="font-size:13px;">Score: -- | Intent: --</div>
//     <div id="spe-missing" style="font-size:12px;color:#555;margin-top:6px;">Missing: --</div>
//     <button id="spe-best" style="margin-top:8px;width:100%;padding:8px;border-radius:10px;border:1px solid #ccc;background:#f7f7f7;cursor:pointer;">
//       Use Best Rewrite
//     </button>
//     <div id="spe-status" style="font-size:12px;color:#777;margin-top:6px;"></div>
//   `;

//     document.body.appendChild(box);
//     return box;
// }

// let widget = null;
// let timer = null;
// let lastRewrite = null;

// async function updateForText(text) {
//     if (!widget) return;
//     const scoreEl = widget.querySelector("#spe-score");
//     const missEl = widget.querySelector("#spe-missing");
//     const statusEl = widget.querySelector("#spe-status");

//     // local score first
//     try {
//         const s = await postJSON("/score", { prompt: text });
//         scoreEl.textContent = `Score: ${s.score ?? "--"} | Intent: ${s.intent ?? "other"}`;
//     } catch {
//         scoreEl.textContent = "Score: -- | Intent: --";
//     }

//     // LLM rewrite suggestions (only if text is not tiny)
//     if (text.trim().length < 10) {
//         missEl.textContent = "Missing: --";
//         lastRewrite = null;
//         return;
//     }

//     statusEl.textContent = "Getting rewrite...";
//     try {
//         const r = await postJSON("/rewrite_suggestions", { prompt: text });
//         if (r.error) {
//             statusEl.textContent = `LLM unavailable`;
//             missEl.textContent = "Missing: --";
//             lastRewrite = null;
//             return;
//         }
//         lastRewrite = r;
//         const missing = Array.isArray(r.missing_info) ? r.missing_info.map(x => x.field).slice(0, 4) : [];
//         missEl.textContent = missing.length ? `Missing: ${missing.join(", ")}` : "Missing: none ✅";
//         statusEl.textContent = "";
//     } catch {
//         statusEl.textContent = "Rewrite failed";
//         missEl.textContent = "Missing: --";
//         lastRewrite = null;
//     }
// }

// async function main() {
//     widget = createWidget();
//     const btn = widget.querySelector("#spe-best");
//     btn.addEventListener("click", async () => {
//         const ta = findTextarea();
//         if (!ta || !lastRewrite) return;

//         const cards = Array.isArray(lastRewrite.rewrite_cards) ? lastRewrite.rewrite_cards : [];
//         if (!cards.length) return;

//         // Use first card as "best" for now
//         ta.value = cards[0];
//         ta.dispatchEvent(new Event("input", { bubbles: true }));

//         // Feedback
//         try {
//             await postJSON("/feedback", {
//                 type: "rewrite_click",
//                 prompt: (ta.value || ""),
//                 intent: lastRewrite.intent || "other",
//                 card_index: 0,
//                 card_text: cards[0]
//             });
//         } catch { }
//     });

//     while (true) {
//         const ta = findTextarea();
//         if (ta) {
//             ta.addEventListener("input", () => {
//                 clearTimeout(timer);
//                 const text = ta.value || "";
//                 timer = setTimeout(() => updateForText(text), 800);
//             });
//         }
//         await sleep(2000);
//     }
// }

// main();

// extension/content.js
// Inline "Grammarly-style" widget for Smart Prompt Engine
// Runs on chatgpt.com / openai.com pages via manifest content_scripts

// extension/content.js
// Inline "Grammarly-style" widget for Smart Prompt Engine
// Runs on chatgpt.com / openai.com pages via manifest content_scripts
console.log("SPE content.js loaded ✅");

const API_BASE = "http://127.0.0.1:8000";

function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
}

// ✅ IMPORTANT: use background proxy (avoids page CSP)
function postJSON(path, body) {
    return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: "SPE_POST", path, body }, (resp) => {
            const err = chrome.runtime.lastError;
            if (err) return reject(err.message);

            if (!resp) return reject("No response from background");
            if (!resp.ok) return reject(resp.error || "Background error");
            resolve(resp.data);
        });
    });
}

function findPromptBox() {
    // 1) Preferred: visible textarea (not display:none)
    const ta = document.querySelector("textarea[name='prompt-textarea']");
    if (ta && ta.offsetParent !== null) return { type: "textarea", el: ta };

    // 2) ChatGPT often uses contenteditable textbox
    const ce =
        document.querySelector("div[contenteditable='true'][role='textbox']") ||
        document.querySelector("div[contenteditable='true']");
    if (ce && ce.offsetParent !== null) return { type: "contenteditable", el: ce };

    // 3) Fallback: any visible textarea
    const anyTa = Array.from(document.querySelectorAll("textarea")).find(
        (x) => x.offsetParent !== null
    );
    if (anyTa) return { type: "textarea", el: anyTa };

    return null;
}

function getPromptText(box) {
    if (!box) return "";
    if (box.type === "textarea") return box.el.value || "";
    // ✅ ProseMirror/contenteditable: textContent works better for paste + large text
    return box.el.textContent || "";
}

function setPromptText(box, text) {
    if (!box) return;
    if (box.type === "textarea") {
        box.el.value = text;
        box.el.dispatchEvent(new Event("input", { bubbles: true }));
        return;
    }
    box.el.focus();
    box.el.textContent = text;
    box.el.dispatchEvent(new Event("input", { bubbles: true }));
}

function createWidget() {
    const existing = document.getElementById("spe-inline");
    if (existing) return existing;

    const box = document.createElement("div");
    box.id = "spe-inline";
    box.style.position = "fixed";
    box.style.right = "16px";
    box.style.bottom = "120px";
    box.style.width = "340px";
    box.style.zIndex = "999999";
    box.style.background = "white";
    box.style.border = "1px solid #ddd";
    box.style.borderRadius = "14px";
    box.style.padding = "12px";
    box.style.boxShadow = "0 6px 18px rgba(0,0,0,0.12)";
    box.style.fontFamily = "system-ui, -apple-system, Segoe UI, Roboto";
    box.style.color = "#111";

    box.innerHTML = `
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <div style="font-weight:700;">Smart Prompt Engine</div>
      <button id="spe-close" style="border:none;background:transparent;cursor:pointer;font-size:16px;">✕</button>
    </div>

    <div id="spe-score" style="font-size:13px;margin-top:6px;">Score: -- | Intent: --</div>
    <div id="spe-missing" style="font-size:12px;color:#555;margin-top:6px;">Missing: --</div>
    <div id="spe-status" style="font-size:12px;color:#777;margin-top:8px;"></div>

    <div id="spe-token" style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;">
      <div style="font-weight:600;font-size:13px;">Token Saver</div>
      <div id="spe-token-status" style="font-size:12px;color:#666;margin-top:4px;">
        Paste large text/code/data to enable (or 5+ CSV rows).
      </div>

      <button id="spe-compress" disabled style="margin-top:8px;width:100%;padding:9px;border-radius:12px;border:1px solid #ccc;background:#f7f7f7;cursor:pointer;">
        Compress (Token Saver)
      </button>

      <div id="spe-token-actions" style="display:none;margin-top:8px;">
        <button id="spe-use-compressed" style="width:100%;padding:8px;border-radius:12px;border:1px solid #ccc;background:#fff;cursor:pointer;">
          Use Compressed
        </button>
        <button id="spe-use-full" style="width:100%;padding:8px;border-radius:12px;border:1px solid #ccc;background:#fff;cursor:pointer;margin-top:6px;">
          Use Full
        </button>
      </div>
    </div>

    <button id="spe-best" disabled style="margin-top:10px;width:100%;padding:9px;border-radius:12px;border:1px solid #ccc;background:#f7f7f7;cursor:pointer;">
      Use Best Rewrite
    </button>
  `;

    document.body.appendChild(box);
    box.querySelector("#spe-close").onclick = () => box.remove();
    return box;
}

// -------------------- State --------------------
let widget = createWidget();
let debounceTimer = null;
let lastRewrite = null;

// --- A: Stability helpers ---
const SCORE_DEBOUNCE_MS = 1200;
const LLM_MIN_LEN = 25;
const LLM_SCORE_THRESHOLD = 75;

let lastSentText = "";
let lastMeaningfulText = "";
let lastCallId = 0;
let rewriteLocked = false;
let lockedText = "";

// simple in-memory caches (avoid repeated hits)
const scoreCache = new Map(); // key: prompt -> response
const llmCache = new Map();   // key: prompt -> response

// Token Saver state
let tokenUIReady = false;
let tokenInputText = ""; // latest large text
let lastToken = null;    // backend /compress response
let lastFullText = "";

function normalizeText(t) {
    // Preserve line breaks (important for CSV/code/log detection), normalize per-line spacing.
    return (t || "")
        .split("\n")
        .map((ln) => ln.trim().replace(/[ \t]+/g, " "))
        .join("\n")
        .trim();
}

function isMeaningfulChange(prev, next) {
    if ((prev || "") === (next || "")) return false;
    if (!prev) return true;
    const deltaLen = Math.abs(next.length - prev.length);
    if (deltaLen >= 6) return true;
    const prevEnd = prev.slice(-1);
    const nextEnd = next.slice(-1);
    if (prevEnd !== nextEnd && (nextEnd === "." || nextEnd === "?" || nextEnd === "!")) return true;
    const prevNl = (prev.match(/\n/g) || []).length;
    const nextNl = (next.match(/\n/g) || []).length;
    if (prevNl !== nextNl) return true;
    const prevLast = prev.split(" ").slice(-3).join(" ");
    const nextLast = next.split(" ").slice(-3).join(" ");
    return prevLast !== nextLast;
}

// -------------------- Token Saver helpers --------------------
function formatPct(before, after) {
    if (!before) return 0;
    return Math.round(((before - after) / before) * 100);
}

function detectLargePaste(prompt) {
    const raw = (prompt || "").trim();
    if (!raw) return null;
    if (raw.length >= 400) return raw; // default threshold

    // Allow smaller tabular payloads (CSV/TSV-like) to use Token Saver.
    const lines = raw.split("\n").map((ln) => ln.trim()).filter(Boolean);
    if (lines.length >= 5) {
        const delimiterLines = lines.filter((ln) => /[,;\t|]/.test(ln)).length;
        if (delimiterLines >= 5) return raw;
    }

    return null;
}

function isTokenSavable(text) {
    return !!detectLargePaste(text);
}

function tokenSaverHint() {
    return "Paste large text/code/data to enable (or 5+ CSV rows).";
}

function tokenSaverReadyText(chars) {
    return `Detected: (ready). Chars: ${chars}. Click Compress.`;
}

function initTokenSaverUI() {
    if (tokenUIReady) return;
    tokenUIReady = true;

    const compressBtn = widget.querySelector("#spe-compress");
    const tokenStatus = widget.querySelector("#spe-token-status");
    const tokenActions = widget.querySelector("#spe-token-actions");
    const useCompressedBtn = widget.querySelector("#spe-use-compressed");
    const useFullBtn = widget.querySelector("#spe-use-full");

    if (!compressBtn || !tokenStatus || !tokenActions || !useCompressedBtn || !useFullBtn) {
        console.warn("[SPE] Token Saver UI missing ids. Check createWidget HTML.");
        return;
    }

    compressBtn.onclick = async () => {
        if (!tokenInputText || !isTokenSavable(tokenInputText)) return;

        tokenStatus.textContent = "Compressing…";
        tokenActions.style.display = "none";
        lastFullText = tokenInputText;

        try {
            const res = await postJSON("/compress", { text: tokenInputText });
            lastToken = res;

            const before = res?.stats?.chars_in ?? tokenInputText.length;
            const after = res?.stats?.chars_out ?? (res?.compressed ? res.compressed.length : before);
            const saved = formatPct(before, after);
            const dtype = res?.detected_type || "unknown";

            if (after >= before) {
                tokenStatus.textContent = `Detected: ${dtype}. Chars: ${before} → ${after} (no savings).`;
                tokenActions.style.display = "none";
                return;
            }

            tokenStatus.textContent = `Detected: ${dtype}. Chars: ${before} → ${after} (save ~${saved}%).`;
            tokenActions.style.display = "block";
        } catch (e) {
            console.error("[SPE] /compress failed:", e);
            tokenStatus.textContent = "Compress failed";
            tokenActions.style.display = "none";
        }
    };

    useCompressedBtn.onclick = () => {
        const box = findPromptBox();
        if (!box || !lastToken?.compressed) return;
        setPromptText(box, lastToken.compressed);
        tokenActions.style.display = "none";
    };

    useFullBtn.onclick = () => {
        const box = findPromptBox();
        if (!box || !lastFullText) return;
        setPromptText(box, lastFullText);
        tokenActions.style.display = "none";
    };
}

// ✅ update token saver state (no onclick rebinding here)
function setupTokenSaverUI(trimmed) {
    initTokenSaverUI();

    const compressBtn = widget.querySelector("#spe-compress");
    const tokenStatus = widget.querySelector("#spe-token-status");
    const tokenActions = widget.querySelector("#spe-token-actions");

    if (!compressBtn || !tokenStatus || !tokenActions) return;

    const bigText = detectLargePaste(trimmed);

    if (!bigText) {
        tokenInputText = "";
        tokenStatus.textContent = tokenSaverHint();
        compressBtn.disabled = true;
        tokenActions.style.display = "none";
        lastToken = null;
        lastFullText = "";
        return;
    }

    tokenInputText = bigText;
    compressBtn.disabled = false;
    tokenActions.style.display = "none";
    tokenStatus.textContent = tokenSaverReadyText(bigText.length);
}

// -------------------- Main update flow --------------------
async function updateForText(text) {
    const callId = ++lastCallId;
    const trimmed = normalizeText(text);
    const scoreEl = widget.querySelector("#spe-score");
    const missEl = widget.querySelector("#spe-missing");
    const statusEl = widget.querySelector("#spe-status");
    const useBtn = widget.querySelector("#spe-best");

    if (!trimmed) {
        scoreEl.textContent = "Score: -- | Intent: --";
        missEl.textContent = "Missing: --";
        statusEl.textContent = "";
        useBtn.disabled = true;
        lastRewrite = null;
        rewriteLocked = false;
        lockedText = "";
        lastSentText = "";
        setupTokenSaverUI("");
        return;
    }

    lastSentText = trimmed;

    // ✅ Token saver should always update even for short prompts
    setupTokenSaverUI(trimmed);

    let localScore = null;

    // 1) score (cached)
    try {
        statusEl.textContent = "Scoring...";
        let s = scoreCache.get(trimmed);
        if (!s) {
            s = await postJSON("/score", { prompt: trimmed });
            scoreCache.set(trimmed, s);
        }

        if (callId !== lastCallId) return;
        localScore = s;

        const score = typeof s.score === "number" ? s.score : "--";
        const intent = s.intent || "other";
        scoreEl.textContent = `Score: ${score} | Intent: ${intent}`;
        statusEl.textContent = "";

        const scoreNum = typeof s.score === "number" ? s.score : 0;
        if (scoreNum >= 75) {
            missEl.textContent = "Missing: none ✅";
        } else {
            const dims = Array.isArray(s.missing_dimensions) ? s.missing_dimensions : [];
            const sug = Array.isArray(s.live_suggestions) ? s.live_suggestions : [];
            if (sug.length) {
                missEl.textContent = `Missing (suggested): ${sug.slice(0, 2).join(" | ")}`;
            } else if (dims.length) {
                missEl.textContent = `Missing (suggested): ${dims.slice(0, 3).join(", ")}`;
            } else {
                missEl.textContent = "Missing: add a few key details for a better answer.";
            }
        }
    } catch (e) {
        if (callId !== lastCallId) return;
        console.error("[SPE] /score failed:", e);
        scoreEl.textContent = "Score: -- | Intent: --";
        missEl.textContent = "Missing: --";
        statusEl.textContent = "Score failed";
    }

    // 2) LLM rewrite — only when worth it
    if (rewriteLocked) {
        const now = normalizeText(trimmed);
        if (!isMeaningfulChange(lockedText, now)) {
            setupTokenSaverUI(trimmed);
            return;
        }
        rewriteLocked = false;
        lockedText = "";
    }

    const localScoreNum = typeof localScore?.score === "number" ? localScore.score : 0;
    const shouldCallLLM =
        trimmed.length >= LLM_MIN_LEN &&
        localScoreNum < LLM_SCORE_THRESHOLD;

    if (!shouldCallLLM) {
        useBtn.disabled = true;
        lastRewrite = null;
        setupTokenSaverUI(trimmed);
        return;
    }

    try {
        statusEl.textContent = "Rewrite...";
        let r = llmCache.get(trimmed);
        if (!r) {
            r = await postJSON("/rewrite_suggestions", { prompt: trimmed });
            llmCache.set(trimmed, r);
        }

        if (callId !== lastCallId) return;

        if (r.error) {
            statusEl.textContent = "LLM unavailable";
            useBtn.disabled = true;
            lastRewrite = null;
            setupTokenSaverUI(trimmed);
            return;
        }

        lastRewrite = r;

        const req = Array.isArray(r.required_missing) ? r.required_missing : [];
        const opt = Array.isArray(r.optional_missing) ? r.optional_missing : [];

        const reqFields = req
            .map((x) => (typeof x === "string" ? x : x?.field))
            .filter(Boolean)
            .slice(0, 5);

        const optFields = opt
            .map((x) => (typeof x === "string" ? x : x?.field))
            .filter(Boolean)
            .slice(0, 3);

        missEl.textContent =
            `Missing (required): ${reqFields.length ? reqFields.join(", ") : "none ✅"} | ` +
            `Optional: ${optFields.length ? optFields.join(", ") : "none"}`;

        // Only overwrite local score if LLM score looks valid.
        if (typeof r.score === "number" && r.score > 0) {
            const llmIntent = (r.intent && r.intent !== "other") ? r.intent : null;
            const current = scoreEl.textContent || "";
            const currentIntentMatch = current.match(/Intent:\s*([a-zA-Z_]+)/);
            const currentIntent = currentIntentMatch ? currentIntentMatch[1] : "other";
            scoreEl.textContent = `Score: ${r.score} | Intent: ${llmIntent || currentIntent}`;
        }

        statusEl.textContent = "";
        useBtn.disabled = false;
    } catch (e) {
        if (callId !== lastCallId) return;
        console.error("[SPE] /rewrite_suggestions failed:", e);
        statusEl.textContent = "Rewrite failed";
        useBtn.disabled = true;
        lastRewrite = null;
    }

    setupTokenSaverUI(trimmed);
}

// -------------------- Binding loop --------------------
async function bindTextareaLoop() {
    const useBtn = widget.querySelector("#spe-best");

    useBtn.onclick = async () => {
        const box = findPromptBox();
        if (!box || !lastRewrite) return;

        const req = Array.isArray(lastRewrite.required_missing) ? lastRewrite.required_missing : [];
        const opt = Array.isArray(lastRewrite.optional_missing) ? lastRewrite.optional_missing : [];
        const cards = Array.isArray(lastRewrite.rewrite_cards) ? lastRewrite.rewrite_cards : [];

        // If nothing is missing, do not overwrite user's prompt.
        if (req.length === 0 && opt.length === 0) {
            const statusEl = widget.querySelector("#spe-status");
            if (statusEl) statusEl.textContent = "Looks complete ✅ No rewrite needed.";
            return;
        }

        if (!cards.length) return;

        const chosen = cards[0];
        setPromptText(box, chosen);

        try {
            await postJSON("/feedback", {
                type: "rewrite_click",
                prompt: chosen,
                intent: lastRewrite.intent || "other",
                card_index: 0,
                card_text: chosen,
            });
        } catch { }
    };

    while (true) {
        const box = findPromptBox();
        if (box && !box.el.dataset.speBound) {
            box.el.dataset.speBound = "1";

            box.el.addEventListener("input", () => {
                clearTimeout(debounceTimer);
                const text = getPromptText(box);
                debounceTimer = setTimeout(() => {
                    const clean = normalizeText(text);
                    if (!clean) return updateForText(clean);
                    if (!isMeaningfulChange(lastMeaningfulText, clean)) return;
                    lastMeaningfulText = clean;
                    updateForText(clean);
                }, SCORE_DEBOUNCE_MS);
            });

            const existing = getPromptText(box);
            if (existing.trim()) {
                const clean = normalizeText(existing);
                lastMeaningfulText = clean;
                updateForText(clean);
            }
            else setupTokenSaverUI(""); // init UI state
        }

        await sleep(1200);
    }
}

bindTextareaLoop();
