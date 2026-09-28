document.addEventListener("DOMContentLoaded", () => {
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (loginForm) {
        loginForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const inputs = loginForm.querySelectorAll("input");
            try {
                await apiFetch("/api/login", { method: "POST", body: JSON.stringify({ email: inputs[0].value, password: inputs[1].value }) });
                window.location.href = "/profile";
            } catch (error) { showDemoToast(error.message); }
        });
    }

    if (registerForm) {
        registerForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const inputs = registerForm.querySelectorAll("input");
            if (inputs[2].value !== inputs[3].value) { showDemoToast("Passwords do not match."); return; }
            try {
                await apiFetch("/api/register", { method: "POST", body: JSON.stringify({ name: inputs[0].value, email: inputs[1].value, password: inputs[2].value }) });
                window.location.href = "/profile";
            } catch (error) { showDemoToast(error.message); }
        });
    }
});
