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
      // Prevent focus from entering the closed menu
      menu.setAttribute("inert", "");
      menu.querySelectorAll(focusablesSelector).forEach((el) => {
        el.setAttribute("tabindex", "-1");
      });
    } else {
      // Restore focusability when opened
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
    btn.focus(); // Return focus to the toggle button
  }

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    toggleMenu();
  });

  // Close the menu when a link inside it is clicked
  menu.addEventListener("click", (e) => {
    const link = e.target.closest("a");
    if (!link) return;

    closeMenu();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });

  // Start closed to match ARIA/inert/tabindex state
  setMenu(false);
})();
