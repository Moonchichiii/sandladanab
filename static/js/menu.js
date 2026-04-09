(() => {
  const btn = document.getElementById("menu-btn");
  const menu = document.getElementById("mobile-menu");
  const check = document.getElementById("menu-check");

  if (!btn || !menu || !check) return;

  const setMenu = (open) => {
    btn.setAttribute("aria-expanded", String(open));
    menu.setAttribute("aria-hidden", String(!open));

    if (open) {
      menu.removeAttribute("inert");
    } else {
      menu.setAttribute("inert", "");
    }

    check.checked = open;
    document.body.style.overflow = open ? "hidden" : "";
  };

  const close = () => {
    setMenu(false);
    btn.focus();
  };

  btn.addEventListener("click", (e) => {
    e.preventDefault();
    const isOpen = btn.getAttribute("aria-expanded") === "true";
    setMenu(!isOpen);
  });

  menu.addEventListener("click", (e) => {
    if (e.target.closest("a")) close();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") close();
  });

  // Ensure closed on init
  setMenu(false);
})();