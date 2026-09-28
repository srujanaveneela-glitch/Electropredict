document.addEventListener("DOMContentLoaded", () => {
    const grid = document.getElementById("wishlist-grid");
    const empty = document.getElementById("empty-wishlist");
    const formatPrice = (price) => `₹${Number(price).toLocaleString("en-IN")}`;

    const card = (product) => {
        const discountPct = Math.max(0, Math.round(((product.original_price || product.price) - product.price) / (product.original_price || product.price) * 100));
        return `
            <article class="product-card">
                <div class="product-image-wrap">
                    <button class="wishlist-button is-saved" type="button" data-remove="${product.id}" aria-label="Remove ${product.name} from wishlist">♥</button>
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
                    <div class="card-actions">
                        <button class="button button-primary" type="button" data-add="${product.id}">Add to cart</button>
                        <button class="button button-secondary" type="button" data-remove="${product.id}">Remove</button>
                    </div>
                </div>
            </article>
        `;
    };

    async function loadWishlist() {
        try {
            const products = await apiFetch("/api/wishlist");
            if (!products || products.length === 0) {
                grid.innerHTML = "";
                empty.hidden = false;
                return;
            }
            grid.innerHTML = products.map(card).join("");
            empty.hidden = true;
        } catch (error) {
            grid.innerHTML = "";
            empty.hidden = false;
            showDemoToast(error.message);
        }
    }

    grid.addEventListener("click", async (event) => {
        const removeButton = event.target.closest("[data-remove]");
        const addButton = event.target.closest("[data-add]");

        if (removeButton) {
            const productId = Number(removeButton.dataset.remove);
            try {
                await apiFetch(`/api/wishlist/${productId}`, { method: "DELETE" });
                showDemoToast("Removed from wishlist.");
                await loadWishlist();
            } catch (error) {
                showDemoToast(error.message);
            }
            return;
        }

        if (addButton) {
            const productId = Number(addButton.dataset.add);
            try {
                await apiFetch("/api/cart", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: 1 }) });
                showDemoToast("Added to cart.");
            } catch (error) {
                showDemoToast(error.message);
            }
        }
    });

    loadWishlist();
});
