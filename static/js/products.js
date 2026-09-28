document.addEventListener("DOMContentLoaded", () => {

    let products = [];

    const grid = document.getElementById("product-grid");
    const emptyState = document.getElementById("empty-state");
    const count = document.getElementById("results-count");
    const toast = document.getElementById("toast");

    const wishlist = new Set();
    let toastTimer;


    /* =========================================================
       HELPERS
    ========================================================= */

    function formatPrice(price) {
        return "₹" + Number(price || 0).toLocaleString("en-IN");
    }

    function discount(product) {
        const price = Number(product.price || 0);
        const originalPrice = Number(
            product.originalPrice ?? product.original_price ?? product.price ?? 0
        );
        if (!originalPrice || originalPrice <= price) return 0;
        return Math.round((1 - price / originalPrice) * 100);
    }

    function escapeHtml(value) {
        return String(value ?? "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    /* FIX: one shared, flexible way to find the search box */
    function findSearchInput() {
        return (
            document.getElementById("product-search") ||
            document.getElementById("search-input") ||
            document.querySelector("#catalogue-search input")
        );
    }


    /* =========================================================
       CATEGORY NORMALIZATION
    ========================================================= */

    function normalizeCategory(category) {
        const value = String(category || "")
            .trim()
            .toLowerCase()
            .replace(/-/g, "_")
            .replace(/\s+/g, "_");

        const map = {
            smartphone: "smartphones",
            smartphones: "smartphones",
            mobile: "smartphones",
            mobiles: "smartphones",
            mobile_phone: "smartphones",
            mobile_phones: "smartphones",

            laptop: "laptops",
            laptops: "laptops",
            laptop_notebook: "laptops",
            notebook: "laptops",
            notebooks: "laptops",

            tablet: "tablets",
            tablets: "tablets",

            watch: "smartwatch",
            watches: "smartwatch",
            smartwatch: "smartwatch",
            smartwatches: "smartwatch",
            smartwatch_clocks: "smartwatch",

            audio: "audio",
            headphone: "audio",
            headphones: "audio",
            earphone: "audio",
            earphones: "audio",

            camera: "camera",
            cameras: "camera",

            video: "video",
            videos: "video",

            computer_peripherals: "computer_peripherals",
            computer_components: "computer_components",

            telephone: "telephone",
            telephones: "telephone",

            desktop: "desktop",
            desktops: "desktop",

            other_electronics: "other_electronics"
        };

        return map[value] || value;
    }


    /* =========================================================
       SEARCH → CATEGORY
    ========================================================= */

    function categoryFromSearch(searchText) {
        const value = String(searchText || "")
            .trim()
            .toLowerCase()
            .replace(/-/g, " ")
            .replace(/\s+/g, " ");

        const categoryMap = {
            "laptop": "laptops",
            "laptops": "laptops",
            "laptop notebook": "laptops",
            "notebook": "laptops",
            "notebooks": "laptops",

            "smartphone": "smartphones",
            "smartphones": "smartphones",
            "mobile": "smartphones",
            "mobiles": "smartphones",
            "mobile phone": "smartphones",
            "mobile phones": "smartphones",

            "tablet": "tablets",
            "tablets": "tablets",

            "watch": "smartwatch",
            "watches": "smartwatch",
            "smartwatch": "smartwatch",
            "smartwatches": "smartwatch",

            "audio": "audio",
            "headphone": "audio",
            "headphones": "audio",
            "earphone": "audio",
            "earphones": "audio",

            "camera": "camera",
            "cameras": "camera",

            "video": "video",
            "videos": "video",

            "desktop": "desktop",
            "desktops": "desktop"
        };

        return categoryMap[value] || "";
    }


    /* =========================================================
       TOAST
    ========================================================= */

    function showToast(message) {
        if (!toast) return;
        toast.textContent = message;
        toast.classList.add("show");
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toast.classList.remove("show"), 2500);
    }


    /* =========================================================
       API
    ========================================================= */

    async function apiFetch(url, options = {}) {
        const response = await fetch(url, {
            credentials: "same-origin",
            ...options
        });
        if (!response.ok) {
            throw new Error(`Request failed: ${response.status}`);
        }
        return response.json();
    }


    /* =========================================================
       URL PARAMETERS
       FIX: also accepts ?products=laptops
    ========================================================= */

    const params = new URLSearchParams(window.location.search);

    const searchParam = params.get("search") || params.get("q") || "";

    const categoryParam =
        params.get("category") || params.get("products") || "";

    let urlCategory = categoryParam ? normalizeCategory(categoryParam) : "";


    /* =========================================================
       LOAD PRODUCTS
    ========================================================= */

    async function loadProducts() {
        try {
            const data = await apiFetch("/api/products");

            if (Array.isArray(data)) {
                products = data;
            } else if (data && Array.isArray(data.products)) {
                products = data.products;
            } else {
                products = [];
            }

            products = products.map((product) => ({
                ...product,
                id: Number(product.id),
                price: Number(product.price || 0),
                originalPrice: Number(
                    product.originalPrice ??
                    product.original_price ??
                    product.price ??
                    0
                ),
                rating: Number(product.rating || 0),
                reviewCount: Number(
                    product.reviewCount ?? product.review_count ?? 0
                )
            }));

            /* URL category -> dropdown */
            if (categoryParam) {
                const categoryFilter = document.getElementById("category-filter");
                if (categoryFilter) {
                    let matchingOption = null;
                    Array.from(categoryFilter.options || []).forEach((option) => {
                        if (
                            normalizeCategory(option.value) ===
                            normalizeCategory(categoryParam)
                        ) {
                            matchingOption = option.value;
                        }
                    });
                    if (matchingOption !== null) {
                        categoryFilter.value = matchingOption;
                    }
                }
            }

            /* URL search -> search box */
            if (searchParam) {
                const input = findSearchInput();
                if (input) input.value = searchParam;
            }

            renderProducts();

        } catch (error) {
            console.error("Could not load products:", error);
            products = [];
            if (grid) grid.innerHTML = "";
            if (emptyState) {
                emptyState.style.display = "block";
                emptyState.textContent =
                    "Unable to load products: " + (error && error.message ? error.message : error);
            }
            if (count) count.textContent = "0 products";
        }
    }


    /* =========================================================
       FILTER PRODUCTS
    ========================================================= */

    function getFilteredProducts() {

        /* Search text (FIX: uses shared helper) */
        const input = findSearchInput();
        const searchTerm = (input ? input.value : searchParam)
            .trim()
            .toLowerCase();

        /* Category dropdown */
        const categoryFilterEl = document.getElementById("category-filter");
        let selectedCategory = "";
        if (categoryFilterEl) {
            selectedCategory = String(categoryFilterEl.value || "")
                .trim()
                .toLowerCase();
        }

        const searchCategory = categoryFromSearch(searchTerm);

        /* Final category: search > dropdown > URL */
        let finalCategory = "";

        if (searchCategory) {
            finalCategory = searchCategory;
        } else if (
            selectedCategory &&
            selectedCategory !== "all" &&
            selectedCategory !== "all_categories"
        ) {
            finalCategory = normalizeCategory(selectedCategory);
        } else if (urlCategory) {
            finalCategory = normalizeCategory(urlCategory);
        }

        /* Price */
        const minPriceInput = document.getElementById("min-price");
        const maxPriceInput = document.getElementById("max-price");
        const minPrice = minPriceInput ? Number(minPriceInput.value || 0) : 0;
        const maxPrice = maxPriceInput
            ? Number(maxPriceInput.value || Infinity)
            : Infinity;

        /* Rating */
        const ratings = [
            ...document.querySelectorAll('input[name="rating"]:checked')
        ]
            .map((el) => Number(el.value))
            .filter((v) => !Number.isNaN(v));
        const minimumRating = ratings.length ? Math.max(...ratings) : 0;

        /* Sale */
        const saleInput =
            document.querySelector('input[name="sale"]:checked') ||
            document.getElementById("discount-only") ||
            document.getElementById("sale-filter");
        const saleOnly = saleInput ? Boolean(saleInput.checked) : false;

        const filtered = products.filter((product) => {

            if (finalCategory) {
                if (normalizeCategory(product.category) !== finalCategory) {
                    return false;
                }
            }

            /* Text search only when the text is not a category word */
            if (searchTerm && !searchCategory) {
                const searchableText = [
                    product.name,
                    product.brand,
                    product.category,
                    product.description
                ]
                    .filter(Boolean)
                    .join(" ")
                    .toLowerCase();

                if (!searchableText.includes(searchTerm)) return false;
            }

            const price = Number(product.price || 0);
            if (price < minPrice || price > maxPrice) return false;

            if (Number(product.rating || 0) < minimumRating) return false;

            if (saleOnly && discount(product) <= 0) return false;

            return true;
        });

        console.log("SEARCH:", searchTerm, "| SEARCH CATEGORY:", searchCategory,
            "| FINAL CATEGORY:", finalCategory,
            "| SHOWING:", filtered.length, "of", products.length);

        return filtered;
    }


    /* =========================================================
       SORT PRODUCTS
    ========================================================= */

    function sortProducts(list) {
        const sortEl = document.getElementById("sort-select");
        const sortValue = sortEl ? sortEl.value : "default";
        const sorted = [...list];

        switch (sortValue) {
            case "price-low":
            case "price_asc":
            case "low-high":
                sorted.sort((a, b) => Number(a.price || 0) - Number(b.price || 0));
                break;

            case "price-high":
            case "price_desc":
            case "high-low":
                sorted.sort((a, b) => Number(b.price || 0) - Number(a.price || 0));
                break;

            case "rating":
            case "rating_desc":
                sorted.sort((a, b) => Number(b.rating || 0) - Number(a.rating || 0));
                break;

            case "newest":
                sorted.sort((a, b) => Number(b.id || 0) - Number(a.id || 0));
                break;

            default:
                sorted.sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
                break;
        }

        return sorted;
    }


    /* =========================================================
       URL SYNC (puts the search text in the address bar)
    ========================================================= */

    function syncUrl(push = false) {
        const input = findSearchInput();
        const text = input ? input.value.trim() : "";

        const url = new URL(window.location.href);
        url.searchParams.delete("category");
        url.searchParams.delete("products");
        url.searchParams.delete("q");

        if (text) {
            url.searchParams.set("search", text);
        } else {
            url.searchParams.delete("search");
        }

        const newUrl = url.pathname + url.search;
        const currentUrl = window.location.pathname + window.location.search;
        if (newUrl === currentUrl) return;

        if (push) {
            window.history.pushState({}, "", newUrl);
        } else {
            window.history.replaceState({}, "", newUrl);
        }
    }


    /* =========================================================
       RENDER PRODUCTS
    ========================================================= */

    function renderProducts() {
        if (!grid) {
            console.error("Missing #product-grid");
            return;
        }

        const filteredProducts = sortProducts(getFilteredProducts());

        grid.innerHTML = "";

        if (count) {
            count.textContent = `${filteredProducts.length} product${
                filteredProducts.length === 1 ? "" : "s"
            }`;
        }

        if (emptyState) {
            emptyState.style.display =
                filteredProducts.length === 0 ? "block" : "none";
        }

        if (filteredProducts.length === 0) return;

        filteredProducts.forEach((product) => {

            const productId = Number(product.id);
            const salePercent = discount(product);

            const card = document.createElement("div");
            card.className = "product-card";

            const image = product.imageUrl || product.image_url || "";
            const brand = escapeHtml(product.brand || "Unknown Brand");
            const name = escapeHtml(product.name || "Unnamed Product");
            const category = escapeHtml(product.category || "");
            const price = Number(product.price || 0);
            const originalPrice = Number(
                product.originalPrice ?? product.original_price ?? price
            );
            const rating = Number(product.rating || 0);
            const reviewCount = Number(
                product.reviewCount ?? product.review_count ?? 0
            );

            card.innerHTML = `
                <div class="product-image-wrap">
                    ${
                        image
                            ? `<img src="${escapeHtml(image)}" alt="${name}"
                                    class="product-image" loading="lazy"
                                    onerror="this.style.display='none';this.parentElement.classList.add('image-error');">`
                            : `<div class="product-image-placeholder">No Image</div>`
                    }

                    ${
                        salePercent > 0
                            ? `<span class="sale-badge">${salePercent}% OFF</span>`
                            : ""
                    }

                    <button type="button" class="wishlist-button"
                            data-product-id="${productId}"
                            aria-label="Add to wishlist">♡</button>
                </div>

                <div class="product-info">
                    <div class="product-brand">${brand}</div>
                    <h3 class="product-name">${name}</h3>
                    <div class="product-category">${category}</div>

                    <div class="product-rating">
                        ★ ${rating.toFixed(1)}
                        <span>(${reviewCount})</span>
                    </div>

                    <div class="product-price">
                        <strong>${formatPrice(price)}</strong>
                        ${
                            originalPrice > price
                                ? `<span class="original-price">${formatPrice(originalPrice)}</span>`
                                : ""
                        }
                    </div>

                    <div class="product-actions">
                        <a href="/product-details?id=${productId}"
                           class="details-button"
                           data-product-id="${productId}">View Details</a>

                        <button type="button" class="add-cart-button"
                                data-product-id="${productId}">Add to Cart</button>
                    </div>
                </div>
            `;

            grid.appendChild(card);
        });

        attachProductHandlers();
    }


    /* =========================================================
       PRODUCT HANDLERS
    ========================================================= */

    function attachProductHandlers() {

        /* View details */
        document.querySelectorAll(".details-button").forEach((button) => {
            button.addEventListener("click", (event) => {
                event.preventDefault();
                const id = Number(button.dataset.productId);
                if (Number.isInteger(id) && id > 0) {
                    window.location.href = `/product-details?id=${id}`;
                }
            });
        });

        /* Wishlist */
        document.querySelectorAll(".wishlist-button").forEach((button) => {
            button.addEventListener("click", async () => {
                const id = Number(button.dataset.productId);
                if (!id) return;

                try {
                    await apiFetch("/api/wishlist/toggle", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ product_id: id })
                    });

                    if (wishlist.has(id)) {
                        wishlist.delete(id);
                        button.textContent = "♡";
                        showToast("Removed from wishlist");
                    } else {
                        wishlist.add(id);
                        button.textContent = "♥";
                        showToast("Added to wishlist");
                    }
                } catch (error) {
                    console.error("Wishlist error:", error);
                    showToast("Unable to update wishlist");
                }
            });
        });

        /* Cart */
        document.querySelectorAll(".add-cart-button").forEach((button) => {
            button.addEventListener("click", async () => {
                const id = Number(button.dataset.productId);
                if (!id) return;

                try {
                    await apiFetch("/api/cart/add", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ product_id: id, quantity: 1 })
                    });
                    showToast("Product added to cart");
                } catch (error) {
                    console.error("Cart error:", error);
                    showToast("Unable to add product to cart");
                }
            });
        });
    }


    /* =========================================================
       EVENT LISTENERS
    ========================================================= */

    /* Category dropdown */
    const categoryFilter = document.getElementById("category-filter");
    if (categoryFilter) {
        categoryFilter.addEventListener("change", () => {
            urlCategory = "";
            renderProducts();
        });
    }

    /* Checkbox filters */
    document
        .querySelectorAll(
            'input[name="category"], input[name="rating"], input[name="sale"], #discount-only'
        )
        .forEach((input) => input.addEventListener("change", renderProducts));

    /* Price filter */
    document
        .querySelectorAll("#min-price, #max-price")
        .forEach((input) => input.addEventListener("input", renderProducts));

    /* Sort */
    const sortSelect = document.getElementById("sort-select");
    if (sortSelect) {
        sortSelect.addEventListener("change", renderProducts);
    }

    /* Search box (FIX: shared helper + form found from the input itself) */
    const searchInput = findSearchInput();

    if (searchInput) {
        searchInput.addEventListener("input", () => {
            urlCategory = "";
            syncUrl(false);
            renderProducts();
        });

        searchInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
                event.preventDefault();
                urlCategory = "";
                syncUrl(true);
                renderProducts();
            }
        });
    }

    const searchForm =
        document.getElementById("catalogue-search") ||
        document.getElementById("search-form") ||
        (searchInput ? searchInput.closest("form") : null);

    if (searchForm) {
        searchForm.addEventListener("submit", (event) => {
            event.preventDefault();
            urlCategory = "";
            syncUrl(true);
            renderProducts();
        });
    }

    /* Clear filters */
    const clearFilters = document.getElementById("clear-filters");
    if (clearFilters) {
        clearFilters.addEventListener("click", () => {

            if (categoryFilter) categoryFilter.value = "";

            document
                .querySelectorAll(
                    'input[name="category"], input[name="rating"], input[name="sale"]'
                )
                .forEach((input) => (input.checked = false));

            document
                .querySelectorAll("#min-price, #max-price")
                .forEach((input) => (input.value = ""));

            if (searchInput) searchInput.value = "";

            urlCategory = "";
            window.history.replaceState({}, "", "/products");
            renderProducts();
        });
    }

    /* Mobile filter panel */
    const filterToggle = document.getElementById("filter-toggle");
    const filterPanel = document.getElementById("filter-panel");
    if (filterToggle && filterPanel) {
        filterToggle.addEventListener("click", () => {
            filterPanel.classList.toggle("active");
        });
    }


    /* =========================================================
       START
    ========================================================= */

    loadProducts();

});