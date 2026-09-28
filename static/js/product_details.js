/* Product details page: real product data, live Random Forest prediction,
   real SHAP evidence, Gemini explanation, and catalogue recommendations.
   Every section is loaded independently so one failing API never leaves the
   whole page stuck in a loading state. */
document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const parsedId = Number(params.get("id"));
    const productId = Number.isInteger(parsedId) && parsedId > 0 ? parsedId : 2;

    const byId = (id) => document.getElementById(id);
    const formatMoney = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;

    /* Turn a real reason into one short, friendly sentence. */
    function cleanReason(text) {
    return String(text || "")
        .replace(/also influenced the prediction\.?/gi, "also played a part.")
        .replace(/contributed to this prediction\.?/gi, "also played a part.")
        .replace(/\bthe prediction\b/gi, "this suggestion")
        // Specific SHAP bullet replacements
                .replace(/Your previous purchases show interest in similar products\.?/gi, "The previous purchase category contributed positively to the prediction.")
        .replace(/This category has appeared frequently in your purchasing history\.?/gi, "The historical frequency of this category contributed positively to the prediction.")
        .replace(/Your previous product and brand preferences also played a part\.?/gi, "Previous brand and product information also contributed to the prediction.")
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
            .replace(/\bpredicts the category\b/gi, "predicts the category")
            .replace(/\bthe model\b/gi, "we")
            .replace(/\bmodel association\b/gi, "historical purchasing pattern")
            .replace(/\bwith a\b/gi, "")
            .replace(/[()"]/g, "")
            .replace(/\s+([.!?])/g, "$1")
            .replace(/\s{2,}/g, " ")
            .trim();
        if (!text) {
            text = category ? `Based on historical purchasing patterns, the model predicts the category ${category}.` : "";
        }
        if (text && !/[.!?]$/.test(text)) text += ".";
        if (text.length > 180) text = text.slice(0, 180).trim() + "…";
        return text;
    }

    let quantity = 1;
    let saved = false;

    /* ---------- Quantity controls ---------- */
    const quantityValue = byId("quantity");
    byId("increase").addEventListener("click", () => {
        quantity += 1;
        quantityValue.textContent = quantity;
    });
    byId("decrease").addEventListener("click", () => {
        if (quantity > 1) {
            quantity -= 1;
            quantityValue.textContent = quantity;
        }
    });

    /* ---------- Add to cart ---------- */
    byId("add-cart").addEventListener("click", async () => {
        try {
            await apiFetch("/api/cart", {
                method: "POST",
                body: JSON.stringify({ product_id: productId, quantity }),
            });
            showDemoToast("Added to your cart.");
        } catch (error) {
            showDemoToast(error.message);
        }
    });

    /* ---------- Wishlist ---------- */
    byId("save-product").addEventListener("click", async () => {
        try {
            if (saved) {
                await apiFetch(`/api/wishlist/${productId}`, { method: "DELETE" });
            } else {
                await apiFetch("/api/wishlist", {
                    method: "POST",
                    body: JSON.stringify({ product_id: productId }),
                });
            }
            saved = !saved;
            const button = byId("save-product");
            button.textContent = saved ? "♥ Saved" : "♡ Wishlist";
            showDemoToast(saved ? "Saved to your wishlist." : "Removed from wishlist.");
        } catch (error) {
            showDemoToast(error.message);
        }
    });

    /* ---------- Rating (optional, only if signed in) ---------- */
    const actionRow = document.querySelector(".product-action-row");
    if (actionRow) {
        const ratingBox = document.createElement("p");
        ratingBox.className = "rating-row";
        ratingBox.innerHTML =
            'Rate this product: <select id="product-rating">' +
            '<option value="">Choose rating</option>' +
            '<option value="5">5 — Excellent</option>' +
            '<option value="4">4 — Good</option>' +
            '<option value="3">3 — Average</option>' +
            '<option value="2">2 — Poor</option>' +
            '<option value="1">1 — Very poor</option>' +
            '</select> <button class="button button-secondary" id="save-rating" type="button">Save rating</button>';
        actionRow.after(ratingBox);
        byId("save-rating").addEventListener("click", async () => {
            const rating = Number(byId("product-rating").value);
            if (!rating) {
                showDemoToast("Choose a rating first.");
                return;
            }
            try {
                await apiFetch("/api/ratings", {
                    method: "POST",
                    body: JSON.stringify({ product_id: productId, rating }),
                });
                showDemoToast("Your rating was saved.");
            } catch (error) {
                showDemoToast(error.message);
            }
        });
    }

    /* ---------- Real product record ---------- */
    async function loadProduct() {
        try {
            const product = await apiFetch(`/api/products/${productId}`);
            const photo = byId("product-photo");
            photo.src = product.image_url || "/static/img/placeholder-electronics.svg";
            photo.alt = `${product.brand || ''} ${product.name || ''}`;
            byId("product-brand-category").textContent = `${product.brand} · ${product.category}`;
            byId("product-name").textContent = product.name;
            byId("product-meta").textContent =
                `★ ${Number(product.rating || 0).toFixed(1)} · ` +
                `${Number(product.review_count || 0).toLocaleString("en-IN")} reviews · In stock`;
            const discount = Math.round((1 - product.price / product.original_price) * 100);
            byId("product-price").innerHTML =
                `${formatMoney(product.price)} ` +
                `<span class="old-price">${formatMoney(product.original_price)}</span> ` +
                (discount > 0 ? `<span class="discount">${discount}% off</span>` : "");
            byId("product-description").textContent =
                product.description || "No description is available for this product.";
            document.title = `${product.name} | ElectroPredict`;
        } catch (error) {
            byId("product-brand-category").textContent = "Product unavailable";
            byId("product-name").textContent = "Product not found";
            byId("product-description").textContent = error.message;
        }
    }

    /* ---------- Live Random Forest prediction + real SHAP + Gemini ---------- */
    async function loadExplanation() {
        try {
            const data = await apiFetch(`/api/explanation`);
            // Populate category and probability
            byId("xai-category").textContent = data.predicted_category || "Unavailable";
            byId("xai-probability").textContent =
                typeof data.prediction_probability === "number"
                    ? `${(data.prediction_probability * 100).toFixed(1)}%`
                    : "—";
            // SHAP contributors
            const shapList = byId("xai-shap");
            const contributors = (Array.isArray(data.shap_contributors) ? data.shap_contributors : []).slice(0, 3);
            if (contributors.length) {
                shapList.innerHTML = contributors
                    .map((item) => `<li>${cleanReason(item.feature)}</li>`)
                    .join("");
            } else {
                shapList.innerHTML = "<li>SHAP identifies the purchasing-pattern features that contributed to the model's prediction.</li>";
            }
            // Gemini explanation
            const geminiBox = byId("xai-gemini");
            geminiBox.textContent = shortSummary(data.gemini_explanation, data.predicted_category);
            // Technical details (optional)
            const technical = byId("xai-technical");
            if (technical) {
                technical.textContent = JSON.stringify(data.technical_details || data, null, 2);
            }
        } catch (error) {
            // Fail-safe UI updates
            byId("xai-category").textContent = "Unavailable";
            byId("xai-probability").textContent = "—";
            byId("xai-shap").innerHTML = `<li>${error.message}</li>`;
            byId("xai-gemini").textContent = "Explainable AI data unavailable";
            console.error("Explanation load error:", error);
        }
    }

    /* ---------- Real recommendations from the predicted category ---------- */
    function recommendationCard(product) {
        const discount = Math.round((1 - product.price / product.original_price) * 100);
        return `
            <article class="product-card">
                <div class="product-image-wrap">
                    <img src="${product.image_url}" alt="${product.brand} ${product.name}">
                </div>
                <div class="product-info">
                    <p class="brand-name">${product.brand}</p>
                    <h2 class="product-name">${product.name}</h2>
                    <p class="product-category">${product.category}</p>
                    <p class="rating">★ ${Number(product.rating || 0).toFixed(1)} <span>(${Number(product.review_count || 0).toLocaleString("en-IN")} reviews)</span></p>
                    <div class="price-row">
                        <strong>${formatMoney(product.price)}</strong>
                        <s>${formatMoney(product.original_price)}</s>
                        ${discount > 0 ? `<em>${discount}% off</em>` : ""}
                    </div>
                    <div class="card-actions">
                        <a class="button button-primary" href="/product-details?id=${product.id}">View details</a>
                    </div>
                </div>
            </article>
        `;
    }

    async function loadRecommendations() {
        const grid = byId("related-grid");
        try {
            const data = await apiFetch(`/api/recommendations?limit=4&exclude_product_id=${productId}`);
            const products = Array.isArray(data.products) ? data.products : [];
            if (!products.length) {
                grid.innerHTML =
                    '<div class="card" style="padding:18px;grid-column:1/-1;">' +
                    "No related products are available in the predicted category yet.</div>";
                return;
            }
            grid.innerHTML = products.map(recommendationCard).join("");
        } catch (error) {
            grid.innerHTML =
                '<div class="card" style="padding:18px;grid-column:1/-1;">' + `${error.message}</div>`;
        }
    }

    /* ---------- Record a consent-based view (ignore login requirement) ---------- */
    apiFetch("/api/activity", {
        method: "POST",
        body: JSON.stringify({ product_id: productId, action_type: "view" }),
    }).catch(() => {});

    /* Each loader is isolated so one failure never blocks the others. */
    loadProduct();
    loadExplanation();
    loadRecommendations();
});