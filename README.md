# Smart Prompt Engine (SPE) 🚀  

A Chrome extension + FastAPI backend that improves prompts **before** they are sent to ChatGPT (and can be extended to Gemini/Claude).  
It provides:
- **Live prompt scoring** while you type
- **LLM-based rewrite cards** with fill-in-the-blank fields
- **Token Saver** (compress logs / code / JSON / CSV to reduce tokens)
- **CSP-safe API calls** via background script proxy
- **Optional cache** for rewrite suggestions to reduce cost + speed up UX

---

## Why this exists (Problem → Solution)
Most users type short prompts like:
> “Suggest me a phone under $500”

That often produces low-quality answers because key details are missing.  
SPE helps by:
1) scoring prompt quality in real-time (cheap, local)
2) showing exactly what’s missing (smart, LLM-based)
3) offering a “Best Rewrite” prompt that keeps your info + adds blanks for missing fields
4) compressing big pasted text (logs/code/data) to save tokens

Goal: **Get better answers with less cost and less effort.**

---

## What you built (Features)

### 1) Live Score (Local / No LLM)
- Runs fast, free, on your backend
- Detects intent (decision/instruction/debugging/etc)
- Gives a score 0–100
- Helps guide users without calling an LLM every keystroke

✅ Endpoint: `POST /score`

---

### 2) LLM Rewrite Suggestions (Fill Blanks)
- Only runs when prompt is long enough
- Extracts **provided_info**
- Finds **missing_info** (required + optional)
- Returns 3 rewrite cards formatted like:

<One-line rewritten prompt>
Fill these (required):

field: ____ (example)

Fill these (optional):

field: ____ (example)


✅ Endpoint: `POST /rewrite_suggestions`

---

### 3) Token Saver (Compression)
Users often paste:
- stack traces
- logs
- long code blocks
- JSON/CSV dumps

This explodes token usage. Token Saver compresses them into a short summary.

✅ Endpoint: `POST /compress`

---

### 4) CSP-safe network calls (Important)
ChatGPT pages block `fetch("http://127.0.0.1:8000")` due to **Content Security Policy (CSP)**.  
Solution:
- content script cannot call backend directly
- so content script sends message to **background.js**
- background makes the network request

✅ Pattern:
`content.js -> chrome.runtime.sendMessage -> background.js -> fetch -> response -> content.js`

---

### 5) Rewrite Cache (Speed + Cost Control)
Rewrite calls cost money (LLM). To reduce repeat calls:
- backend caches results for a short TTL (time-to-live)
- returns `meta.cache = "hit"` or `"miss"`

This makes the extension feel instant after the first request.

---

## Tech Stack
- **Backend:** FastAPI (Python)
- **LLM:** OpenAI (via `openai>=1.x` client)
- **Extension:** Chrome Manifest v3
- **Frontend UI:** Inline widget injected into the page (`content.js`)
- **CSP workaround:** background proxy requests

---

## Project Structure (Typical)

smart-prompt-engine/
backend/
api.py
llm/
openai_client.py
rewrite/
suggestions.py
scorer/
local_score.py
representation.py
...
compress/
logs.py
json.py
csv.py
code.py
extension/
manifest.json
content.js
background.js
popup.html
popup.js
icons/
spe16.png
spe48.png
spe128.png
README.md


---

# Setup & Run (Backend)

## 1) Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
2) Install dependencies
pip install -r requirements.txt
If you don’t have requirements yet:

pip install fastapi uvicorn openai numpy
3) Set OpenAI key (Required for rewrite/optimize)
Mac/Linux:

export OPENAI_API_KEY="YOUR_KEY_HERE"
Windows PowerShell:

setx OPENAI_API_KEY "YOUR_KEY_HERE"
✅ IMPORTANT: Put only the raw key (no quotes like smart quotes, no “Bearer”).

4) Run backend server
From project root:

uvicorn backend.api:app --reload --port 8000
You should see:

Uvicorn running on http://127.0.0.1:8000

Setup & Run (Chrome Extension)
1) Load unpacked extension
Open Chrome

Go to: chrome://extensions

Enable Developer Mode

Click Load unpacked

Select the extension/ folder

2) Confirm permissions
Make sure manifest includes:

host permissions for backend

content script match rules

Example:

"host_permissions": [
  "http://127.0.0.1:8000/*",
  "http://localhost:8000/*"
]
3) Open ChatGPT and test
Go to:

https://chat.openai.com/
or

https://chatgpt.com/

You should see the inline widget.

Usage Guide
✅ Normal Prompt
Type:

Suggest me a phone under $500

You will see:

Score + intent

Missing fields (LLM if available)

Use Best Rewrite button

✅ Token Saver Test
Paste a large log/code/json/csv inside prompt box (400+ chars).
The Token Saver section enables:

“Compress”

“Use Compressed”

“Use Full”

API Endpoints
POST /score
Local scoring (no LLM).
Request:

{ "prompt": "Suggest me a phone under $500" }
Response:

{
  "score": 11,
  "intent": "decision",
  "missing_items": ["output format", "constraints", ...]
}
POST /rewrite_suggestions
LLM-based missing info + rewrite cards.
Request:

{ "prompt": "Suggest iPhone under $500 in USA..." }
Response:

{
  "provided_info": [...],
  "required_missing": [...],
  "optional_missing": [...],
  "rewrite_cards": [...],
  "intent": "decision",
  "score": 75
}
POST /compress
Detects and compresses large pasted text.
Request:

{ "text": "Traceback (most recent call last): ..." }
Response:

{
  "detected_type": "logs",
  "compressed": "Traceback...\nTypeError...",
  "stats": { "chars_in": 1000, "chars_out": 200 }
}
Troubleshooting
1) “Refused to connect because of CSP”
If you try direct fetch from the page console:

fetch("http://127.0.0.1:8000/score")
it will fail.

✅ Fix: use background proxy (already implemented)

2) LLM not available
Error:

{"error":"LLM call failed"}
Common reasons:

OPENAI_API_KEY not set

quota/billing issue

key had smart quotes “ ” causing ascii error

3) “await is only valid in async functions”
This happens if you used await at top level in a non-module script.
Fix: ensure await is inside async function.

4) Score not updating unless refresh
This usually happens when the page replaces the prompt input element dynamically.
Fix:

the content script uses a loop to re-bind when ChatGPT replaces DOM nodes.

5) Token Saver says “Detected csv” for normal text
Detection order matters (logs/json/csv/code).
If CSV detector is too loose, it can false-positive.
Fix:

tighten looks_like_csv to reject sentence-heavy text (already improved).

Privacy / Data Storage
✅ By default:

Prompts are processed in memory (no DB)

Cache is in-memory (TTL cache)

No user identity required unless you add it

If you add analytics/feedback logging later:

store minimal metadata only (event type, timestamp, anonymized id)

never store full prompts unless user opts in

Roadmap (Next Tasks)
Host backend (Render / Railway / Fly.io)

Replace API_BASE with HTTPS URL

Web Store release build

Add per-user cache scoping

Add cache metrics endpoint

Automated regression tests

License
For personal / learning use. Add your own license later (MIT recommended).


---

## ✅ Now push README to Git

Run these commands:

```bash
git status
git add README.md
git commit -m "Add complete project README"
git push origin main