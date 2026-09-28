/* Shared frontend helpers and responsive navigation. */
document.addEventListener('DOMContentLoaded',()=>{
    const menu=document.querySelector('.menu-toggle');
    const nav=document.querySelector('.primary-nav');
    const actions=document.querySelector('.nav-actions');
    if(menu)menu.addEventListener('click',()=>{
        const open=nav?.classList.toggle('is-open');
        actions?.classList.toggle('is-open', open);
        menu.setAttribute('aria-expanded', String(Boolean(open)));
    });
});
function showDemoToast(message){const toast=document.getElementById('toast');if(!toast)return;toast.textContent=message;toast.classList.add('is-visible');clearTimeout(window.demoToastTimer);window.demoToastTimer=setTimeout(()=>toast.classList.remove('is-visible'),2800);}

/* Small wrapper used by pages that communicate with Flask JSON endpoints. */
async function apiFetch(url, options = {}) {
    const response = await fetch(url, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The request could not be completed.");
    return data;
}
