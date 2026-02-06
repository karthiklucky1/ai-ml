function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
}

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

function getSite() {
    const h = location.hostname;
    if (h.includes("chatgpt.com") || h.includes("chat.openai.com")) return "chatgpt";
    if (h.includes("gemini.google.com")) return "gemini";
    if (h.includes("claude.ai")) return "claude";
    return "unknown";
}

function findPromptBox() {
    const site = getSite();

    if (site === "chatgpt") {
        const ta = document.querySelector("textarea[name='prompt-textarea']");
        if (ta && ta.offsetParent !== null) return { site, type: "textarea", el: ta };

        const ce =
            document.querySelector("div[contenteditable='true'][role='textbox']") ||
            document.querySelector("div[contenteditable='true']#prompt-textarea") ||
            document.querySelector("div[contenteditable='true']");
        if (ce && ce.offsetParent !== null) return { site, type: "contenteditable", el: ce };

        const anyTa = Array.from(document.querySelectorAll("textarea")).find(
            (x) => x.offsetParent !== null
        );
        if (anyTa) return { site, type: "textarea", el: anyTa };
        return null;
    }

    if (site === "gemini") {
        const ce =
            document.querySelector("div[contenteditable='true'][role='textbox']") ||
            document.querySelector("div[contenteditable='true']");
        if (ce && ce.offsetParent !== null) return { site, type: "contenteditable", el: ce };

        const ta = Array.from(document.querySelectorAll("textarea")).find(
            (x) => x.offsetParent !== null
        );
        if (ta) return { site, type: "textarea", el: ta };
        return null;
    }

    if (site === "claude") {
        const ce =
            document.querySelector("div[contenteditable='true'][role='textbox']") ||
            document.querySelector("div[contenteditable='true']");
        if (ce && ce.offsetParent !== null) return { site, type: "contenteditable", el: ce };

        const ta = Array.from(document.querySelectorAll("textarea")).find(
            (x) => x.offsetParent !== null
        );
        if (ta) return { site, type: "textarea", el: ta };
        return null;
    }

    const ce =
        document.querySelector("div[contenteditable='true'][role='textbox']") ||
        document.querySelector("div[contenteditable='true']");
    if (ce && ce.offsetParent !== null) return { site: "unknown", type: "contenteditable", el: ce };

    const anyTa = Array.from(document.querySelectorAll("textarea")).find(
        (x) => x.offsetParent !== null
    );
    if (anyTa) return { site: "unknown", type: "textarea", el: anyTa };

    return null;
}

function getPromptText(box) {
    if (!box) return "";
    if (box.type === "textarea") return box.el.value || "";
    return box.el.innerText || box.el.textContent || "";
}

function setPromptText(box, text) {
    if (!box) return;

    if (box.type === "textarea") {
        box.el.value = text;
        box.el.dispatchEvent(new Event("input", { bubbles: true }));
        return;
    }

    box.el.focus();

    try {
        document.execCommand("selectAll", false, null);
        document.execCommand("insertText", false, text);
    } catch {
        box.el.innerText = text;
    }

    try {
        box.el.dispatchEvent(new InputEvent("input", { bubbles: true }));
    } catch {
        box.el.dispatchEvent(new Event("input", { bubbles: true }));
    }
    box.el.dispatchEvent(new Event("change", { bubbles: true }));
}

function getRect(el) {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return {
        left: r.left,
        top: r.top,
        right: r.right,
        bottom: r.bottom,
        width: r.width,
        height: r.height,
    };
}

function rectsOverlap(a, b) {
    return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
}

function clampWidgetToViewport(widgetEl) {
    if (!widgetEl) return;
    const w = getRect(widgetEl);
    if (!w) return;

    const gap = 8;
    const maxLeft = Math.max(gap, window.innerWidth - w.width - gap);
    const maxTop = Math.max(gap, window.innerHeight - w.height - gap);
    const nextLeft = Math.min(maxLeft, Math.max(gap, w.left));
    const nextTop = Math.min(maxTop, Math.max(gap, w.top));

    widgetEl.style.left = `${nextLeft}px`;
    widgetEl.style.top = `${nextTop}px`;
    widgetEl.style.right = "auto";
    widgetEl.style.bottom = "auto";
}

let activePromptEl = null;
let widgetManualPosition = false;
let widgetCollapsed = false;

function repositionWidget(widgetEl, promptEl) {
    if (!widgetEl) return;

    const maxWidth = Math.min(340, Math.floor(window.innerWidth * 0.4));
    widgetEl.style.width = `${Math.max(240, maxWidth)}px`;

    if (widgetManualPosition) {
        clampWidgetToViewport(widgetEl);
        return;
    }

    let right = 16;
    let bottom = 120;

    widgetEl.style.right = `${right}px`;
    widgetEl.style.bottom = `${bottom}px`;
    widgetEl.style.left = "auto";
    widgetEl.style.top = "auto";

    const w = getRect(widgetEl);
    const p = getRect(promptEl);
    if (!w || !p) return;

    if (rectsOverlap(w, p)) {
        const extraGap = 14;
        const newBottom = window.innerHeight - p.top + extraGap;
        widgetEl.style.bottom = `${Math.min(newBottom, window.innerHeight - 80)}px`;
    }
    clampWidgetToViewport(widgetEl);
}

