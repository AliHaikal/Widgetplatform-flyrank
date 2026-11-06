/* Embeddable widget, bundle v2.
 * Usage on any site:  <script src="https://API/widget.v2.js?id=WIDGET_ID"></script>
 * Flow: read ?id= -> GET /widgets/:id/config -> render -> POST /submissions
 */
(function () {
  "use strict";

  var script = document.currentScript;
  if (!script) return;
  var src = new URL(script.src);
  var widgetId = src.searchParams.get("id");
  var base = src.origin;
  if (!widgetId) {
    console.error("[widget] missing ?id= in the script URL");
    return;
  }

  var host = document.createElement("div");
  script.parentNode.insertBefore(host, script);
  var root = host.attachShadow ? host.attachShadow({ mode: "open" }) : host;

  fetch(base + "/widgets/" + encodeURIComponent(widgetId) + "/config")
    .then(function (r) {
      if (!r.ok) throw new Error("config " + r.status);
      return r.json();
    })
    .then(render)
    .catch(function (err) {
      console.error("[widget] failed to load:", err);
    });

  // One key per submission attempt. It is kept across failed tries so a retry
  // is recognised by the server as the same request, and renewed after success.
  function newKey() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "k" + Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
  }

  function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      node[k] = props[k];
    });
    (children || []).forEach(function (c) {
      node.appendChild(c);
    });
    return node;
  }

  var STYLE =
    ":host{all:initial}" +
    "*{box-sizing:border-box;font-family:system-ui,sans-serif}" +
    "form,.panel{background:#fff;color:#111;border:1px solid #ddd;border-radius:8px;padding:16px;max-width:340px}" +
    "h3{margin:0 0 6px;font-size:18px}p{margin:0 0 10px;font-size:14px;color:#444}" +
    "label{display:block;font-size:13px;margin-bottom:10px}" +
    "input,textarea{display:block;width:100%;margin-top:4px;padding:8px;border:1px solid #bbb;border-radius:4px;font-size:14px}" +
    "button{padding:9px 14px;border:0;border-radius:4px;background:#111;color:#fff;font-size:14px;cursor:pointer}" +
    "button:disabled{opacity:.6;cursor:default}" +
    ".msg{margin-top:10px;font-size:13px}.ok{color:#0a6b2b}.err{color:#b00020}" +
    ".hp{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}" +
    ".trigger{position:fixed;bottom:20px;z-index:2147483000;box-shadow:0 2px 8px rgba(0,0,0,.25)}" +
    ".panel{position:fixed;bottom:70px;z-index:2147483000;box-shadow:0 4px 18px rgba(0,0,0,.3)}" +
    ".left{left:20px}.right{right:20px}";

  function render(cfg) {
    root.appendChild(el("style", { textContent: STYLE }));
    var opts = cfg.display_options || {};
    var key = newKey();
    var inputs = {};

    var form = el("form", { noValidate: false }, [el("h3", { textContent: cfg.title })]);
    if (cfg.description) form.appendChild(el("p", { textContent: cfg.description }));

    cfg.fields.forEach(function (f) {
      var input =
        f.type === "textarea"
          ? el("textarea", { rows: 3 })
          : el("input", { type: f.type === "number" ? "number" : f.type || "text" });
      input.name = f.name;
      input.required = !!f.required;
      inputs[f.name] = input;
      form.appendChild(el("label", { textContent: f.label }, [input]));
    });

    // Honeypot: invisible to people, tempting to bots.
    var hp = el("input", { name: "honeypot", tabIndex: -1, autocomplete: "off", className: "hp" });
    form.appendChild(hp);

    var button = el("button", { type: "submit", textContent: cfg.button_text || "Submit" });
    var msg = el("div", { className: "msg", role: "status" });
    form.appendChild(button);
    form.appendChild(msg);

    function say(text, ok) {
      msg.textContent = text;
      msg.className = "msg " + (ok ? "ok" : "err");
    }

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (button.disabled) return; // double-click guard
      var data = {};
      cfg.fields.forEach(function (f) {
        data[f.name] = inputs[f.name].value;
      });
      button.disabled = true;
      say("Sending...", true);

      fetch(base + "/submissions?widget_id=" + encodeURIComponent(widgetId), {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": key },
        body: JSON.stringify({ data: data, honeypot: hp.value }),
      })
        .then(function (r) {
          if (r.ok) {
            say(opts.success_message || "Thanks, submitted!", true);
            form.reset();
            key = newKey();
            if (panel) setTimeout(function () { panel.style.display = "none"; }, 1500);
            return;
          }
          if (r.status === 429) {
            var wait = r.headers.get("Retry-After");
            say("Too many attempts. Try again" + (wait ? " in " + wait + "s." : " shortly."), false);
            return;
          }
          return r.json().then(
            function (body) {
              var first = body.errors && body.errors[0];
              say(first ? (first.field ? first.field + ": " : "") + first.msg : body.detail || "Error " + r.status, false);
            },
            function () { say("Error " + r.status, false); }
          );
        })
        .catch(function () {
          say("Network error. Please try again.", false);
        })
        .then(function () {
          button.disabled = false;
        });
    });

    var panel = null;
    if (cfg.type === "cta_popover") {
      var side = opts.position === "bottom-left" ? "left" : "right";
      panel = el("div", { className: "panel " + side }, [form]);
      panel.style.display = "none";
      var trigger = el("button", {
        type: "button",
        className: "trigger " + side,
        textContent: opts.trigger_label || "Sign up",
      });
      trigger.style.display = "none";
      trigger.addEventListener("click", function () {
        panel.style.display = panel.style.display === "none" ? "block" : "none";
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") panel.style.display = "none";
      });
      root.appendChild(panel);
      root.appendChild(trigger);
      setTimeout(function () {
        trigger.style.display = "block";
      }, (opts.delay_seconds || 0) * 1000);
    } else {
      root.appendChild(form);
    }
  }
})();
