document.getElementById("scoreBtn").addEventListener("click", async () => {
    const prompt = document.getElementById("popupPrompt").value;
    const res = await fetch("http://127.0.0.1:8000/score", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt })
    });
    const data = await res.json();
    document.getElementById("result").innerText = `Score: ${data.score} (${data.quality})`;
});

document.getElementById("optimizeBtn").addEventListener("click", async () => {
    const prompt = document.getElementById("popupPrompt").value;
    const res = await fetch("http://127.0.0.1:8000/optimize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            prompt,
            answers: { task: "classification", output: "Python code", level: "beginner-friendly" }
        })
    });
    const data = await res.json();
    document.getElementById("popupPrompt").value = data.optimized_prompt;
});
