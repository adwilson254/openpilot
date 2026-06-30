(function () {
  "use strict";

  const el = (id) => document.getElementById(id);
  const stage = el("stage");

  // --- adaptive scaling: uniformly scale the 2160x1080 design canvas to fit ---
  function fit() {
    const vw = (window.visualViewport && window.visualViewport.width) || window.innerWidth;
    const vh = (window.visualViewport && window.visualViewport.height) || window.innerHeight;
    const s = Math.min(vw / 2160, vh / 1080);
    stage.style.transform = "translate(-50%, -50%) scale(" + s + ")";
  }
  window.addEventListener("resize", fit);
  window.addEventListener("orientationchange", fit);
  if (window.visualViewport) window.visualViewport.addEventListener("resize", fit);
  fit();

  // model/path overlay canvas
  HUDModel.init(el("overlay"));

  const conn = el("conn");
  const src = el("src");

  const MAX_ENGAGED = "#80D8A6";
  const MAX_DIM = "#919B95";
  const MAX_GREY = "#A6A6A6";

  function updateHud(s) {
    el("speedNum").textContent = s.speed != null ? s.speed : 0;
    el("speedUnit").textContent = s.speedUnit || "mph";

    const box = el("setSpeed");
    box.style.display = s.cruiseAvailable ? "flex" : "none";
    el("setVal").textContent = s.cruiseSet ? s.setSpeed : "\u2013";
    el("setMax").style.color = s.cruiseSet ? (s.status === "engaged" ? MAX_ENGAGED : MAX_DIM) : MAX_GREY;
    el("setVal").style.color = s.cruiseSet ? "#fff" : "#727272";

    el("border").style.borderColor = s.borderColor || "#122839";
    el("expbtn").classList.toggle("active", !!s.experimentalMode);

    const a = s.alert;
    const alertEl = el("alert");
    if (a && (a.text1 || a.text2)) {
      el("alertText1").textContent = a.text1 || "";
      el("alertText2").textContent = a.text2 || "";
      alertEl.classList.toggle("crit", a.status === "critical");
      alertEl.classList.remove("hidden");
    } else {
      alertEl.classList.add("hidden");
    }

    el("blinkL").classList.toggle("on", !!s.leftBlinker);
    el("blinkR").classList.toggle("on", !!s.rightBlinker);

    if (s.source) src.textContent = "\u25CF " + s.source;
  }

  // --- websocket with auto-reconnect ---
  let ws = null;
  let reconnectTimer = null;

  function send(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
  }

  function scheduleReconnect() {
    if (reconnectTimer) return;
    reconnectTimer = setTimeout(function () {
      reconnectTimer = null;
      connect();
    }, 1000);
  }

  function connect() {
    ws = new WebSocket("ws://" + location.host + "/ws/state");
    ws.onopen = function () {
      conn.textContent = "connected";
      conn.className = "ok";
      send({ type: "getParams" });
    };
    ws.onclose = function () {
      conn.textContent = "disconnected";
      conn.className = "bad";
      scheduleReconnect();
    };
    ws.onerror = function () {
      try { ws.close(); } catch (e) {}
    };
    ws.onmessage = function (ev) {
      let m;
      try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (m.type === "state") updateHud(m);
      else if (m.type === "model") HUDModel.onModel(m);
      else if (m.type === "params") renderParams(m.items);
      else if (m.type === "param") updateParam(m.key, m.value);
    };
  }
  connect();

  // --- experimental-mode toggle via the wheel button ---
  el("expbtn").addEventListener("click", function () {
    const next = !el("expbtn").classList.contains("active");
    send({ type: "setParam", key: "ExperimentalMode", value: next });
  });

  // --- settings (touch param control) ---
  const settings = el("settings");
  el("gear").addEventListener("click", function () {
    settings.classList.remove("hidden");
    send({ type: "getParams" });
  });
  el("closeSettings").addEventListener("click", function () {
    settings.classList.add("hidden");
  });

  const paramToggles = {};
  function renderParams(items) {
    const list = el("paramList");
    list.innerHTML = "";
    for (const k in paramToggles) delete paramToggles[k];
    (items || []).forEach(function (it) {
      const row = document.createElement("div");
      row.className = "param-row";
      const label = document.createElement("div");
      label.className = "label";
      label.textContent = it.label || it.key;
      const tog = document.createElement("div");
      tog.className = "toggle" + (it.value ? " on" : "");
      const knob = document.createElement("div");
      knob.className = "knob";
      tog.appendChild(knob);
      tog.addEventListener("click", function () {
        send({ type: "setParam", key: it.key, value: !tog.classList.contains("on") });
      });
      paramToggles[it.key] = tog;
      row.appendChild(label);
      row.appendChild(tog);
      list.appendChild(row);
    });
  }
  function updateParam(key, value) {
    const tog = paramToggles[key];
    if (tog) tog.classList.toggle("on", !!value);
  }
})();
