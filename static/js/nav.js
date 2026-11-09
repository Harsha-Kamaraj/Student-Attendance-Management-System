// Open and close the sidebar on narrow screens. On wide screens it is always shown by CSS.
(function () {
  var toggle = document.querySelector("[data-sidebar-toggle]");
  var backdrop = document.querySelector("[data-sidebar-close]");
  if (!toggle) {
    return;
  }

  function setOpen(open) {
    document.body.classList.toggle("sidebar-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (backdrop) {
      backdrop.hidden = !open;
    }
  }

  toggle.addEventListener("click", function () {
    setOpen(!document.body.classList.contains("sidebar-open"));
  });
  if (backdrop) {
    backdrop.addEventListener("click", function () {
      setOpen(false);
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && document.body.classList.contains("sidebar-open")) {
      setOpen(false);
      toggle.focus();
    }
  });
})();
