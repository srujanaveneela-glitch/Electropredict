/* Home page: real categories, featured electronics, and AI-recommended products.
   Every section renders its own real data so nothing stays stuck on "Loading". */
document.addEventListener("DOMContentLoaded", async () => {
    const toast = document.getElementById("toast");
    const navigation = document.getElementById("primary-navigation");
    const menuToggle = document.querySelector(".menu-toggle");
    const categoryGrid = document.getElementById("home-category-grid");
    const featuredGrid = document.getElementById("home-featured-grid");
    const recommendationGrid = document.getElementById("home-recommendation-grid");

    let toastTimer;
    const formatPrice = (value) => `₹${Number(value || 0).toLocaleString("en-IN")}`;

    function showToast(message) {
        if (!toast) return;
        window.clearTimeout(toastTimer);
        toast.textContent = message;
        toast.classList.add("is-visible");
        toastTimer = window.setTimeout(() => toast.classList.remove("is-visible"), 2800);
    }

    if (menuToggle && navigation) {
        menuToggle.addEventListener("click", () => {
            const isOpen = navigation.classList.toggle("is-open");
            menuToggle.setAttribute("aria-expanded", String(isOpen));
        });
    }

    /* Customer-facing names for the categories used by the catalogue. */
    const CANONICAL_LABELS = {
        smartphone: "Smartphones",
        laptop_notebook: "Laptops",
        tablet: "Tablets",
        smartwatch_clocks: "Smart Watches",
        audio: "Headphones",
        video: "Televisions & Video",
        computer_peripherals: "Computer Peripherals",
        computer_components: "Computer Components",
        telephone: "Telephones",
        desktop: "Desktops",
        camera: "Cameras",
        other_electronics: "Other Electronics",
    };

    const CATEGORY_ICONS = {
        smartphone: "",
        laptop_notebook: "💻",
        tablet: "📟",
        smartwatch_clocks: "⌚",
        audio: "🎧",
        video: "📺",
        computer_peripherals: "🖱️",
        computer_components: "🧩",
        telephone: "️",
        desktop: "🖥️",
        camera: "📷",
        other_electronics: "🔌",
    };

    const CATEGORY_CLASSES = {
        audio: "category-audio",
        smartwatch_clocks: "category-watch",
        camera: "category-camera",
        video: "category-monitor",
        computer_peripherals: "category-monitor",
    };

    function normalizeCategory(value) {
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
            "computer peripherals": "computer_peripherals",
            "computer components": "computer_components",
            computer_components: "computer_components",
            telephone: "telephone",
            telephones: "telephone",
            desktop: "desktop",
            desktops: "desktop",
            camera: "camera",
            cameras: "camera",
            other_electronics: "other_electronics",
            "other electronics": "other_electronics",
        };
        return map[normalized] || null;
    }

    function discountPercent(product) {
        const original = Number(product.original_price || product.price || 0);
        if (!original) return 0;
        return Math.max(0, Math.round(((original - product.price) / original) * 100));
    }

    function productCard(product) {
        const discount = discountPercent(product);
        return `
            <article class="product-card">
                <div class="product-image-wrap">
                    <button class="wishlist-button" type="button" data-id="${product.id}" aria-label="Save ${product.name} to wishlist"></button>
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
                        ${discount > 0 ? `<em>${discount}% off</em>` : ""}
                    </div>
                    <div class="card-actions">
                        <button class="button button-primary add-cart-button" type="button" data-id="${product.id}">Add to cart</button>
                        <a class="button button-secondary" href="/product-details?id=${product.id}">View details</a>
                    </div>
                </div>
            </article>
        `;
    }

    /* ---------- Categories ---------- */
    function renderCategories(products) {
        if (!categoryGrid) return;
        const counts = new Map();
        products.forEach((product) => {
            const canonical = normalizeCategory(product.category);
            if (!canonical) return;
            counts.set(canonical, (counts.get(canonical) || 0) + 1);
        });
        if (!counts.size) {
            categoryGrid.innerHTML = '<div class="card" style="padding:18px;grid-column:1/-1;">No categories are available right now.</div>';
            return;
        }
        categoryGrid.innerHTML = [...counts.entries()]
            .sort((a, b) => b[1] - a[1])
            .map(([canonical, count]) => {
                const label = CANONICAL_LABELS[canonical] || canonical;
                const extraClass = CATEGORY_CLASSES[canonical] || "";
                return `
                    <a class="category-card ${extraClass}" href="/products?category=${encodeURIComponent(canonical)}">
                        <span class="category-icon">${CATEGORY_ICONS[canonical] || "🔌"}</span>
                        <span>
                            <strong>${label}</strong>
                            <small>${count} product${count === 1 ? "" : "s"}</small>
                        </span>
                        <b>→</b>
                    </a>
                `;
            })
            .join("");
    }

    /* ---------- Featured electronics ---------- */
    function renderFeatured(products) {
        if (!featuredGrid) return;
        const featured = [...products]
            .sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0))
            .slice(0, 4);
        featuredGrid.innerHTML = featured.length
            ? featured.map(productCard).join("")
            : '<div class="card" style="padding:18px;grid-column:1/-1;">No featured products are available right now.</div>';
    }

    /* ---------- AI recommendations ---------- */
    async function loadRecommendations() {
        if (!recommendationGrid) return;
        try {
            const result = await apiFetch("/api/recommendations?limit=4");
            const products = Array.isArray(result.products) ? result.products : [];
            if (!products.length) {
                recommendationGrid.innerHTML = '<div class="card" style="padding:18px;grid-column:1/-1;">No recommendations are available right now.</div>';
                return;
            }
            const label = result.predicted_category_display || CANONICAL_LABELS[result.predicted_category] || "electronics";
            recommendationGrid.innerHTML = products.map((product) => {
                const discount = discountPercent(product);
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
                                ${discount > 0 ? `<em>${discount}% off</em>` : ""}
                            </div>
                            <p class="recommendation-why">Chosen for you because your shopping pattern points to ${label}.</p>
                            <div class="card-actions">
                                <button class="button button-primary add-cart-button" type="button" data-id="${product.id}">Add to cart</button>
                                <a class="button button-secondary" href="/product-details?id=${product.id}">View details</a>
                            </div>
                        </div>
                    </article>
                `;
            }).join("");
        } catch (error) {
            recommendationGrid.innerHTML = '<div class="card" style="padding:18px;grid-column:1/-1;">Recommendations are unavailable right now.</div>';
        }
    }

    /* ---------- Initial load ---------- */
    try {
        const products = await apiFetch("/api/products");
        renderCategories(products);
        renderFeatured(products);
    } catch (error) {
        if (categoryGrid) categoryGrid.innerHTML = '<div class="card" style="padding:18px;grid-column:1/-1;">Categories are unavailable right now.</div>';
        if (featuredGrid) featuredGrid.innerHTML = '<div class="card" style="padding:18px;grid-column:1/-1;">Featured products are unavailable right now.</div>';
    }
    loadRecommendations();

    /* ---------- Add to cart ---------- */
    document.addEventListener("click", async (event) => {
        const addButton = event.target.closest(".add-cart-button");
        if (!addButton) return;
        const productId = Number(addButton.dataset.id);
        if (!productId) return;
        try {
            await apiFetch("/api/cart", { method: "POST", body: JSON.stringify({ product_id: productId, quantity: 1 }) });
            showToast("Added to your cart.");
        } catch (error) {
            showToast(error.message);
        }
    });

    /* ---------- Wishlist ---------- */
    document.addEventListener("click", async (event) => {
        const wishButton = event.target.closest(".wishlist-button");
        if (!wishButton) return;
        const productId = Number(wishButton.dataset.id);
        if (!productId) return;
        try {
            await apiFetch("/api/wishlist", { method: "POST", body: JSON.stringify({ product_id: productId }) });
            wishButton.classList.add("is-saved");
            wishButton.textContent = "♥";
            showToast("Saved to your wishlist.");
        } catch (error) {
            showToast(error.message);
        }
    });

    document.getElementById("site-search-form")?.addEventListener("submit", (event) => {
        const input = document.getElementById("site-search");
        if (!input || !input.value.trim()) {
            event.preventDefault();
            showToast("Enter a product, brand, or category to search.");
        }
    });

});