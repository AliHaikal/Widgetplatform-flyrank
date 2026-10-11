(function () {
  var script = document.currentScript;
  var src = new URL(script.src);
  var widgetId = src.searchParams.get("id");
  var base = src.origin;

  var mount = document.createElement("div");
  script.parentNode.insertBefore(mount, script);

  fetch(base + "/widgets/" + widgetId + "/config")
    .then(function (r) {
      if (!r.ok) throw new Error("config " + r.status);
      return r.json();
    })
    .then(render)
    .catch(function (err) {
      console.error("Widget failed to load:", err);
    });

  function render(cfg) {
    var form = document.createElement("form");

    var h = document.createElement("h3");
    h.textContent = cfg.title;
    form.appendChild(h);

    if (cfg.description) {
      var p = document.createElement("p");
      p.textContent = cfg.description;
      form.appendChild(p);
    }

    cfg.fields.forEach(function (f) {
      var label = document.createElement("label");
      label.textContent = f.label + " ";
      var input = document.createElement("input");
      input.name = f.name;
      input.type = f.type || "text";
      input.required = !!f.required;
      label.appendChild(input);
      form.appendChild(label);
      form.appendChild(document.createElement("br"));
    });

    // honeypot: hidden from humans, bots fill it
    var hp = document.createElement("input");
    hp.name = "honeypot";
    hp.tabIndex = -1;
    hp.autocomplete = "off";
    hp.style.cssText = "position:absolute;left:-9999px;";
    form.appendChild(hp);

    var btn = document.createElement("button");
    btn.type = "submit";
    btn.textContent = cfg.button_text || "Submit";
    form.appendChild(btn);

    var msg = document.createElement("p");
    form.appendChild(msg);

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var data = {};
      cfg.fields.forEach(function (f) {
        data[f.name] = form.elements[f.name].value;
      });
      fetch(base + "/submissions?widget_id=" + widgetId, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: data, honeypot: hp.value }),
      })
        .then(function (r) {
          msg.textContent = r.ok ? "Thanks, submitted!" : "Error " + r.status;
        })
        .catch(function () {
          msg.textContent = "Network error";
        });
    });

    mount.appendChild(form);
  }
})();