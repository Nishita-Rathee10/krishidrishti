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

  var LAYERS = {
    rain: { label: "Yearly rain", key: "rain", unit: "mm", digits: 0, ramp: ["#35564f", "#2f7f80", "#4fb0c4", "#a6e4f2"] },
    winter: { label: "Winter temperature", key: "t_winter", unit: "°C", digits: 1, ramp: ["#4b523d", "#8f8a3b", "#d0ae2e", "#f7d65f"] },
    summer: { label: "Peak summer heat", key: "t_summer", unit: "°C", digits: 1, ramp: ["#5b3b35", "#9a4a38", "#d8653a", "#f7a266"] }
  };

  var layerName = "rain";
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

  // Build the tile map row by row, so keyboard order runs north to south
  grid.style.setProperty("--cols", data.cols);
  var spot = {};
  districts.forEach(function (d) { spot[d.col + "," + d.row] = d; bySlug[d.slug] = d; });
  var counter = 0;
  for (var r = 0; r < data.rows; r++) {
    for (var c = 0; c < data.cols; c++) {
      var d = spot[c + "," + r];
      if (!d) {
        var gap = document.createElement("span");
        gap.className = "void";
        gap.setAttribute("aria-hidden", "true");
        grid.appendChild(gap);
        continue;
      }
      var b = document.createElement("button");
      b.type = "button";
      b.className = "cell" + (d.approx_rain ? " approx" : "");
      b.style.setProperty("--i", counter++);
      b.setAttribute("aria-pressed", "false");
      b.dataset.slug = d.slug;
      b.innerHTML = '<svg viewBox="0 0 10 10" aria-hidden="true" focusable="false"><path d="M1.5 1.5L8.5 8.5M8.5 1.5L1.5 8.5"/></svg>';
      grid.appendChild(b);
      cells[d.slug] = b;
    }
  }

  function applyLayer() {
    var L = LAYERS[layerName];
    var vals = districts.map(function (d) { return d[L.key]; });
    var min = Math.min.apply(null, vals);
    var max = Math.max.apply(null, vals);
    districts.forEach(function (d) {
      var t = max === min ? 0.5 : (d[L.key] - min) / (max - min);
      var el = cells[d.slug];
      el.style.setProperty("--c", colorAt(L.ramp, t));
      el.setAttribute("aria-label", d.name + ", " + d.state + ". " + L.label + " " + fmt(d[L.key], L.digits) + " " + L.unit);
    });
    legendMin.textContent = fmt(min, L.digits) + " " + L.unit;
    legendMax.textContent = fmt(max, L.digits) + " " + L.unit;
    legendBar.style.background = "linear-gradient(90deg," + L.ramp.join(",") + ")";
    panel.classList.remove("layer-rain", "layer-winter", "layer-summer");
    panel.classList.add("layer-" + layerName);
    approxNote.hidden = layerName !== "rain";
  }

  function figure(cls, label, value, digits, unit) {
    return '<div class="' + cls + '"><dt>' + label + '</dt><dd>' + fmt(value, digits) + ' <small>' + unit + '</small></dd></div>';
  }

  function renderReadout(d) {
    var note = "Rain is the average of 1986 to 2015. Temperatures come from a NASA model for 2001 to 2025. Peak summer heat is the highest temperature the model shows in April, May and June, so it reads far higher than a normal day.";
    if (d.approx_rain) note += " Rain for this district is copied from the district it was carved out of.";
    readout.innerHTML =
      '<h2 class="readout-name">' + esc(d.name) + '</h2>' +
      '<p class="readout-state">' + esc(d.state) + '</p>' +
      '<dl class="figures">' +
      figure("fig-rain", "Yearly rain", d.rain, 0, "mm") +
      figure("fig-winter", "Winter temperature", d.t_winter, 1, "°C") +
      figure("fig-summer", "Peak summer heat", d.t_summer, 1, "°C") +
      '</dl><p class="readout-note">' + esc(note) + '</p>' +
      '<p><a class="btn" href="/district/' + encodeURIComponent(d.slug) + '">Open the ' + esc(d.name) + ' page</a></p>';
  }

  function choose(slug) {
    if (selected && cells[selected]) cells[selected].setAttribute("aria-pressed", "false");
    if (!slug || !bySlug[slug]) {
      selected = null;
      select.value = "";
      readout.innerHTML = '<p class="readout-empty">Choose a district from the list, or select a square on the map.</p>';
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
    var b = e.target.closest(".cell");
    if (b) choose(b.dataset.slug);
  });
  grid.addEventListener("mouseover", function (e) {
    var b = e.target.closest(".cell");
    if (b) showTip(b.dataset.slug);
  });
  grid.addEventListener("mouseout", hideTip);
  grid.addEventListener("focusin", function (e) {
    var b = e.target.closest(".cell");
    if (b) showTip(b.dataset.slug);
  });
  grid.addEventListener("focusout", hideTip);
  select.addEventListener("change", function () { choose(select.value); });
  Array.prototype.forEach.call(document.querySelectorAll('input[name="layer"]'), function (input) {
    input.addEventListener("change", function () {
      if (input.checked) { layerName = input.value; applyLayer(); }
    });
  });

  applyLayer();
})();
