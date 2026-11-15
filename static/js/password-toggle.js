// Add an eye button to every password box so people can check what they typed.
// The password is shown only while the user asks for it, and is hidden again before the form is sent.
(function () {
  var EYE =
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>';
  var EYE_OFF =
    '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false" fill="none" ' +
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
    '<path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.4 0 10 7 10 7a17.6 17.6 0 0 1-3.2 4.2"/>' +
    '<path d="M6.6 6.6A17.6 17.6 0 0 0 2 12s3.6 7 10 7a9.5 9.5 0 0 0 5.4-1.6"/>' +
    '<path d="M14.1 14.1a3 3 0 1 1-4.2-4.2"/><path d="M2 2l20 20"/></svg>';

  function setVisible(input, button, visible) {
    input.type = visible ? "text" : "password";
    button.innerHTML = visible ? EYE_OFF : EYE;
    button.setAttribute("aria-pressed", visible ? "true" : "false");
    button.setAttribute("aria-label", visible ? "Hide password" : "Show password");
    button.title = visible ? "Hide password" : "Show password";
  }

  function addToggle(input) {
    if (input.dataset.passwordToggle) {
      return;
    }
    input.dataset.passwordToggle = "1";
    var wrapper = document.createElement("div");
    wrapper.className = "password-field";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    var button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle";
    if (input.id) {
      button.setAttribute("aria-controls", input.id);
    }
    setVisible(input, button, false);
    wrapper.appendChild(button);

    button.addEventListener("click", function () {
      setVisible(input, button, input.type === "password");
      input.focus();
    });
    if (input.form) {
      input.form.addEventListener("submit", function () {
        setVisible(input, button, false);
      });
    }
  }

  Array.prototype.forEach.call(document.querySelectorAll('input[type="password"]'), addToggle);
})();
