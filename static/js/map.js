(function () {
  "use strict";

  var node = document.getElementById("map-data");
  var grid = document.getElementById("tile-map");
  if (!node || !grid) return;

  var data = JSON.parse(node.textContent);
  var districts = data.districts;
  var panel = document.getElementById("map-panel");
  var select = document.getElementById("district-select");
  var readout = document.getElementById("readout");
  var tip = document.getElementById("tip");
  var legendMin = document.getElementById("legend-min");
  var legendMax = document.getElementById("legend-max");
  var legendBar = document.getElementById("legend-bar");
  var approxNote = document.getElementById("approx-note");

  var T = data.text;
  var prefix = data.prefix || "";

  var LAYERS = {
    water: { label: T.water, key: "gw", unit: "%", digits: 0, ramp: ["#2f7f4f", "#d0ae2e", "#d9822b", "#b3321f"] },
    rain: { label: T.rain, key: "rain", unit: T.mm, digits: 0, ramp: ["#35564f", "#2f7f80", "#4fb0c4", "#a6e4f2"] },
    winter: { label: T.winter, key: "t_winter", unit: "°C", digits: 1, ramp: ["#4b523d", "#8f8a3b", "#d0ae2e", "#f7d65f"] },
    summer: { label: T.summer, key: "t_summer", unit: "°C", digits: 1, ramp: ["#5b3b35", "#9a4a38", "#d8653a", "#f7a266"] }
  };

  var layerName = "water";
  var selected = null;
  var cells = {};
  var bySlug = {};

  function hexToRgb(h) {
    return [parseInt(h.substr(1, 2), 16), parseInt(h.substr(3, 2), 16), parseInt(h.substr(5, 2), 16)];
  }

  function colorAt(ramp, t) {
    var n = ramp.length - 1;
    var x = Math.min(Math.max(t, 0), 1) * n;
    var i = Math.min(Math.floor(x), n - 1);
    var f = x - i;
    var a = hexToRgb(ramp[i]);
    var b = hexToRgb(ramp[i + 1]);
    var c = a.map(function (v, k) { return Math.round(v + (b[k] - v) * f); });
    return "rgb(" + c.join(",") + ")";
  }

  function fmt(v, digits) {
    return Number(v).toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }

  // Build a 3D map: one tower per district
  grid.style.setProperty("--cols", data.cols);
  grid.style.setProperty("--rows", data.rows);
  grid.classList.add("iso");
  districts.forEach(function (d, i) {
    bySlug[d.slug] = d;
    var b = document.createElement("div");
    b.className = "iso-cell" + (d.approx_rain ? " approx" : "");
    b.setAttribute("role", "button");
    b.setAttribute("tabindex", "0");
    b.setAttribute("aria-pressed", "false");
    b.dataset.slug = d.slug;
    b.style.setProperty("--x", d.col);
    b.style.setProperty("--y", d.row);
    b.style.setProperty("--i", i);
    b.innerHTML = '<i class="f ft"></i><i class="f ff"></i><i class="f fr"></i>';
    grid.appendChild(b);
    cells[d.slug] = b;
  });

  function applyLayer() {
    var L = LAYERS[layerName];
    var vals = districts.map(function (d) { return d[L.key]; });
    var min = Math.min.apply(null, vals);
    var max = Math.max.apply(null, vals);
    districts.forEach(function (d) {
      var t = max === min ? 0.5 : (d[L.key] - min) / (max - min);
      var el = cells[d.slug];
      el.style.setProperty("--c", colorAt(L.ramp, t));
      el.style.setProperty("--h", Math.round(8 + t * 112) + "px");
      el.setAttribute("aria-label", d.name + ", " + d.state_label + ". " + L.label + " " + fmt(d[L.key], L.digits) + " " + L.unit);
    });
    legendMin.textContent = fmt(min, L.digits) + " " + L.unit;
    legendMax.textContent = fmt(max, L.digits) + " " + L.unit;
    legendBar.style.background = "linear-gradient(90deg," + L.ramp.join(",") + ")";
    panel.classList.remove("layer-rain", "layer-winter", "layer-summer", "layer-water");
    panel.classList.add("layer-" + layerName);
    approxNote.hidden = layerName !== "rain";
  }

  function figure(cls, label, value, digits, unit) {
    return '<div class="' + cls + '"><dt>' + label + '</dt><dd>' + fmt(value, digits) + ' <small>' + unit + '</small></dd></div>';
  }

  function renderReadout(d) {
    var note = T.note;
    if (d.approx_rain) note += " " + T.note_approx;
    readout.innerHTML =
      '<h2 class="readout-name">' + esc(d.name) + '</h2>' +
      '<p class="readout-state">' + esc(d.state_label) + '</p>' +
      '<dl class="figures">' +
      figure("fig-rain", T.rain, d.rain, 0, T.mm) +
      figure("fig-winter", T.winter, d.t_winter, 1, "°C") +
      figure("fig-summer", T.summer, d.t_summer, 1, "°C") +
      (d.gw ? figure("fig-water", T.water, d.gw, 0, "%") : "") +
      '</dl><p class="readout-note">' + esc(note) + '</p>' +
      '<p><a class="btn" href="' + prefix + '/district/' + encodeURIComponent(d.slug) + '">' + esc(T.open.replace("{name}", d.name)) + '</a></p>';
  }

  function choose(slug) {
    if (selected && cells[selected]) cells[selected].setAttribute("aria-pressed", "false");
    if (!slug || !bySlug[slug]) {
      selected = null;
      select.value = "";
      readout.innerHTML = '<p class="readout-empty">' + esc(T.empty) + '</p>';
      return;
    }
    selected = slug;
    cells[slug].setAttribute("aria-pressed", "true");
    select.value = slug;
    renderReadout(bySlug[slug]);
  }

  function showTip(slug) {
    var d = bySlug[slug];
    var L = LAYERS[layerName];
    var r = cells[slug].getBoundingClientRect();
    var p = panel.getBoundingClientRect();
    tip.innerHTML = "<strong>" + esc(d.name) + "</strong><br>" + L.label + " " + fmt(d[L.key], L.digits) + " " + L.unit;
    tip.hidden = false;
    var half = tip.offsetWidth / 2;
    var x = r.left - p.left + r.width / 2;
    x = Math.max(half + 4, Math.min(p.width - half - 4, x));
    tip.style.left = x + "px";
    tip.style.top = (r.top - p.top) + "px";
  }

  function hideTip() { tip.hidden = true; }

  grid.addEventListener("click", function (e) {
    var b = e.target.closest(".iso-cell");
    if (b) choose(b.dataset.slug);
  });
  grid.addEventListener("mouseover", function (e) {
    var b = e.target.closest(".iso-cell");
    if (b) showTip(b.dataset.slug);
  });
  grid.addEventListener("mouseout", hideTip);
  grid.addEventListener("focusin", function (e) {
    var b = e.target.closest(".iso-cell");
    if (b) showTip(b.dataset.slug);
  });
  grid.addEventListener("focusout", hideTip);
  grid.addEventListener("keydown", function (e) {
    var b = e.target.closest(".iso-cell");
    if (b && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); choose(b.dataset.slug); }
  });
  var scene = grid.parentNode;
  if (!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches)) {
    scene.addEventListener("mousemove", function (e) {
      var r = scene.getBoundingClientRect();
      var k = (e.clientX - r.left) / r.width - 0.5;
      grid.style.setProperty("--rz", (-35 + k * 24) + "deg");
    });
    scene.addEventListener("mouseleave", function () { grid.style.setProperty("--rz", "-35deg"); });
  }
  select.addEventListener("change", function () { choose(select.value); });
  Array.prototype.forEach.call(document.querySelectorAll('input[name="layer"]'), function (input) {
    input.addEventListener("change", function () {
      if (input.checked) { layerName = input.value; applyLayer(); }
    });
  });

  applyLayer();
  // rise animation on load: start flat, then grow
  Array.prototype.forEach.call(grid.querySelectorAll(".iso-cell"), function (el) {
    el.dataset.h = el.style.getPropertyValue("--h");
    el.style.setProperty("--h", "0px");
  });
  setTimeout(function () {
    Array.prototype.forEach.call(grid.querySelectorAll(".iso-cell"), function (el) { el.style.setProperty("--h", el.dataset.h); });
  }, 250);
})();