function scheduleReposition() {
    requestAnimationFrame(() => {
        repositionWidget(widget, activePromptEl);
        clampWidgetToViewport(widget);
    });
}

function syncMiniView(widgetEl) {
    if (!widgetEl) return;
    const scoreText = widgetEl.querySelector("#spe-score")?.textContent || "Score: -- | Intent: --";
    const miniText = widgetEl.querySelector("#spe-mini-line");
    if (miniText) miniText.textContent = scoreText;
}

function setCollapsedState(widgetEl, collapsed) {
    if (!widgetEl) return;
    widgetCollapsed = collapsed;
    const body = widgetEl.querySelector("#spe-body");
    const mini = widgetEl.querySelector("#spe-mini");
    const collapseBtn = widgetEl.querySelector("#spe-collapse");
    if (body) body.style.display = collapsed ? "none" : "block";
    if (mini) mini.style.display = collapsed ? "block" : "none";
    if (collapseBtn) collapseBtn.textContent = collapsed ? "+" : "—";
    repositionWidget(widgetEl, activePromptEl);
}

function makeWidgetDraggable(widgetEl) {
    if (!widgetEl) return;
    const header = widgetEl.querySelector("#spe-header");
    if (!header || header.dataset.speDragBound) return;
    header.dataset.speDragBound = "1";
    header.style.cursor = "move";

    let startX = 0;
    let startY = 0;
    let baseLeft = 0;
    let baseTop = 0;
    let dragging = false;

    const onMove = (e) => {
        if (!dragging) return;
        const nextLeft = baseLeft + (e.clientX - startX);
        const nextTop = baseTop + (e.clientY - startY);
        widgetEl.style.left = `${nextLeft}px`;
        widgetEl.style.top = `${nextTop}px`;
        widgetEl.style.right = "auto";
        widgetEl.style.bottom = "auto";
        clampWidgetToViewport(widgetEl);
    };

    const onUp = () => {
        dragging = false;
        window.removeEventListener("pointermove", onMove);
        window.removeEventListener("pointerup", onUp);
    };

    header.addEventListener("pointerdown", (e) => {
        if (e.button !== 0) return;
        if (e.target.closest("button")) return;
        const rect = widgetEl.getBoundingClientRect();
        widgetEl.style.left = `${rect.left}px`;
        widgetEl.style.top = `${rect.top}px`;
        widgetEl.style.right = "auto";
        widgetEl.style.bottom = "auto";

        startX = e.clientX;
        startY = e.clientY;
        baseLeft = rect.left;
        baseTop = rect.top;
        dragging = true;
        widgetManualPosition = true;
        e.preventDefault();
        window.addEventListener("pointermove", onMove);
        window.addEventListener("pointerup", onUp);
    });
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
    box.style.webkitTextFillColor = "#111";
    const iconUrl = chrome.runtime.getURL("icon/spe-48.png");

    box.innerHTML = `
    <div id="spe-header" style="display:flex; justify-content:space-between; align-items:center;">
      <div style="display:flex; align-items:center; gap:1px;">
        <img src="${iconUrl}" alt="SPE" style="width:25px;height:25px;display:block;margin-bottom:-2px;transition:transform 140ms ease;" />
        <div style="font-weight:700;font-size:16px;line-height:22px;white-space:nowrap;">Smart Prompt Engine</div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;">
        <button id="spe-collapse" style="border:none;background:transparent;cursor:pointer;font-size:16px;color:#111 !important;-webkit-text-fill-color:#111 !important;opacity:1 !important;">—</button>
        <button id="spe-close" style="border:none;background:transparent;cursor:pointer;font-size:16px;color:#111 !important;-webkit-text-fill-color:#111 !important;opacity:1 !important;">✕</button>
      </div>
    </div>
    <div id="spe-mini" style="display:none;font-size:12px;color:#333;margin-top:8px;">
      <span id="spe-mini-line">Score: -- | Intent: --</span>
    </div>
    <div id="spe-body">
      <div id="spe-score" style="font-size:13px;margin-top:6px;">Score: -- | Intent: --</div>
      <div id="spe-missing" style="font-size:12px;color:#555;margin-top:6px;">Missing: --</div>
      <div id="spe-status" style="font-size:12px;color:#777;margin-top:8px;"></div>

      <div id="spe-token" style="margin-top:10px;padding-top:10px;border-top:1px solid #eee;">
        <div style="font-weight:600;font-size:13px;">Token Saver</div>
        <div id="spe-token-status" style="font-size:12px;color:#666;margin-top:4px;">
          Paste large text/code/data to enable (or 5+ CSV rows).
        </div>

        <button id="spe-compress" disabled style="margin-top:8px;width:100%;padding:9px;border-radius:12px;border:1px solid #ccc;background:#f7f7f7;cursor:pointer;color:#111 !important;-webkit-text-fill-color:#111 !important;opacity:1 !important;">
          Compress (Token Saver)
        </button>

        <div id="spe-token-actions" style="display:none;margin-top:8px;">
          <button id="spe-use-compressed" style="width:100%;padding:8px;border-radius:12px;border:1px solid #ccc;background:#fff;cursor:pointer;color:#111 !important;-webkit-text-fill-color:#111 !important;opacity:1 !important;">
            Use Compressed
          </button>
          <button id="spe-use-full" style="width:100%;padding:8px;border-radius:12px;border:1px solid #ccc;background:#fff;cursor:pointer;margin-top:6px;color:#111 !important;-webkit-text-fill-color:#111 !important;opacity:1 !important;">
            Use Full
          </button>
        </div>
      </div>

      <button id="spe-best" disabled style="margin-top:10px;width:100%;padding:9px;border-radius:12px;border:1px solid #ccc;background:#f7f7f7;cursor:pointer;color:#111 !important;-webkit-text-fill-color:#111 !important;opacity:1 !important;">
        Use Best Rewrite
      </button>
    </div>
  `;

    document.body.appendChild(box);
    const logo = box.querySelector("img");
    logo?.addEventListener("mouseenter", (e) => {
        e.target.style.transform = "scale(1.08)";
    });
    logo?.addEventListener("mouseleave", (e) => {
        e.target.style.transform = "scale(1)";
    });
    box.querySelector("#spe-close").onclick = () => box.remove();
    box.querySelector("#spe-collapse").onclick = () => setCollapsedState(box, !widgetCollapsed);
    makeWidgetDraggable(box);
    setCollapsedState(box, false);
    return box;
}

