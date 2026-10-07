// OpenRouter Weekly: week picker, full-size chart viewer, copy-link buttons.
(function () {
  "use strict";

  // Week picker: jump to the chosen week's page
  var select = document.getElementById("week-select");
  if (select) {
    select.addEventListener("change", function () {
      window.location.href = select.value;
    });
  }

  // Full-size viewer with previous / next and keyboard support
  var box = document.getElementById("lightbox");
  var img = document.getElementById("lb-img");
  var caption = document.getElementById("lb-caption");
  var items = Array.prototype.slice.call(document.querySelectorAll("[data-full]"));
  var current = 0;
  var opener = null;

  function show(i) {
    current = (i + items.length) % items.length;
    var item = items[current];
    img.src = item.getAttribute("data-full");
    img.alt = item.getAttribute("data-title");
    caption.textContent = item.getAttribute("data-title");
  }
  function open(i, trigger) {
    opener = trigger;
    show(i);
    box.hidden = false;
    document.body.style.overflow = "hidden";
    box.querySelector(".lb-close").focus();
  }
  function close() {
    box.hidden = true;
    document.body.style.overflow = "";
    if (opener) { opener.focus(); }
  }
  items.forEach(function (item, i) {
    item.addEventListener("click", function () { open(i, item); });
  });
  if (box) {
    box.querySelector(".lb-close").addEventListener("click", close);
    box.querySelector(".lb-prev").addEventListener("click", function () { show(current - 1); });
    box.querySelector(".lb-next").addEventListener("click", function () { show(current + 1); });
    box.addEventListener("click", function (e) { if (e.target === box) { close(); } });
    document.addEventListener("keydown", function (e) {
      if (box.hidden) { return; }
      if (e.key === "Escape") { close(); }
      if (e.key === "ArrowLeft") { show(current - 1); }
      if (e.key === "ArrowRight") { show(current + 1); }
    });
  }

  // Copy a link straight to one chart
  document.querySelectorAll("[data-copy]").forEach(function (button) {
    button.addEventListener("click", function () {
      var url = new URL(button.getAttribute("data-copy"), window.location.href).href;
      var done = function () {
        var label = button.textContent;
        button.textContent = "Link copied";
        button.classList.add("copied");
        setTimeout(function () { button.textContent = label; button.classList.remove("copied"); }, 1600);
      };
      if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(done, function () { window.prompt("Copy this link:", url); });
      } else {
        window.prompt("Copy this link:", url);
      }
    });
  });
})();
