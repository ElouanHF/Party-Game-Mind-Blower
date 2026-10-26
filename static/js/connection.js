/* Shared helpers: the socket connection, storage, small DOM helpers.
   Everything hangs off one global, MB. */
(function () {
  const MB = (window.MB = window.MB || {});
  const params = new URLSearchParams(location.search);

  // The dev page opens several phones in one browser; ?slot=N keeps their storage apart.
  MB.slot = params.get("slot") || "";

  MB.store = {
    get(key) { try { return localStorage.getItem(key + MB.slot); } catch (e) { return null; } },
    set(key, value) { try { localStorage.setItem(key + MB.slot, value); } catch (e) { /* private mode */ } },
    del(key) { try { localStorage.removeItem(key + MB.slot); } catch (e) { /* ignore */ } },
  };

  MB.esc = (text) => String(text ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  MB.$ = (sel, root = document) => root.querySelector(sel);
  MB.$$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /** Build an element from an HTML string. */
  MB.html = (markup) => {
    const t = document.createElement("template");
    t.innerHTML = markup.trim();
    return t.content.firstElementChild;
  };

  /** Question text with the name dropped in and highlighted. */
  MB.question = (template, name) => {
    const [before, after] = String(template).split("{player}");
    return `${MB.esc(before)}<span class="name-hl">${MB.esc(name)}</span>${MB.esc(after ?? "")}`;
  };

  MB.burstSvg = (fill) =>
    `<svg viewBox="0 0 100 100" aria-hidden="true"><path fill="${fill}" d="M50 2 L58 30 L84 14 L70 40 L98 50 L70 60 L84 86 L58 70 L50 98 L42 70 L16 86 L30 60 L2 50 L30 40 L16 14 L42 30Z"/></svg>`;

  MB.logo = () =>
    `<span class="logo"><span class="burst">${MB.burstSvg("#FFD9BD")}</span><span class="word">Mind <b>Blower</b></span></span>`;

  MB.face = (person, extraClass = "") =>
    `<span class="ring ${extraClass}"><img src="${MB.esc(person.selfie)}" alt="${MB.esc(person.name)}"></span>`;

  // ---------------------------------------------------------------- toast & offline

  let toastTimer = null;
  MB.toast = (message) => {
    let el = MB.$(".toast");
    if (!el) { el = MB.html('<div class="toast" role="status"></div>'); document.body.appendChild(el); }
    el.textContent = message;
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 3200);
  };

  function setOffline(show) {
    let el = MB.$(".offline");
    if (!el) {
      el = MB.html('<div class="offline"><div>Reconnecting<span class="dots"></span><br><small class="muted">Make sure you are on the party Wi-Fi.</small></div></div>');
      document.body.appendChild(el);
    }
    el.classList.toggle("show", show);
  }

  // ---------------------------------------------------------------- server time

  MB.clockOffset = 0;
  MB.serverNow = () => Date.now() + MB.clockOffset;
  MB.secondsLeft = (deadlineMs) => Math.max(0, Math.ceil((deadlineMs - MB.serverNow()) / 1000));

  // ---------------------------------------------------------------- socket

  /**
   * Connect and say hello. onView gets every view; onFx gets each fx cue.
   * role: "phone" or "tv".
   */
  MB.connect = ({ role, onView, onFx }) => {
    const socket = io({ transports: ["websocket", "polling"] });
    MB.socket = socket;
    let offlineTimer = null;

    MB.hello = () => socket.emit("hello", { role, player_id: MB.store.get("mb_player") });
    MB.send = (event, data = {}) => socket.emit(event, data);

    socket.on("connect", () => { clearTimeout(offlineTimer); setOffline(false); MB.hello(); });
    socket.on("disconnect", () => { offlineTimer = setTimeout(() => setOffline(true), 1500); });
    socket.on("view", (view) => {
      MB.clockOffset = view.now - Date.now();
      onView(view);
    });
    socket.on("fx", (list) => { if (onFx) list.forEach(onFx); });
    socket.on("oops", (data) => MB.toast(data.message));
    // The server didn't recognise our saved player id (for example it was restarted).
    socket.on("forget", () => MB.store.del("mb_player"));
  };
})();
