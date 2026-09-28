document.addEventListener("DOMContentLoaded", () => {
    const container = document.getElementById("cart-items");
    async function loadCart() {
        try {
            const items = await apiFetch("/api/cart");
            const total = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
            container.innerHTML = items.map((item) => `<div class="cart-item"><img src="${item.image_url}" alt="${item.name}"><div><b>${item.brand} ${item.name}</b><p>₹${Number(item.price).toLocaleString("en-IN")}</p><div class="quantity-control"><button data-dec="${item.id}" data-quantity="${item.quantity}">−</button> ${item.quantity} <button data-inc="${item.id}" data-quantity="${item.quantity}">+</button> <button data-remove="${item.id}">Remove</button></div></div><strong>₹${Number(item.price * item.quantity).toLocaleString("en-IN")}</strong></div>`).join("") || "<p>Your cart is empty.</p>";
            document.getElementById("subtotal").textContent = document.getElementById("total").textContent = `₹${total.toLocaleString("en-IN")}`;
        } catch (error) { container.innerHTML = "<p>Please log in to view your cart.</p>"; showDemoToast(error.message); }
    }
    container.addEventListener("click", async (event) => {
        const productId = Number(event.target.dataset.inc || event.target.dataset.dec || event.target.dataset.remove); if (!productId) return;
        try {
            if (event.target.dataset.remove) await apiFetch(`/api/cart/${productId}`, { method: "DELETE" });
            else { const quantity = Number(event.target.dataset.quantity) + (event.target.dataset.inc ? 1 : -1); if (quantity > 0) await apiFetch(`/api/cart/${productId}`, { method: "PATCH", body: JSON.stringify({ quantity }) }); }
            loadCart();
        } catch (error) { showDemoToast(error.message); }
    });
    loadCart();
});
