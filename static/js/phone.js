/* The phone page. Draws whatever screen the latest view asks for.

   Each screen has mount(view) -> element, and optionally update(view, element).
   A screen is re-mounted only when its key changes (for example a new question),
   so typing in the answer box is never wiped by an unrelated update. */
(function () {
  const { $, $$, esc, html, Sound, Motion } = MB;
  Sound.setVolume(0.45); // phones stay quieter than the TV

  const app = {
    view: null,
    key: null,
    busy: false,
    draft: { name: MB.store.get("mb_name") || "", blob: null, url: null },
  };
  const devFrame = MB.slot !== "";
  const hostKey = readHostKey();

  function readHostKey() {
    const params = new URLSearchParams(location.search);
    const key = params.get("host");
    if (key) {
      MB.store.set("mb_host_key", key);
      params.delete("host");
      const rest = params.toString();
      history.replaceState(null, "", location.pathname + (rest ? `?${rest}` : ""));
    }
    return MB.store.get("mb_host_key");
  }

  const dots = (on, max, cls = "") =>
    Array.from({ length: max }, (_, i) => `<i class="dot ${cls} ${i < on ? "on" : ""}"></i>`).join("");

  const MARK_COLOURS = { correct: "#2FBF71", partly: "#FFB020", wrong: "#F2545B", mind_blown: "#8B5CF6" };

  /** Guard against double taps; frees itself if the server doesn't move us on. */
  function once(fn) {
    if (app.busy) return;
    app.busy = true;
    const key = app.key;
    fn();
    setTimeout(() => { if (app.key === key) app.busy = false; }, 2000);
  }

  // ---------------------------------------------------------------- help sheet

  const HELP = {
    lobby: ["Getting started", [
      "Wait for everyone to join. Your face is now on the TV.",
      "The host starts the game when the room is ready.",
      "Keep this page open. If it closes, just open the same link again and you'll be right back.",
    ]],
    party: ["How to play: party time", [
      "Pick a category. Harder ones are worth more points.",
      "Find the person on your card. Their face is on your screen.",
      "Chat with them and find out the answer.",
      "Type what you found out and submit, then pick your next one.",
      "Skips: you hold up to 3, and get 1 back for every answer.",
    ]],
    grace: ["Time's nearly up!", [
      "Finish and submit the question you're holding.",
      "Skipping is switched off now.",
      "When the timer ends, everyone moves on to marking.",
    ]],
    review: ["How to play: marking", [
      "These are answers other people wrote about you. You won't see who wrote them.",
      "Mark each one Correct, Partly right or Wrong.",
      "Mind blown is for outstanding answers. It doubles their points, and you get 1 bonus point for each one you give. You have 3.",
      "Made a mis-tap? Use Undo.",
    ]],
    ending: ["The big finish", [
      "Watch the TV for highlights, awards and the podium.",
      "Your own results appear here at the very end.",
    ]],
  };

  function helpKeyFor(phase) {
    if (phase === "highlights" || phase === "results") return "ending";
    return HELP[phase] ? phase : "lobby";
  }

  function openHelp(phase) {
    const [title, steps] = HELP[helpKeyFor(phase)];
    const wrap = $("#help");
    wrap.innerHTML = `<div class="sheet" role="dialog" aria-label="${esc(title)}">
      <div class="grab"></div><h2>${esc(title)}</h2>
      ${steps.map((s, i) => `<div class="step"><div class="n">${i + 1}</div><div>${esc(s)}</div></div>`).join("")}
      <div class="switch-row"><span>Sound</span><button class="switch ${Sound.isMuted() ? "" : "on"}" aria-label="Sound on or off"></button></div>
      <button class="btn got-it">Got it</button></div>`;
    wrap.classList.add("show");
    $(".switch", wrap).onclick = (e) => {
      Sound.setMuted(!Sound.isMuted());
      e.currentTarget.classList.toggle("on", !Sound.isMuted());
      Sound.play("click");
    };
    $(".got-it", wrap).onclick = closeHelp;
    wrap.onclick = (e) => { if (e.target === wrap) closeHelp(); };
  }
  function closeHelp() { $("#help").classList.remove("show"); Sound.play("click"); }

  // ---------------------------------------------------------------- top bar & host controls

  function renderBar(v) {
    const bar = $("#bar");
    if (!v.me) { bar.hidden = true; return; }
    bar.hidden = false;
    let middle = "";
    if (v.phase === "party" || v.phase === "grace") {
      middle = `<span>Skips<span class="dots">${dots(v.me.skips, v.me.max_skips)}</span></span>`;
    } else if (v.phase === "review" && v.mind_blowns_max) {
      middle = `<span>Mind blowns<span class="dots">${dots(v.mind_blowns_left, v.mind_blowns_max, "mind")}</span></span>`;
    }
    bar.innerHTML = `<span>Answers<span class="count">${v.me.count}</span></span>
      <span class="right">${middle}<button class="help-btn" aria-label="How to play">?</button></span>`;
    $(".help-btn", bar).onclick = () => { Sound.play("click"); openHelp(v.phase); };
  }

  const CONFIRM = {
    end: "End the party for everyone? Anyone holding a question gets 30 seconds to finish.",
    new_game: "Start a new game? Everyone will need to join again.",
  };

  function renderHost(v) {
    const el = $("#host");
    const buttons = v.host_controls || [];
    if (!buttons.length) { el.innerHTML = ""; return; }
    el.innerHTML = `<div class="lbl">Host controls</div>` + buttons.map((b) =>
      `<button class="btn ${b.action === "end" ? "ghost" : ""} ${b.enabled ? "pulse" : ""}"
         data-action="${b.action}" ${b.enabled ? "" : "disabled"}>${esc(b.label)}</button>`).join("");
    $$("button", el).forEach((btn) => {
      btn.onclick = () => {
        const action = btn.dataset.action;
        Sound.play("click");
        if (CONFIRM[action] && !confirm(CONFIRM[action])) return;
        MB.send("host", { action });
      };
    });
  }

  // ---------------------------------------------------------------- grace timer

  const RING = 2 * Math.PI * 27;

  function graceBanner(deadline, line, calm = false) {
    return `<div class="grace ${calm ? "calm" : ""}" data-deadline="${deadline}">
      <div class="timer"><svg viewBox="0 0 64 64"><circle cx="32" cy="32" r="27" fill="#fff" stroke="#F8C9C6" stroke-width="7"/>
        <circle class="arc" cx="32" cy="32" r="27" fill="none" stroke="#F2545B" stroke-width="7" stroke-linecap="round" stroke-dasharray="${RING}"/></svg>
        <div class="secs"></div></div>
      <div><div class="t1">${calm ? "Marking soon" : "Time's nearly up!"}</div><div class="muted">${esc(line)}</div></div></div>`;
  }

  let lastTick = null;
  setInterval(() => {
    $$("[data-deadline]").forEach((el) => {
      const deadline = Number(el.dataset.deadline);
      const left = MB.secondsLeft(deadline);
      const total = 30;
      $(".secs", el).textContent = left;
      $(".arc", el).style.strokeDashoffset = RING * (1 - Math.min(1, left / total));
      $(".timer", el).classList.toggle("hurry", left <= 10);
      if (left <= 10 && left > 0 && left !== lastTick) { lastTick = left; Sound.play("tick"); }
    });
  }, 200);

  // ---------------------------------------------------------------- selfies

  const SELFIE_SIZE = 400;

  function toSelfie(file) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        const side = Math.min(img.naturalWidth, img.naturalHeight);
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = SELFIE_SIZE;
        canvas.getContext("2d").drawImage(img, (img.naturalWidth - side) / 2, (img.naturalHeight - side) / 2,
          side, side, 0, 0, SELFIE_SIZE, SELFIE_SIZE);
        URL.revokeObjectURL(url);
        canvas.toBlob((blob) => (blob ? resolve(blob) : reject()), "image/jpeg", 0.85);
      };
      img.onerror = () => { URL.revokeObjectURL(url); reject(); };
      img.src = url;
    });
  }

  /** For testing in the dev page, where there's no camera. */
  function cartoonSelfie() {
    const c = document.createElement("canvas");
    c.width = c.height = SELFIE_SIZE;
    const g = c.getContext("2d");
    const pick = (list) => list[Math.floor(Math.random() * list.length)];
    g.fillStyle = pick(["#FFD9BD", "#FFE7A8", "#FFC9B0", "#FBE3B8"]); g.fillRect(0, 0, 400, 400);
    g.fillStyle = pick(["#FF8A3D", "#8B5CF6", "#2FBF71", "#4A90E2"]); g.beginPath(); g.ellipse(200, 420, 120, 90, 0, 0, 7); g.fill();
    g.fillStyle = pick(["#F6D2B5", "#E8B58F", "#C98B61", "#9C6440"]); g.beginPath(); g.ellipse(200, 190, 95, 105, 0, 0, 7); g.fill();
    g.fillStyle = pick(["#3B2416", "#8A4B22", "#D9A441", "#1E1410"]); g.beginPath(); g.ellipse(200, 120, 100, 60, 0, Math.PI, 2 * Math.PI); g.fill();
    g.fillStyle = "#3A2418"; [160, 240].forEach((x) => { g.beginPath(); g.arc(x, 200, 11, 0, 7); g.fill(); });
    g.strokeStyle = "#3A2418"; g.lineWidth = 9; g.lineCap = "round"; g.beginPath(); g.arc(200, 225, 40, 0.2, Math.PI - 0.2); g.stroke();
    return new Promise((resolve) => c.toBlob(resolve, "image/jpeg", 0.85));
  }

  // ---------------------------------------------------------------- screens

  const SCREENS = {};

  SCREENS.join = {
    mount(v) {
      if (!v.can_join) {
        return html(`<div class="screen center"><div class="join-logo">${MB.logo()}</div>
          <div class="big-msg">The game has already started</div>
          <p class="muted">Ask the host to start a new game to join in.</p></div>`);
      }
      if (!v.host_joined && !hostKey) {
        return html(`<div class="screen center"><div class="join-logo">${MB.logo()}</div>
          <div class="big-msg bob">Waiting for the host</div>
          <p class="muted">The host joins first. This page updates by itself.</p></div>`);
      }
      const el = html(`<div class="screen">
        <div class="join-logo">${MB.logo()}</div>
        ${!v.host_joined ? `<div class="host-banner">You're the host! Join first to open the game for everyone.</div>` : ""}
        <label class="label" for="name">Your real name</label>
        <input id="name" class="input" maxlength="${v.name_max}" placeholder="e.g. Sam" autocomplete="given-name" autocapitalize="words" enterkeyhint="done">
        <div class="help">The name your friends call you in person. <b>Not a username or gamertag</b>, people need to find you in the room.</div>
        <div class="selfie-zone"></div>
        <div class="grow"></div>
        <button class="btn join-btn">Join the party</button>
        <input class="file" type="file" accept="image/*" capture="user" hidden>
      </div>`);
      const nameInput = $("#name", el);
      nameInput.value = app.draft.name;
      nameInput.oninput = () => { app.draft.name = nameInput.value; };
      const file = $(".file", el);
      file.onchange = async () => {
        if (!file.files[0]) return;
        try { setSelfie(await toSelfie(file.files[0])); }
        catch (e) { MB.toast("That photo didn't work. Please try again."); }
        file.value = "";
      };
      renderSelfieZone(el);
      $(".join-btn", el).onclick = (e) => join(e.currentTarget);
      return el;
    },
  };

  function setSelfie(blob) {
    if (app.draft.url) URL.revokeObjectURL(app.draft.url);
    app.draft.blob = blob;
    app.draft.url = URL.createObjectURL(blob);
    Sound.play("shutter");
    renderSelfieZone(document);
  }

  function renderSelfieZone(root) {
    const zone = $(".selfie-zone", root);
    if (!zone) return;
    const openCamera = () => { Sound.play("click"); $(".file", root).click(); };
    if (app.draft.url) {
      zone.innerHTML = `<span class="ring pop-in"><img src="${app.draft.url}" alt="Your selfie"></span>
        <button class="link retake">Retake</button>`;
      $(".retake", zone).onclick = openCamera;
    } else {
      zone.innerHTML = `<button class="cam-btn breathe" aria-label="Take your selfie">
          <svg viewBox="0 0 24 24"><rect x="2" y="6" width="20" height="14" rx="4" fill="#fff"/><rect x="8" y="3" width="8" height="5" rx="2" fill="#fff"/>
          <circle cx="12" cy="13" r="4.2" fill="#FF8A3D"/><circle cx="12" cy="13" r="2" fill="#fff"/></svg></button>
        <div class="label" style="margin-top:14px">Take your selfie</div>
        <div class="help" style="text-align:center">Make sure your face is clear, this is how people will find you.</div>
        ${devFrame ? '<button class="link cartoon">No camera? Use a cartoon face</button>' : ""}`;
      $(".cam-btn", zone).onclick = openCamera;
      const cartoon = $(".cartoon", zone);
      if (cartoon) cartoon.onclick = async () => setSelfie(await cartoonSelfie());
    }
  }

  async function join(button) {
    const name = $("#name").value.trim();
    if (!name) return MB.toast("Please enter your name.");
    if (!app.draft.blob) return MB.toast("Please take a selfie first.");
    button.disabled = true;
    Sound.play("click");
    const form = new FormData();
    form.append("name", name);
    form.append("selfie", app.draft.blob, "selfie.jpg");
    if (hostKey) form.append("host_key", hostKey);
    try {
      const res = await fetch("/api/join", { method: "POST", body: form });
      const data = await res.json();
      if (!res.ok) { MB.toast(data.error || "Something went wrong."); button.disabled = false; return; }
      MB.store.set("mb_player", data.player_id);
      MB.store.set("mb_name", name);
      Sound.play("pop");
      MB.hello();
    } catch (e) {
      MB.toast("Couldn't reach the game. Check you're on the party Wi-Fi.");
      button.disabled = false;
    }
  }

  SCREENS.lobby = {
    mount(v) {
      const el = html(`<div class="screen center">
        <div class="big-msg">You're in!</div>
        <div class="me-tile">${MB.face(v.me, "bob")}<div class="nm">${esc(v.me.name)}</div></div>
        <p class="muted lobby-count"></p>
        <div class="faces"></div>
        <div class="grow"></div>
        <p class="muted lobby-hint"></p>
      </div>`);
      SCREENS.lobby.update(v, el);
      return el;
    },
    update(v, el) {
      const n = v.players.length;
      $(".lobby-count", el).textContent = `${n} ${n === 1 ? "player" : "players"} here so far`;
      $(".lobby-hint", el).textContent = v.me.is_host
        ? (n >= v.min_players ? "Start when everyone's here." : `You need at least ${v.min_players} players to start.`)
        : "Waiting for the host to start the game.";
      const faces = $(".faces", el);
      const shown = new Set($$("[data-id]", faces).map((f) => f.dataset.id));
      v.players.filter((p) => p.id !== v.me.id && !shown.has(p.id)).forEach((p) => {
        const face = html(MB.face(p, shown.size ? "new" : ""));
        face.dataset.id = p.id;
        faces.prepend(face);
      });
    },
  };

  SCREENS.categories = {
    mount(v) {
      const el = html(`<div class="screen"><div class="title">Pick a category</div>
        ${v.options.map((o) => `<button class="cat ${o.key}" data-key="${o.key}" ${o.available ? "" : "disabled"}>
          <div>${esc(o.name)}<small>${esc(o.blurb)}</small></div>
          <span class="pts">${o.points} ${o.points === 1 ? "pt" : "pts"}</span></button>`).join("")}
      </div>`);
      const enabled = $$(".cat:not(:disabled)", el);
      if (enabled.length) enabled[Math.floor(Math.random() * enabled.length)].classList.add("wiggle");
      $$(".cat", el).forEach((btn) => {
        btn.onclick = () => once(() => { Sound.play("click"); MB.send("pick", { category: btn.dataset.key }); });
      });
      if (!MB.store.get("mb_help_party")) {
        MB.store.set("mb_help_party", "1");
        setTimeout(() => openHelp("party"), 500);
      }
      return el;
    },
    update(v, el) {
      v.options.forEach((o) => { const b = $(`[data-key="${o.key}"]`, el); if (b) b.disabled = !o.available; });
    },
  };

  SCREENS.question = {
    mount(v) {
      const a = v.assignment;
      const pts = `${a.category.points} ${a.category.points === 1 ? "pt" : "pts"}`;
      const el = html(`<div class="screen">
        <div class="grace-slot"></div>
        <div><span class="chip">${esc(a.category.name)} &middot; ${pts}</span></div>
        <div class="q">${MB.question(a.template, a.subject.name)}</div>
        <div class="subject">${MB.face(a.subject, "bob")}<div class="nm">${esc(a.subject.name)}</div>
          <div class="go-find">Go find them and get chatting <span class="arrow">&rarr;</span></div></div>
        <div class="grow"></div>
        <textarea class="input answer" maxlength="${v.answer_max}" placeholder="Type what you found out..."></textarea>
        <div class="char-count">0 / ${v.answer_max}</div>
        <div class="row"><button class="btn ghost skip">Skip</button><button class="btn wide submit">Submit</button></div>
      </div>`);
      const box = $(".answer", el);
      box.oninput = () => { $(".char-count", el).textContent = `${box.value.length} / ${v.answer_max}`; };
      $(".submit", el).onclick = () => {
        const text = box.value.trim();
        if (!text) { MB.toast("Type an answer first."); return; }
        once(() => {
          Sound.play("click");
          el.classList.add("flies-up");
          MB.send("answer", { assignment_id: a.id, text });
          setTimeout(() => el.classList.remove("flies-up"), 2000); // back if the server said no
        });
      };
      $(".skip", el).onclick = () => once(() => { Sound.play("swoop"); MB.send("skip", { assignment_id: a.id }); });
      SCREENS.question.update(v, el);
      return el;
    },
    update(v, el) {
      $(".skip", el).disabled = !v.can_skip;
      const slot = $(".grace-slot", el);
      if (v.deadline && !slot.firstChild) {
        slot.innerHTML = graceBanner(v.deadline, "Submit this one before the timer ends");
        $(".subject", el).classList.add("small");
      }
    },
  };

  SCREENS.grace_wait = {
    mount(v) {
      return html(`<div class="screen center">
        <div class="big-msg" style="margin-top:40px">Time's up!</div>
        <p class="muted" style="margin-bottom:24px">Waiting for the others to finish their last answers.</p>
        ${graceBanner(v.deadline, "Marking starts when the timer ends", true)}
      </div>`);
    },
  };

  SCREENS.mark = {
    mount(v) {
      const c = v.card;
      const pts = `${c.category.points} ${c.category.points === 1 ? "pt" : "pts"}`;
      const left = v.mind_blowns_left;
      const el = html(`<div class="screen">
        <div class="muted" style="font-weight:600">Answers about you: ${v.position} of ${v.total}</div>
        <div class="card mark-card" style="margin-top:10px">
          <span class="chip">${esc(c.category.name)} &middot; ${pts}</span>
          <div class="q">${MB.question(c.template, v.me.name)}</div>
          <div class="quote">"${esc(c.text)}"</div>
          <div class="help">Someone wrote this about you. You won't see who.</div>
        </div>
        <div class="grow"></div>
        <div class="marks">
          <button class="mark correct" data-mark="correct">Correct</button>
          <button class="mark partly" data-mark="partly">Partly right</button>
          <button class="mark wrong" data-mark="wrong">Wrong</button>
          <button class="mark mind_blown" data-mark="mind_blown" ${left ? "" : "disabled"}>Mind blown<small>${left} left</small></button>
        </div>
        ${v.can_undo ? '<button class="undo">Undo last</button>' : ""}
      </div>`);
      $$(".mark", el).forEach((btn) => {
        btn.onclick = () => once(() => {
          const mark = btn.dataset.mark;
          Sound.play(mark);
          const card = $(".mark-card", el);
          card.style.setProperty("--c", MARK_COLOURS[mark]);
          card.classList.add("flick");
          if (mark === "mind_blown") Motion.burst(btn);
          setTimeout(() => MB.send("mark", { answer_id: c.answer_id, mark }), 220);
          setTimeout(() => card.classList.remove("flick"), 2000);
        });
      });
      const undo = $(".undo", el);
      if (undo) undo.onclick = () => once(() => { Sound.play("undo"); MB.send("undo"); });
      return el;
    },
  };

  SCREENS.show_it = {
    mount(v) {
      const c = v.card;
      Sound.play("sparkle");
      const el = html(`<div class="screen">
        <div class="show-it"><div class="burst-bg">${MB.burstSvg("#D9CCFC")}</div>
          ${MB.face(c.subject, "pop-in")}
          <div class="big-msg" style="position:relative;margin-top:22px">Your answer about <span style="color:var(--mind)">${esc(c.subject.name)}</span> blew their mind!</div>
        </div>
        <div class="card grape-card" style="margin-top:14px">
          <div class="muted" style="font-size:15px;margin-bottom:6px">${esc(c.template.replace("{player}", c.subject.name))}</div>
          <div style="font-size:21px;line-height:1.25">"${esc(c.text)}"</div>
        </div>
        <p class="muted" style="text-align:center;margin-top:14px">Show it on the TV before the results?</p>
        <div class="grow"></div>
        <button class="btn grape show" style="margin-bottom:14px">Show it</button>
        <button class="btn ghost keep">Keep it private</button>
      </div>`);
      $(".show", el).onclick = () => once(() => { Sound.play("click"); MB.send("highlight", { answer_id: c.answer_id, show: true }); });
      $(".keep", el).onclick = () => once(() => { Sound.play("click"); MB.send("highlight", { answer_id: c.answer_id, show: false }); });
      return el;
    },
  };

  const TV_ICON = `<svg class="tv-icon" viewBox="0 0 140 110"><rect x="6" y="6" width="128" height="80" rx="16" fill="#FF8A3D"/>
    <rect x="18" y="18" width="104" height="56" rx="8" fill="#FFF6EC"/><path d="M50 104 L70 86 L90 104" stroke="#E8681A" stroke-width="8" fill="none" stroke-linecap="round"/>
    <circle cx="70" cy="46" r="12" fill="#FFD9BD"/></svg>`;

  SCREENS.review_done = {
    mount(v) {
      const el = html(`<div class="screen center">
        ${TV_ICON}
        <div class="big-msg">${v.nothing_to_mark ? "Nothing to mark" : "All done!"}</div>
        <p class="muted">Watch the TV.</p>
        <p class="muted waiting" style="margin-top:8px"></p>
        <div class="grow"></div>
        ${v.can_undo ? '<button class="undo">Undo last</button>' : ""}
      </div>`);
      const undo = $(".undo", el);
      if (undo) undo.onclick = () => once(() => { Sound.play("undo"); MB.send("undo"); });
      SCREENS.review_done.update(v, el);
      return el;
    },
    update(v, el) {
      $(".waiting", el).textContent = v.still_marking
        ? `Waiting for ${v.still_marking} ${v.still_marking === 1 ? "person" : "people"} to finish marking.`
        : "Everyone's finished marking!";
    },
  };

  const ENDING_LINES = {
    highlights: "Mind blown highlights are on!",
    highlight: "Mind blown highlights are on!",
    award: "Awards are being handed out...",
    podium: "The podium is being revealed...",
  };
  const MEDAL = `<svg class="medal" viewBox="0 0 44 44"><path d="M14 2 L22 16 L30 2Z" fill="#8B5CF6"/><circle cx="22" cy="27" r="15" fill="#FFB020"/>
    <circle cx="22" cy="27" r="10" fill="#FFD27A"/></svg>`;

  SCREENS.ending = {
    mount(v) {
      if (!v.results) {
        const el = html(`<div class="screen center">${TV_ICON}<div class="big-msg">Eyes on the TV!</div><p class="muted line"></p></div>`);
        SCREENS.ending.update(v, el);
        return el;
      }
      const r = v.results;
      const stat = (label, value) => `<div class="stat"><b>${value}</b><span class="muted">${label}</span></div>`;
      Sound.play("jingle");
      return html(`<div class="screen center">
        <p class="muted" style="margin-top:10px">You came</p>
        <div class="rank pop-in">#${r.rank}</div>
        <p class="muted">of ${r.of} &middot; <b style="color:var(--cocoa)">${r.points} points</b></p>
        <div class="stats" style="width:100%">
          ${stat("answers submitted", r.submitted)}${stat("correct", r.correct)}
          ${stat("partly right", r.partly)}${stat("wrong", r.wrong)}
          ${stat("Mind blowns received", r.mind_blown)}${stat("Mind blown bonus", `+${r.giver_bonus}`)}
        </div>
        <div style="width:100%;text-align:left">
          ${r.awards.map((a, i) => `<div class="badge" style="animation-delay:${0.3 + i * 0.25}s">${MEDAL}
            <div><div class="t">${esc(a.title)}</div><div class="muted">${esc(a.subtext)}</div></div></div>`).join("")}
        </div>
      </div>`);
    },
    update(v, el) {
      const line = $(".line", el);
      if (line) line.textContent = ENDING_LINES[v.step_kind] || "";
    },
  };

  // ---------------------------------------------------------------- render

  function screenKey(v) {
    switch (v.screen) {
      case "join": return `join:${v.can_join}:${v.host_joined}`;
      case "question": return `question:${v.assignment.id}`;
      case "mark": return `mark:${v.card.answer_id}`;
      case "show_it": return `show_it:${v.card.answer_id}`;
      case "ending": return `ending:${Boolean(v.results)}`;
      default: return v.screen;
    }
  }

  function reactToChanges(prev, v) {
    if (!prev || !v.me || !prev.me) return;
    if (prev.phase !== v.phase) {
      if (v.phase === "party") Sound.play("jingle");
      if (v.phase === "grace") Sound.play("whistle");
      if (v.phase === "review") Sound.play("gong");
    }
    if (v.me.count > prev.me.count) {
      Sound.play("ding");
      setTimeout(() => Motion.bump($("#bar .count")), 30);
    }
    if (v.me.skips > prev.me.skips) setTimeout(() => Sound.play("plink"), 250);
  }

  function onView(v) {
    const prev = app.view;
    app.view = v;
    renderBar(v);
    renderHost(v);
    reactToChanges(prev, v);

    const key = screenKey(v);
    const screen = SCREENS[v.screen];
    const holder = $("#screen");
    if (key !== app.key) {
      app.key = key;
      app.busy = false;
      holder.replaceChildren(screen.mount(v));
      window.scrollTo(0, 0);
    } else if (screen.update) {
      screen.update(v, holder.firstElementChild);
    }
  }

  MB.connect({ role: "phone", onView });
})();
