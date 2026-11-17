(function () {
  "use strict";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  function build(root) {
    var node = root.querySelector("script");
    if (!node) return;
    var cfg = JSON.parse(node.textContent);
    var items = cfg.items || [];
    if (!items.length) return;
    var n = 0;
    items.forEach(function (it, i) { if (it.x === undefined) it.x = i; n = Math.max(n, it.x + 1); });
    var max = cfg.max || Math.max.apply(null, items.map(function (it) { return it.v; })) || 1;

    var scene = document.createElement("div");
    scene.className = "t3-scene";
    var plane = document.createElement("div");
    plane.className = "t3-plane";
    scene.appendChild(plane);
    var tip = document.createElement("div");
    tip.className = "t3-tip";
    tip.hidden = true;
    var keyEl = root.querySelector(".t3-key");
    if (keyEl) root.insertBefore(scene, keyEl); else root.appendChild(scene);
    root.appendChild(tip);

    var cells = [];
    items.forEach(function (it, i) {
      var c = document.createElement("div");
      c.className = "t3-cell" + (it.dim ? " dim" : "") + (it.on ? " on" : "") + (it.hide ? " hide" : "");
      c.setAttribute("tabindex", "0");
      c.setAttribute("role", "img");
      c.setAttribute("aria-label", it.tip || it.l || "");
      c.style.setProperty("--x", it.x);
      c.style.setProperty("--i", i);
      c.style.setProperty("--c", it.c || "#5cc08a");
      c.dataset.k = i;
      c.innerHTML = '<i class="t3f t3t"></i><i class="t3f t3a"></i><i class="t3f t3r"></i>' +
        (it.val ? '<span class="t3-val">' + esc(it.val) + '</span>' : "") +
        (it.l ? '<span class="t3-lab">' + esc(it.l) + '</span>' : "");
      plane.appendChild(c);
      cells.push(c);
    });

    function size() {
      var w = root.clientWidth || 600;
      var S = Math.max(14, Math.min(cfg.maxS || 48, Math.floor(w * 0.66 / (0.9 * n + 0.8))));
      var H = Math.round(Math.min(cfg.maxH || 200, Math.max(110, w * 0.3)));
      plane.style.setProperty("--s", S + "px");
      plane.style.width = n * S + "px";
      plane.style.height = S + "px";
      scene.style.height = Math.round(H + S * 3.4 + 70) + "px";
      cells.forEach(function (c, i) {
        var it = items[i];
        c.style.setProperty("--h", c.classList.contains("up") ? Math.max(6, Math.round(it.v / max * H)) + "px" : "0px");
        c.dataset.hh = Math.max(6, Math.round(it.v / max * H));
      });
    }

    function grow() {
      cells.forEach(function (c) { c.classList.add("up"); c.style.setProperty("--h", c.dataset.hh + "px"); });
    }

    size();
    var shown = false;
    function start() { if (shown) return; shown = true; setTimeout(grow, reduce ? 0 : 150); }
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es, ob) { if (es[0].isIntersecting) { start(); ob.disconnect(); } }, { threshold: 0.2 }).observe(root);
    } else { start(); }
    window.addEventListener("resize", function () { size(); if (shown) grow(); });

    function show(c) {
      var it = items[+c.dataset.k];
      if (!it.tip) return;
      var r = c.getBoundingClientRect(), p = root.getBoundingClientRect();
      tip.textContent = it.tip;
      tip.hidden = false;
      var half = tip.offsetWidth / 2;
      var x = r.left - p.left + r.width / 2;
      tip.style.left = Math.max(half + 4, Math.min(p.width - half - 4, x)) + "px";
      tip.style.top = Math.max(4, r.top - p.top - 8) + "px";
    }
    plane.addEventListener("mouseover", function (e) { var c = e.target.closest(".t3-cell"); if (c) show(c); });
    plane.addEventListener("mouseout", function () { tip.hidden = true; });
    plane.addEventListener("focusin", function (e) { var c = e.target.closest(".t3-cell"); if (c) show(c); });
    plane.addEventListener("focusout", function () { tip.hidden = true; });
    if (!reduce) {
      root.addEventListener("mousemove", function (e) {
        var r = root.getBoundingClientRect();
        plane.style.setProperty("--rz", (-25 + ((e.clientX - r.left) / r.width - 0.5) * 20) + "deg");
      });
      root.addEventListener("mouseleave", function () { plane.style.setProperty("--rz", "-25deg"); });
    }
  }

  Array.prototype.forEach.call(document.querySelectorAll(".t3"), build);
})();
