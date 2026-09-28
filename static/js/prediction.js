document.addEventListener("DOMContentLoaded", async () => {
    const catName = document.getElementById("pred-category-name");
    const prob = document.getElementById("pred-probability");
    const factorsList = document.getElementById("prediction-factors-list");

    const friendlyName = (feature) => {
        const cleaned = String(feature || "").toLowerCase();
        if (cleaned.includes("most_frequent_previous_category")) return "Category purchasing pattern";
        if (cleaned.includes("previous_category_proportion")) return "Category purchase ratio";
        if (cleaned.includes("previous_category_count")) return "Category order frequency";
        if (cleaned.includes("previous_category")) return "Previous category";
        if (cleaned.includes("previous_brand")) return "Previous brand loyalty";
        if (cleaned.includes("previous_product")) return "Past product interactions";
        if (cleaned.includes("previous_average_order_spend")) return "Average order spend";
        if (cleaned.includes("previous_average_item_price")) return "Average item price";
        if (cleaned.includes("previous_min_order_spend")) return "Minimum order spend";
        if (cleaned.includes("previous_orders_last_90_days")) return "Recent order frequency (90d)";
        if (cleaned.includes("average_days_between_orders")) return "Days between orders";
        return feature.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
    };

    try {
        const data = await apiFetch("/api/explanation");
        if (catName && data.predicted_category) catName.textContent = data.predicted_category;
        if (prob && data.prediction_probability) prob.textContent = `${(data.prediction_probability * 100).toFixed(1)}%`;

        if (factorsList) {
            const positives = (data.top_positive_contributors || []).slice(0, 5);
            const negatives = (data.top_negative_contributors || []).slice(0, 2);
            const maxVal = Math.max(
                ...positives.map((item) => Math.abs(Number(item.shap_value) || 0)),
                ...negatives.map((item) => Math.abs(Number(item.shap_value) || 0)),
                0.15
            );

            let html = '<div class="shap-group"><p class="shap-group-title">Positive contributors (increases probability):</p>';
            positives.forEach((item) => {
                const val = Number(item.shap_value) || 0;
                const pct = Math.min(100, Math.max(12, Math.round((Math.abs(val) / maxVal) * 100)));
                html += `
                    <div class="shap-row">
                        <div class="shap-meta">
                            <span class="shap-name">↑ ${friendlyName(item.feature)}</span>
                            <span class="shap-val positive">+${val.toFixed(4)}</span>
                        </div>
                        <div class="shap-bar-track">
                            <div class="shap-bar positive" style="width: ${pct}%"></div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            if (negatives.length > 0) {
                html += '<div class="shap-group" style="margin-top:14px;"><p class="shap-group-title">Negative contributors (decreases probability):</p>';
                negatives.forEach((item) => {
                    const val = Number(item.shap_value) || 0;
                    const pct = Math.min(100, Math.max(8, Math.round((Math.abs(val) / maxVal) * 100)));
                    html += `
                        <div class="shap-row">
                            <div class="shap-meta">
                                <span class="shap-name">↓ ${friendlyName(item.feature)}</span>
                                <span class="shap-val negative">${val.toFixed(4)}</span>
                            </div>
                            <div class="shap-bar-track">
                                <div class="shap-bar negative" style="width: ${pct}%"></div>
                            </div>
                        </div>
                    `;
                });
                html += '</div>';
            }

            factorsList.innerHTML = html;
        }
    } catch (err) {
        if (factorsList) factorsList.innerHTML = `<div class="info-notice">Could not load SHAP factors.</div>`;
    }
});
