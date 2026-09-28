/* Explainable AI page: three short, shopper-friendly reasons for the suggestion.
   Built from the real SHAP contributors and the real generated summary. */
document.addEventListener("DOMContentLoaded", async () => {
    const catDisplay = document.getElementById("exp-category-display");
    const probDisplay = document.getElementById("exp-probability");
    const shapList = document.getElementById("exp-shap-list");
    const geminiBox = document.getElementById("exp-gemini-box");

    /* Turn a real reason into one short, friendly sentence. */
    function cleanReason(text) {
        return String(text || "")
            .replace(/also influenced the prediction\.?/gi, "also played a part.")
            .replace(/contributed to this prediction\.?/gi, "also played a part.")
            .replace(/\bthe prediction\b/gi, "this suggestion")
            .replace(/\s{2,}/g, " ")
            .trim();
    }

    /* Reduce the generated text to a single short, plain-language summary. */
    function shortSummary(raw, category) {
        let text = String(raw || "")
            .replace(/^#+ .*/gm, "")
            .replace(/\*\*(.*?)\*\*/g, "$1")
            .replace(/Model Prediction:?/gi, "")
            .replace(/Explanation of Prediction:?/gi, "")
            .replace(/\s*[-•]\s*[^\n]*/g, " ")
            .replace(/The following positive factors[\s\S]*$/i, "")
            .replace(/Factors pushing[\s\S]*$/i, "")
            .replace(/Please note:[\s\S]*$/i, "")
            .replace(/probability of [0-9.]+/gi, "")
            .replace(/with a strong likelihood/gi, "")
            .replace(/\bpredicts the category\b/gi, "think you will like")
            .replace(/\bthe model\b/gi, "we")
            .replace(/\bmodel association\b/gi, "pattern in your shopping history")
            .replace(/[()"]/g, "")
            .replace(/\s{2,}/g, " ")
            .trim();
        if (!text) {
            text = category ? `Based on your past activity, we think you will like ${category}.` : "";
        }
        if (text && !/[.!?]$/.test(text)) text += ".";
        if (text.length > 180) text = text.slice(0, 180).trim() + "…";
        return text;
    }

    try {
        const data = await apiFetch("/api/explanation");

        if (catDisplay && data.predicted_category) {
            catDisplay.textContent = data.predicted_category;
        }
        if (probDisplay && typeof data.prediction_probability === "number") {
            probDisplay.textContent = `${(data.prediction_probability * 100).toFixed(1)}%`;
        }

        if (shapList) {
            const contributors = (Array.isArray(data.shap_contributors) ? data.shap_contributors : []).slice(0, 3);
            if (contributors.length) {
                shapList.innerHTML = `<ul class="reason-list">${contributors
                    .map((item) => `<li>${cleanReason(item.feature)}</li>`)
                    .join("")}</ul>`;
            } else {
                shapList.innerHTML =
                    '<ul class="reason-list"><li>Because your shopping history shows interest in this category.</li></ul>';
            }
        }

        if (geminiBox) {
            const summary = shortSummary(data.gemini_explanation, data.predicted_category);
            geminiBox.innerHTML = `<p class="gemini-paragraph">${summary || "Based on your past activity, this is what we think you will like."}</p>`;
        }
    } catch (err) {
        if (shapList) shapList.innerHTML = '<div class="info-notice">Could not load the reasons right now.</div>';
        if (geminiBox) geminiBox.innerHTML = '<div class="info-notice">The explanation is unavailable right now.</div>';
    }
});