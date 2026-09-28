/* Show only the signed-in user's activity records created through the Flask API. */
document.addEventListener("DOMContentLoaded", async () => {
    const body = document.querySelector(".activity-table tbody");
    try {
        const events = await apiFetch("/api/activity");
        body.innerHTML = events.map((event) => `<tr><td>Current user</td><td>${event.product_id || "—"}</td><td>${event.category || "—"}</td><td><span class="event-tag">${event.action_type}</span></td><td>${event.price ? `₹${Number(event.price).toLocaleString("en-IN")}` : "—"}</td><td>${event.created_at}</td></tr>`).join("") || "<tr><td colspan='6'>No activity recorded yet.</td></tr>";
    } catch (error) {
        body.innerHTML = "<tr><td colspan='6'>Please log in to view your activity records.</td></tr>";
    }
});
