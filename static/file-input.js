document.addEventListener("DOMContentLoaded", () => {
  document
    .querySelectorAll('.file-wrap input[type="file"]')
    .forEach((input) => {
      const nameEl = input.closest(".file-wrap")?.querySelector(".file-name");
      const update = () => {
        const f = input.files && input.files[0];
        nameEl && (nameEl.textContent = f ? f.name : "Ingen fil vald");
      };
      input.addEventListener("change", update);
      update();
    });
});
