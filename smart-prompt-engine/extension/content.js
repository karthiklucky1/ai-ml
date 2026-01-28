// 1️⃣ Find input box
const inputBox = document.querySelector("textarea");

// 2️⃣ Helper functions
async function fetchScore(prompt) {
    const res = await fetch("http://127.0.0.1:8000/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    });
    return await res.json();
}

async function fetchSuggestions(prompt) {
    const res = await fetch("http://127.0.0.1:8000/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    });
    return await res.json();
}

async function fetchOptimized(prompt, answers = {}) {
    const res = await fetch("http://127.0.0.1:8000/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, answers })
    });
    return await res.json();
}

// 3️⃣ Display suggestions & score
inputBox.addEventListener("input", async () => {
    const prompt = inputBox.value;

    const scoreData = await fetchScore(prompt);
    showScore(scoreData);

    const suggestions = await fetchSuggestions(prompt);
    showSuggestions(suggestions.questions);
});

// 4️⃣ Optimize button
let optimizeBtn = document.createElement("button");
optimizeBtn.innerText = "Optimize Prompt";
inputBox.parentNode.appendChild(optimizeBtn);

optimizeBtn.addEventListener("click", async () => {
    const answers = {
        task: "classification",
        output: "Python code",
        level: "beginner-friendly"
    };
    const optimized = await fetchOptimized(inputBox.value, answers);
    inputBox.value = optimized.optimized_prompt;
});

// 5️⃣ Helper display functions
function showScore(data) {
    let div = document.getElementById("scoreDiv");
    if (!div) {
        div = document.createElement("div");
        div.id = "scoreDiv";
        inputBox.parentNode.appendChild(div);
    }
    div.innerText = `Score: ${data.score} (${data.quality})`;
}

function showSuggestions(questions) {
    let div = document.getElementById("sugDiv");
    if (!div) {
        div = document.createElement("div");
        div.id = "sugDiv";
        div.style.background = "#f9f9f9";
        div.style.padding = "8px";
        inputBox.parentNode.appendChild(div);
    }
    div.innerHTML = questions.map(q => `<p>${q}</p>`).join("");
}

const textarea = document.getElementById("prompt-textarea");

textarea.addEventListener("input", async () => {
    const prompt = textarea.value;
    const largeText = document.getElementById("large-text-input").value;

    if (largeText && largeText.length > 200) { // threshold
        const response = await fetch("http://127.0.0.1:8000/optimize_context", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt: prompt, text: largeText })
        });
        const data = await response.json();

        const hintBox = document.getElementById("hint-box");
        hintBox.innerHTML = `
            💡 You can reduce tokens by ${data.tokens_saved}<br>
            Suggested context:<br>${data.optimized_context}
        `;
    }
});
