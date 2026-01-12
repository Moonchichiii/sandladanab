(() => {
  const btn = document.getElementById("menu-btn");
  const menu = document.getElementById("mobile-menu");
  const check = document.getElementById("menu-check");

  if (!btn || !menu || !check) return;

  function setMenu(open) {
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    menu.setAttribute("aria-hidden", open ? "false" : "true");
    check.checked = !!open;
    document.body.style.overflow = open ? "hidden" : "";
  }

  function toggleMenu() {
    const isOpen = btn.getAttribute("aria-expanded") === "true";
    setMenu(!isOpen);
  }

  function closeMenu() {
    setMenu(false);
  }

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    toggleMenu();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });
  window.closeMenu = closeMenu;
})();
