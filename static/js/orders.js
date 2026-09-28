document.addEventListener("DOMContentLoaded", async () => {
    const container = document.querySelector(".section .container");
    try {
        const orders = await apiFetch("/api/orders");
        container.innerHTML = orders.map((order) => `<article class="card order-card"><div class="order-top"><div><b>Order #EP-${order.id}</b><p class="order-date">${order.created_at}</p></div><span class="status">${order.status}</span></div>${order.items.map((item) => `<div class="order-product"><span>${item.brand} ${item.name} × ${item.quantity}</span><b>₹${Number(item.unit_price * item.quantity).toLocaleString("en-IN")}</b></div>`).join("")}<div class="order-product"><strong>Total</strong><strong>₹${Number(order.total_amount).toLocaleString("en-IN")}</strong></div></article>`).join("") || "<p>No orders yet.</p>";
    } catch (error) { container.innerHTML = "<p>Please log in to view your order history.</p>"; showDemoToast(error.message); }
});
