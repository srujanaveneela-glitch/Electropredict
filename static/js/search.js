document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("search-form");
    const searchInput = document.getElementById("search-input");
    const category = document.getElementById("category");
    const rating = document.getElementById("rating");
    const resultCount = document.getElementById("result-count");
    const resultList = document.getElementById("result-list");

    async function searchFromDatabase() {
        const searchValue = searchInput.value.trim();

        const params = new URLSearchParams();

        if (searchValue) {
            params.set("search", searchValue);
        }

        /*
         * IMPORTANT:
         * Do not send "laptop_notebook" here.
         * Your actual database category is "Laptops".
         */

        if (category.value && category.value !== "all") {
            params.set("category", category.value);
        }

        try {
            const url = `/api/products?${params.toString()}`;

            console.log("Searching:", url);

            let products = await apiFetch(url);

            console.log("API returned:", products.length, products);

            /*
             * Rating filter
             */
            const minimumRating = Number(rating.value || 0);

            products = products.filter(product => {
                return Number(product.rating || 0) >= minimumRating;
            });

            /*
             * Display count
             */
            resultCount.textContent =
                `${products.length} product${products.length === 1 ? "" : "s"} found`;

            /*
             * No results
             */
            if (products.length === 0) {
                resultList.innerHTML = `
                    <div class="card"
                         style="padding:30px;grid-column:1/-1;text-align:center;">

                        <h2>No products found</h2>

                        <p class="small-muted">
                            No products match "${searchValue}".
                        </p>

                    </div>
                `;

                return;
            }

            /*
             * Render ONLY the products returned by the API
             */
            resultList.innerHTML = products.map(product => `
                <article class="card search-result product-card">

                    <div class="product-image-wrap">
                        <img
                            src="${product.image_url || ""}"
                            alt="${product.name || "Product"}"
                            loading="lazy"
                            onerror="this.style.display='none'"
                        >
                    </div>

                    <div class="product-info">

                        <p class="brand-name">
                            ${product.brand || "Unknown Brand"}
                        </p>

                        <h3>
                            ${product.name || "Unnamed Product"}
                        </h3>

                        <p class="rating">
                            ★ ${Number(product.rating || 0).toFixed(1)}
                        </p>

                        <div class="price-row">
                            <strong>
                                ₹${Number(product.price || 0).toLocaleString("en-IN")}
                            </strong>
                        </div>

                        <div class="card-actions">

                            <a
                                class="details-button"
                                href="/product-details?id=${product.id}"
                            >
                                View Details
                            </a>

                        </div>

                    </div>

                </article>
            `).join("");

        } catch (error) {

            console.error("Search error:", error);

            resultCount.textContent = "Unable to load products.";

            resultList.innerHTML = `
                <div class="card"
                     style="padding:30px;grid-column:1/-1;text-align:center;">

                    <h2>Something went wrong</h2>

                    <p class="small-muted">
                        Unable to load products. Please try again.
                    </p>

                </div>
            `;
        }
    }

    /*
     * Search button
     */
    form.addEventListener("submit", event => {
        event.preventDefault();

        const value = searchInput.value.trim();

        /*
         * Keep the URL synchronized with the search.
         */
        const newUrl = value
            ? `/search?q=${encodeURIComponent(value)}`
            : `/search`;

        window.history.replaceState({}, "", newUrl);

        searchFromDatabase();
    });

    /*
     * Category filter
     */
    category.addEventListener("change", searchFromDatabase);

    /*
     * Rating filter
     */
    rating.addEventListener("change", searchFromDatabase);

    /*
     * Read search query from URL
     */
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get("q");

    if (query) {
        searchInput.value = query;
    }

    /*
     * Initial search
     */
    searchFromDatabase();
});