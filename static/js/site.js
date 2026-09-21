/* Sandlådan AB — the site's only script. No framework, no dependencies.
   1. Mobile menu (open/close, Escape, inert, scroll lock)
   2. Availability line: GET /api/status → swap into #status
   3. Quote form: POST as FormData → swap the server's HTML notice into #form-response
   Everything degrades: without JS the form posts normally and the status line keeps its fallback text. */
(() => {
  "use strict";

  /* ── 1. Mobile menu ─────────────────────────────── */
  const btn = document.getElementById("menu-btn");
  const menu = document.getElementById("mobile-menu");

  if (btn && menu) {
    const setMenu = (open) => {
      btn.setAttribute("aria-expanded", String(open));
      btn.setAttribute("aria-label", open ? "Stäng meny" : "Öppna meny");
      menu.setAttribute("aria-hidden", String(!open));
      if (open) menu.removeAttribute("inert");
      else menu.setAttribute("inert", "");
      document.body.style.overflow = open ? "hidden" : "";
    };

    btn.addEventListener("click", () => {
      setMenu(btn.getAttribute("aria-expanded") !== "true");
    });

    menu.addEventListener("click", (e) => {
      if (e.target.closest("a")) {
        setMenu(false);
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && btn.getAttribute("aria-expanded") === "true") {
        setMenu(false);
        btn.focus();
      }
    });

    setMenu(false);
  }

  /* ── 2. Availability line ───────────────────────── */
  const status = document.getElementById("status");
  const statusUrl = status && status.dataset.statusUrl;

  if (status && statusUrl) {
    fetch(statusUrl, { headers: { Accept: "text/html" }, credentials: "same-origin" })
      .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
      .then((html) => {
        // Same-origin response from our own API: two spans, no scripts.
        status.innerHTML = html;
      })
      .catch(() => {
        /* keep the fallback text */
      });
  }

  /* ── 3. Quote form ──────────────────────────────── */
  const form = document.querySelector("form[data-async]");

  if (form) {
    const target = document.querySelector(form.dataset.target || "#form-response");
    const submit = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", async (e) => {
      if (!form.reportValidity()) return; // native validation messages
      e.preventDefault();
      if (!target) return;

      const label = submit ? submit.textContent : "";
      if (submit) {
        submit.disabled = true;
        submit.setAttribute("aria-disabled", "true");
        submit.textContent = "Skickar…";
      }

      try {
        const res = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: { Accept: "text/html" },
          credentials: "same-origin",
        });
        target.innerHTML = await res.text(); // server-rendered <div class="notice …"> from /api/offert
        if (res.ok) form.reset();
      } catch {
        target.innerHTML =
          '<div class="notice notice--err" role="alert"><p><strong>Kunde inte skicka.</strong> Kontrollera uppkopplingen och försök igen, eller ring oss.</p></div>';
      } finally {
        if (submit) {
          submit.disabled = false;
          submit.removeAttribute("aria-disabled");
          submit.textContent = label;
        }
        target.focus({ preventScroll: false });
      }
    });
  }
})();
