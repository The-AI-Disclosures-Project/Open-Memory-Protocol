(function () {
  var toc = document.querySelector(".toc");
  var here = toc.querySelector(".toc-here");
  var wide = window.matchMedia("(min-width: 62rem)");
  function fit() {
    if (wide.matches) toc.setAttribute("open", "");
    else toc.removeAttribute("open");
  }
  fit();
  wide.addEventListener("change", fit);

  // Close the contents after picking a section on small screens.
  toc.addEventListener("click", function (e) {
    if (e.target.closest("a") && !wide.matches) toc.removeAttribute("open");
  });

  // Mark the section being read, in the sidebar and in the mobile bar.
  var links = {};
  toc.querySelectorAll("nav a[href^='#']").forEach(function (a) {
    links[decodeURIComponent(a.getAttribute("href").slice(1))] = a;
  });
  var heads = Array.prototype.filter.call(
    document.querySelectorAll(".doc h2[id], .doc h3[id]"),
    function (h) { return links[h.id]; }
  );
  function label(a) {
    var copy = a.cloneNode(true);
    copy.querySelectorAll(".st").forEach(function (s) { s.remove(); });
    return copy.textContent.trim();
  }
  var current = null;
  function update() {
    var line = wide.matches ? 120 : 90;
    var found = null;
    for (var i = 0; i < heads.length; i++) {
      if (heads[i].getBoundingClientRect().top <= line) found = heads[i];
      else break;
    }
    var a = found ? links[found.id] : null;
    if (a === current) return;
    if (current) current.removeAttribute("aria-current");
    if (a) a.setAttribute("aria-current", "true");
    if (here) here.textContent = a ? label(a) : "";
    current = a;
  }
  var queued = false;
  window.addEventListener("scroll", function () {
    if (queued) return;
    queued = true;
    requestAnimationFrame(function () { queued = false; update(); });
  }, { passive: true });
  window.addEventListener("resize", update);
  update();

  // On small screens, open the list at the section being read.
  var body = toc.querySelector(".toc-body");
  toc.addEventListener("toggle", function () {
    if (!toc.open || wide.matches || !body) return;
    update();
    if (!current) return;
    body.scrollTop = current.offsetTop - body.offsetTop - body.clientHeight / 3;
  });
})();