let widget = createWidget();
let debounceTimer = null;
let lastRewrite = null;

const SCORE_DEBOUNCE_MS = 1200;
const LLM_MIN_LEN = 12;
const LLM_SCORE_THRESHOLD = 75;
const REWRITE_THROTTLE_MS = 2500;
const REWRITE_IDLE_BYPASS_MS = 800;

let lastSentText = "";
let lastMeaningfulText = "";
let lastCallId = 0;
let rewriteLocked = false;
let lockedText = "";
let lastInputAt = 0;
let lastRewriteAt = 0;
let lastRewritePrompt = "";

const scoreCache = new Map();
const llmCache = new Map();

let tokenUIReady = false;
let tokenInputText = "";
let lastToken = null;
let lastFullText = "";

function normalizeText(t) {
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

function textChangedALot(prev, next) {
    if (!prev) return true;

    const deltaLen = Math.abs((next || "").length - (prev || "").length);
    if (deltaLen >= 30) return true;

    const prevWords = (prev.match(/\S+/g) || []).length;
    const nextWords = (next.match(/\S+/g) || []).length;
    if (Math.abs(nextWords - prevWords) >= 6) return true;

    const maxLen = Math.max(prev.length, next.length) || 1;
    const minLen = Math.min(prev.length, next.length);
    let i = 0;
    while (i < minLen && prev[i] === next[i]) i += 1;
    const changedRatio = 1 - (i / maxLen);
    return changedRatio >= 0.45;
}

function formatPct(before, after) {
    if (!before) return 0;
    return Math.max(0, Math.round(((before - after) / before) * 100));
}

function detectLargePaste(prompt) {
    const raw = (prompt || "").trim();
    if (!raw) return null;
    if (raw.length >= 400) return raw;

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

async function updateForText(text) {
    const callId = ++lastCallId;
    const trimmed = normalizeText(text);
    const scoreEl = widget.querySelector("#spe-score");
    const missEl = widget.querySelector("#spe-missing");
    const statusEl = widget.querySelector("#spe-status");
    const useBtn = widget.querySelector("#spe-best");

    if (!trimmed) {
        scoreEl.textContent = "Score: -- | Intent: --";
        syncMiniView(widget);
        missEl.textContent = "Missing: --";
        statusEl.textContent = "";
        useBtn.disabled = true;
        lastRewrite = null;
        rewriteLocked = false;
        lockedText = "";
        lastSentText = "";
        lastInputAt = 0;
        setupTokenSaverUI("");
        scheduleReposition();
        return;
    }

    lastSentText = trimmed;

    setupTokenSaverUI(trimmed);
    scheduleReposition();

    let localScore = null;

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
        syncMiniView(widget);
        statusEl.textContent = "";
        scheduleReposition();

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
        scheduleReposition();
    }

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
        scheduleReposition();
        return;
    }

    const localMissingText = missEl.textContent;
    try {
        statusEl.textContent = "Rewrite...";
        let r = llmCache.get(trimmed);
        if (!r) {
            const now = Date.now();
            const cooldownMs = now - lastRewriteAt;
            const idleMs = now - lastInputAt;
            const bypassCooldown =
                idleMs > REWRITE_IDLE_BYPASS_MS &&
                textChangedALot(lastRewritePrompt, trimmed);

            if (cooldownMs < REWRITE_THROTTLE_MS && !bypassCooldown) {
                statusEl.textContent = "";
                useBtn.disabled = true;
                lastRewrite = null;
                setupTokenSaverUI(trimmed);
                return;
            }

            lastRewriteAt = now;
            lastRewritePrompt = trimmed;
            r = await postJSON("/rewrite_suggestions", { prompt: trimmed });
            llmCache.set(trimmed, r);
        }

        if (callId !== lastCallId) return;

        if (r.error) {
            statusEl.textContent = "LLM unavailable";
            missEl.textContent = localMissingText;
            useBtn.disabled = true;
            lastRewrite = null;
            setupTokenSaverUI(trimmed);
            scheduleReposition();
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

        if (typeof r.score === "number" && r.score > 0) {
            const llmIntent = (r.intent && r.intent !== "other") ? r.intent : null;
            const current = scoreEl.textContent || "";
            const currentIntentMatch = current.match(/Intent:\s*([a-zA-Z_]+)/);
            const currentIntent = currentIntentMatch ? currentIntentMatch[1] : "other";
            scoreEl.textContent = `Score: ${r.score} | Intent: ${llmIntent || currentIntent}`;
            syncMiniView(widget);
        }

        statusEl.textContent = "";
        useBtn.disabled = false;
        scheduleReposition();
    } catch (e) {
        if (callId !== lastCallId) return;
        console.error("[SPE] /rewrite_suggestions failed:", e);
        statusEl.textContent = "Rewrite failed";
        missEl.textContent = localMissingText;
        useBtn.disabled = true;
        lastRewrite = null;
        scheduleReposition();
    }

    setupTokenSaverUI(trimmed);
    scheduleReposition();
}

function bindPromptBox(box) {
    if (!box || !box.el || box.el.dataset.speBound) return false;

    box.el.dataset.speBound = "1";
    activePromptEl = box.el;
    repositionWidget(widget, activePromptEl);
    const onChange = () => {
        clearTimeout(debounceTimer);
        lastInputAt = Date.now();
        debounceTimer = setTimeout(() => {
            const clean = normalizeText(getPromptText(box));
            if (!clean) {
                lastMeaningfulText = "";
                return updateForText(clean);
            }
            if (clean === lastMeaningfulText) return;
            lastMeaningfulText = clean;
            updateForText(clean);
        }, 250);
    };
    box.el.addEventListener("input", onChange);
    box.el.addEventListener("keyup", onChange);
    box.el.addEventListener("paste", () => setTimeout(onChange, 0));
    box.el.addEventListener("cut", () => setTimeout(onChange, 0));
    box.el.addEventListener("compositionend", onChange);

    const existing = getPromptText(box);
    if (existing.trim()) {
        const clean = normalizeText(existing);
        lastMeaningfulText = clean;
        updateForText(clean);
    } else {
        setupTokenSaverUI("");
    }

    return true;
}

function observeChatGPTDom() {
    const observer = new MutationObserver(() => {
        const box = findPromptBox();
        if (box?.el) {
            activePromptEl = box.el;
            repositionWidget(widget, activePromptEl);
        }
        bindPromptBox(box);
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

async function bindTextareaLoop() {
    const useBtn = widget.querySelector("#spe-best");

    useBtn.onclick = async () => {
        const box = findPromptBox();
        if (!box || !lastRewrite) return;

        const req = Array.isArray(lastRewrite.required_missing) ? lastRewrite.required_missing : [];
        const opt = Array.isArray(lastRewrite.optional_missing) ? lastRewrite.optional_missing : [];
        const cards = Array.isArray(lastRewrite.rewrite_cards) ? lastRewrite.rewrite_cards : [];

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
        if (box?.el) {
            activePromptEl = box.el;
            repositionWidget(widget, activePromptEl);
        }
        bindPromptBox(box);

        await sleep(1200);
    }
}

window.addEventListener("resize", () => repositionWidget(widget, activePromptEl));
repositionWidget(widget, findPromptBox()?.el || null);

observeChatGPTDom();
bindTextareaLoop();
document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    const box = findPromptBox();
    if (!box) return;
    bindPromptBox(box);
    updateForText(getPromptText(box));
});
