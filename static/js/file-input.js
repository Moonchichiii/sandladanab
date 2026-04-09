(() => {
  const wraps = document.querySelectorAll(".file-wrap");
  if (!wraps.length) return;

  wraps.forEach((wrap) => {
    const input = wrap.querySelector('input[type="file"]');
    const nameEl = wrap.querySelector(".file-name");
    if (!input || !nameEl) return;

    nameEl.setAttribute("aria-live", "polite");

    const update = () => {
      const { files } = input;
      nameEl.textContent =
        files && files.length
          ? files.length > 1
            ? `${files.length} filer valda`
            : files[0].name
          : "Ingen fil vald";
    };

    input.addEventListener("change", update);

    if (input.form) {
      input.form.addEventListener("reset", () => setTimeout(update, 0));
    }

    update();
  });
})();