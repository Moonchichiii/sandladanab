(function () {
  var wraps = document.querySelectorAll(".file-wrap");
  if (!wraps.length) return;

  wraps.forEach(function (wrap) {
    var input = wrap.querySelector('input[type="file"]');
    var nameEl = wrap.querySelector(".file-name");
    if (!input || !nameEl) return;

    nameEl.setAttribute("aria-live", "polite");

    var update = function () {
      var files = input.files;
      var text = "Ingen fil vald";
      if (files && files.length) {
        text = files.length > 1 ? files.length + " filer valda" : files[0].name;
      }
      nameEl.textContent = text;
    };

    input.addEventListener("change", update);

    if (input.form) {
      input.form.addEventListener("reset", function () {
        setTimeout(update, 0);
      });
    }

    update();
  });
})();
