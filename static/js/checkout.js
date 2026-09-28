document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("checkout-form").addEventListener("submit", async (event) => {
        event.preventDefault();
        const address = document.querySelector("textarea").value.trim();
        try {
            const result = await apiFetch("/api/checkout", { method: "POST", body: JSON.stringify({ delivery_address: address }) });
            document.getElementById("checkout-area").innerHTML = `<div class="card success-box"><div class="success-icon">✓</div><h1>Demo order placed</h1><p>Order #${result.order_id} was saved in your local development database. No payment was taken.</p><a class="button button-primary" href="/orders">View orders</a></div>`;
        } catch (error) { showDemoToast(error.message); }
    });
});
