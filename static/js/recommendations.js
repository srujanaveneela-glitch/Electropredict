document.addEventListener("DOMContentLoaded", async () => {
    const form = document.getElementById("recommendation-form");
    const categorySelect = document.getElementById("predicted-category");
    const grid = document.getElementById("recommendation-grid");
    const status = document.getElementById("recommendation-status");
    const predictedDisplay = document.getElementById("predicted-category-display");
    const probabilityDisplay = document.getElementById("prediction-probability-display");
    const shapList = document.getElementById("shap-factors-list");
    const geminiBox = document.getElementById("gemini-explanation-box");

    const formatPrice = (value) => `₹${Number(value).toLocaleString("en-IN")}`;

    const canonicalLabels = {
        smartphone: "Smartphones",
        laptop_notebook: "Laptops",
        tablet: "Tablets",
        smartwatch_clocks: "Smart Watches",
        audio: "Headphones",
        video: "Video",
        computer_peripherals: "Computer peripherals",
        computer_components: "Computer components",
        telephone: "Telephones",
        desktop: "Desktops",
        camera: "Cameras",
        other_electronics: "Other electronics"
    };

    const normalizeCategory = (value) => {
        const normalized = String(value || "").trim().toLowerCase();
        const map = {
            smartphone: "smartphone",
            smartphones: "smartphone",
            laptop_notebook: "laptop_notebook",
            laptops: "laptop_notebook",
            laptop: "laptop_notebook",
            notebook: "laptop_notebook",
            notebooks: "laptop_notebook",
            tablet: "tablet",
            tablets: "tablet",
            smartwatch_clocks: "smartwatch_clocks",
            "smart watches": "smartwatch_clocks",
            smartwatch: "smartwatch_clocks",
            audio: "audio",
            headphones: "audio",
            video: "video",
            computer_peripherals: "computer_peripherals",
            "computer components": "computer_components",
            computer_components: "computer_components",
            telephone: "telephone",
            telephones: "telephone",
            desktop: "desktop",
            desktops: "desktop",
            camera: "camera",
            cameras: "camera",
            other_electronics: "other_electronics"
        };
        return map[normalized] || null;
    };

    const friendlyFeatureName = (feature) => {
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

    const productCard = (product, recommendedCategory) => {
        const label = canonicalLabels[recommendedCategory] || recommendedCategory;
        const discountPct = Math.max(0, Math.round(((product.original_price || product.price) - product.price) / (product.original_price || product.price) * 100));

        return `
            <article class="product-card">
                <div class="product-image-wrap">
                    <button class="wishlist-button" type="button" data-id="${product.id}" aria-label="Save ${product.name} to wishlist">♡</button>
                    <img src="${product.image_url || ""}" alt="${product.brand} ${product.name}">
                </div>
                <div class="product-info">
                    <p class="brand-name">${product.brand}</p>
                    <h2 class="product-name">${product.name}</h2>
                    <p class="product-category">${product.category}</p>
                    <p class="rating">★ ${Number(product.rating || 0).toFixed(1)} <span>(${Number(product.review_count || 0).toLocaleString("en-IN")} reviews)</span></p>
                    <div class="price-row">
                        <strong>${formatPrice(product.price)}</strong>
                        <s>${formatPrice(product.original_price || product.price)}</s>
                        ${discountPct > 0 ? `<em>${discountPct}% off</em>` : ""}
                    </div>
                    <div class="recommendation-why">
                        <strong>Why recommended?</strong>
                        <p>This product belongs to the category predicted by the AI (${label}) and was selected from the available products using the existing recommendation ranking.</p>
                    </div>
                    <div class="card-actions">
                        <button class="button button-primary add-recommendation" type="button" data-id="${product.id}">Add to cart</button>
                        <a class="button button-secondary" href="/product-details?id=${product.id}">View details</a>
                    </div>
                </div>
            </article>
        `;
    };

    let explanationData = null;

    const loadExplanationData = async () => {
        try {
            explanationData = await apiFetch("/api/explanation");
            renderExplainableAI(explanationData);
        } catch (error) {
            console.error("Could not load explanation evidence:", error);
            if (shapList) shapList.innerHTML = `<div class="info-notice">Explanation evidence is temporarily unavailable.</div>`;
            if (geminiBox) geminiBox.innerHTML = `<div class="info-notice">AI natural-language explanation is temporarily unavailable.</div>`;
        }
    };

    const renderExplainableAI = (data) => {
        if (!data) return;

        if (probabilityDisplay && data.prediction_probability) {
            probabilityDisplay.textContent = `${(data.prediction_probability * 100).toFixed(1)}%`;
        }

        // Render SHAP factors
        if (shapList) {
            const positives = (data.top_positive_contributors || []).slice(0, 5);
            const negatives = (data.top_negative_contributors || []).slice(0, 2);
            const maxVal = Math.max(
                ...positives.map((item) => Math.abs(Number(item.shap_value) || 0)),
                ...negatives.map((item) => Math.abs(Number(item.shap_value) || 0)),
                0.15
            );

            let html = '<div class="shap-group"><p class="shap-group-title">Factors increasing prediction likelihood:</p>';
            positives.forEach((item) => {
                const val = Number(item.shap_value) || 0;
                const pct = Math.min(100, Math.max(12, Math.round((Math.abs(val) / maxVal) * 100)));
                const name = friendlyFeatureName(item.feature);
                html += `
                    <div class="shap-row">
                        <div class="shap-meta">
                            <span class="shap-name">↑ ${name}</span>
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
                html += '<div class="shap-group" style="margin-top:14px;"><p class="shap-group-title">Factors reducing prediction likelihood:</p>';
                negatives.forEach((item) => {
                    const val = Number(item.shap_value) || 0;
                    const pct = Math.min(100, Math.max(8, Math.round((Math.abs(val) / maxVal) * 100)));
                    const name = friendlyFeatureName(item.feature);
                    html += `
                        <div class="shap-row">
                            <div class="shap-meta">
                                <span class="shap-name">↓ ${name}</span>
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

            shapList.innerHTML = html;
        }

        // Render Gemini natural-language explanation
        if (geminiBox) {
            const rawExplanation = data.gemini_explanation || "";
            // Clean markdown formatting for professional UI presentation
            let cleaned = rawExplanation
                .replace(/^#+ .*/gm, "")
                .replace(/\*\*Model Prediction\*\*[\s\S]*?\*\*Explanation of Prediction\*\*/i, "")
                .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                .trim();

            if (!cleaned) {
                cleaned = "The machine-learning model reached this prediction based on observed customer purchase history, past brand choices, and category browsing frequencies.";
            }

            // Split into readable paragraphs
            const paragraphs = cleaned.split("\n\n").filter((p) => p.trim().length > 0);
            geminiBox.innerHTML = paragraphs.map((p) => {
                if (p.includes("* <strong>") || p.startsWith("* ")) {
                    const items = p.split("\n").filter((l) => l.trim().length > 0).map((l) => `<li>${l.replace(/^\*\s*/, "")}</li>`).join("");
                    return `<ul class="gemini-bullets">${items}</ul>`;
                }
                return `<p class="gemini-paragraph">${p.replace(/\n/g, "<br>")}</p>`;
            }).join("");
        }
    };

    const populateCategories = async () => {
        try {
            const products = await apiFetch("/api/products");
            // Count products per canonical category so zero-product categories are completely excluded
            const categoryCounts = new Map();
            const categoryDisplayNames = new Map();

            products.forEach((product) => {
                const canonical = normalizeCategory(product.category);
                if (!canonical) return;
                categoryCounts.set(canonical, (categoryCounts.get(canonical) || 0) + 1);
                if (!categoryDisplayNames.has(canonical)) {
                    categoryDisplayNames.set(canonical, canonicalLabels[canonical] || product.category);
                }
            });

            // Keep ONLY categories with at least 1 actual product
            const validCategories = [...categoryCounts.entries()]
                .filter(([_, count]) => count > 0)
                .map(([canonical]) => canonical);

            if (validCategories.length === 0) {
                categorySelect.innerHTML = '<option value="">No categories available</option>';
                status.textContent = "No products found in catalogue.";
                return;
            }

            categorySelect.innerHTML = validCategories.map((canonical) => `
                <option value="${canonical}">${categoryDisplayNames.get(canonical)} (${categoryCounts.get(canonical)} ${categoryCounts.get(canonical) === 1 ? 'item' : 'items'})</option>
            `).join("");

            // Default to first valid category
            const defaultCategory = validCategories.includes("laptop_notebook") ? "laptop_notebook" : validCategories[0];
            categorySelect.value = defaultCategory;
            await fetchAndRenderRecommendations(defaultCategory);
        } catch (error) {
            categorySelect.innerHTML = '<option value="">Categories unavailable</option>';
            status.textContent = "The live category data is unavailable right now.";
        }
    };

    const fetchAndRenderRecommendations = async (selectedCategory) => {
        if (!selectedCategory) return;
        const label = canonicalLabels[selectedCategory] || selectedCategory;

        if (predictedDisplay) predictedDisplay.textContent = label;
        grid.innerHTML = '<div class="card" style="padding:20px;grid-column:1/-1;">Loading recommended products...</div>';
        status.textContent = `Finding catalogue products for ${label}...`;

        try {
            const result = await apiFetch("/api/recommendations", {
                method: "POST",
                body: JSON.stringify({ predicted_category: selectedCategory, limit: 6 })
            });

            if (!result.products || result.products.length === 0) {
                grid.innerHTML = '<div class="card" style="padding:20px;grid-column:1/-1;">No products available for this category.</div>';
                status.textContent = "No products found for this category.";
                return;
            }

            grid.innerHTML = result.products.map((product) => productCard(product, result.predicted_category)).join("");
            status.textContent = `Showing ${result.products.length} ${result.products.length === 1 ? 'product' : 'products'} from the predicted ${label} category.`;
        } catch (error) {
            grid.innerHTML = '<div class="card" style="padding:20px;grid-column:1/-1;">Could not load recommendations.</div>';
            status.textContent = error.message;
        }
    };

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        await fetchAndRenderRecommendations(categorySelect.value);
    });

    categorySelect.addEventListener("change", async () => {
        await fetchAndRenderRecommendations(categorySelect.value);
    });

    grid.addEventListener("click", async (event) => {
        const cartButton = event.target.closest(".add-recommendation");
        if (cartButton) {
            const id = Number(cartButton.dataset.id);
            try {
                await apiFetch("/api/cart", { method: "POST", body: JSON.stringify({ product_id: id, quantity: 1 }) });
                showDemoToast("Product added to your cart.");
            } catch (error) {
                showDemoToast(error.message);
            }
            return;
        }

        const wishlistButton = event.target.closest(".wishlist-button");
        if (wishlistButton) {
            const id = Number(wishlistButton.dataset.id);
            try {
                await apiFetch("/api/wishlist", { method: "POST", body: JSON.stringify({ product_id: id }) });
                wishlistButton.classList.add("is-saved");
                wishlistButton.textContent = "♥";
                showDemoToast("Saved to your wishlist.");
            } catch (error) {
                showDemoToast(error.message);
            }
        }
    });

    await loadExplanationData();
    await populateCategories();
});
