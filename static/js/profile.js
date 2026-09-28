document.addEventListener("DOMContentLoaded", async () => {
    try {
        const data = await apiFetch("/api/me");
        if (!data.user) { window.location.href = "/login"; return; }
        document.querySelector(".profile-nav b").textContent = data.user.name;
        document.querySelector(".profile-grid section.card").innerHTML = `<h2>Account information</h2><p><b>Name:</b> ${data.user.name}</p><p><b>Email:</b> ${data.user.email}</p><p><b>Created:</b> ${data.user.created_at}</p>`;
    } catch (error) { showDemoToast(error.message); }
    document.getElementById("logout").onclick = async () => { await apiFetch("/api/logout", { method: "POST" }); window.location.href = "/"; };
});
