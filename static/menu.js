(() => {
  const btn = document.getElementById("menu-btn");
  const menu = document.getElementById("mobile-menu");
  const check = document.getElementById("menu-check");

  if (!btn || !menu || !check) return;

  const focusablesSelector = "a, button, input, textarea, select, [tabindex]";

  function setMenu(open) {
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    menu.setAttribute("aria-hidden", open ? "false" : "true");

    if (!open) {
      menu.setAttribute("inert", "");
      menu.querySelectorAll(focusablesSelector).forEach((el) => {
        el.setAttribute("tabindex", "-1");
      });
    } else {
      menu.removeAttribute("inert");
      menu.querySelectorAll("[tabindex='-1']").forEach((el) => {
        el.removeAttribute("tabindex");
      });
    }

    check.checked = !!open;
    document.body.style.overflow = open ? "hidden" : "";
  }

  function toggleMenu() {
    const isOpen = btn.getAttribute("aria-expanded") === "true";
    setMenu(!isOpen);
  }

  function closeMenu() {
    setMenu(false);
    btn.focus(); // nice keyboard UX
  }

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    toggleMenu();
  });

  // Close when clicking any link inside the menu
  menu.addEventListener("click", (e) => {
    const link = e.target.closest("a");
    if (!link) return;

    // If it's an in-page anchor, close menu immediately.
    // Tel links also fine to close.
    closeMenu();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });

  // Ensure correct initial state
  setMenu(false);
})();
