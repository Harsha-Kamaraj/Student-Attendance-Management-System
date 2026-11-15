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

// Stop a form being sent twice. Some saves (for example a new account whose login details are
// emailed) take a few seconds; a second click used to send the form again and show a confusing
// "already exists" error even though the first save had worked.
(function () {
  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (event.defaultPrevented || !form || (form.method || "").toLowerCase() !== "post") {
      return;
    }
    if (form.dataset.submitting === "1") {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = "1";
    var clicked = event.submitter;
    // Wait until the browser has collected the form data, so the clicked button's value is still sent.
    window.setTimeout(function () {
      var buttons = form.querySelectorAll("button[type=submit], button:not([type]), input[type=submit]");
      Array.prototype.forEach.call(buttons, function (button) {
        if (!button.disabled) {
          button.disabled = true;
          button.dataset.autoDisabled = "1";
        }
      });
      if (clicked && clicked.tagName === "BUTTON") {
        clicked.dataset.originalLabel = clicked.innerHTML;
        clicked.textContent = "Please wait…";
      }
    }, 0);
  });

  // Coming back with the browser's Back button: make the form usable again.
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) {
      return;
    }
    Array.prototype.forEach.call(document.querySelectorAll("form[data-submitting]"), function (form) {
      delete form.dataset.submitting;
      Array.prototype.forEach.call(form.querySelectorAll("[data-auto-disabled]"), function (button) {
        button.disabled = false;
        delete button.dataset.autoDisabled;
        if (button.dataset.originalLabel) {
          button.innerHTML = button.dataset.originalLabel;
          delete button.dataset.originalLabel;
        }
      });
    });
  });
})();
