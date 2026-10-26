/* The TV screen. Keeps player tiles alive between updates so their
   animations (bounces, flashes, flying pages) play on the same elements. */
(function () {
  const { $, $$, esc, html, Sound, Motion } = MB;
  Sound.setVolume(0.9);

  const tv = { view: null, layout: null, centerKey: null, tiles: new Map(), animateJoins: false, qrShown: null, lastTick: null };

  const COLOURS = { correct: "#2FBF71", partly: "#FFB020", wrong: "#F2545B", mind_blown: "#8B5CF6" };
  const CROWN = `<svg class="crown" viewBox="0 0 54 40"><path d="M4 34 L8 8 L19 22 L27 4 L35 22 L46 8 L50 34Z" fill="#FFB020" stroke="#fff" stroke-width="3" stroke-linejoin="round"/><circle cx="27" cy="4" r="3.5" fill="#fff"/></svg>`;
  const TICK = `<svg viewBox="0 0 24 24"><path d="M5 12.5 L10 17 L19 7" stroke="#fff" stroke-width="3.5" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const SPEAKER_ON = `<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4z" fill="#4A2C1D"/><path d="M16 8.5a5 5 0 0 1 0 7M18.5 6a8.5 8.5 0 0 1 0 12" stroke="#FF8A3D" stroke-width="2" fill="none" stroke-linecap="round"/></svg>`;
  const SPEAKER_OFF = `<svg viewBox="0 0 24 24"><path d="M4 9h4l5-4v14l-5-4H4z" fill="#4A2C1D"/><path d="M16 9l5 6M21 9l-5 6" stroke="#F2545B" stroke-width="2" stroke-linecap="round"/></svg>`;
  const FULLSCREEN = `<svg viewBox="0 0 24 24"><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" stroke="#4A2C1D" stroke-width="2.2" fill="none" stroke-linecap="round"/></svg>`;

  const HOWTO = [
    ["Pick a category", "Harder ones are worth more"],
    ["Find the person", "Their face is on your phone"],
    ["Chat and dig", "Get the answer out of them"],
    ["Submit", "Then pick your next one"],
  ];

  const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

  // ---------------------------------------------------------------- layout

  function layoutFor(phase) {
    if (phase === "lobby") return "lobby";
    if (phase === "party" || phase === "grace" || phase === "review") return "grid";
    return "ending";
  }

  function mountStage(layout) {
    const stage = $("#stage");
    tv.tiles = new Map();
    tv.qrShown = null;
    tv.centerKey = null;
    if (layout === "lobby") {
      stage.innerHTML = `<div class="qr-panel"></div>
        <div class="grid-wrap"><div class="grid-title">Who's here</div><div class="grid"></div></div>`;
    } else if (layout === "grid") {
      stage.innerHTML = `<div class="grid-wrap"><div class="grid"></div></div><div class="side"></div>`;
    } else {
      stage.innerHTML = `<div class="center-stage"></div>`;
    }
  }

  // ---------------------------------------------------------------- header & footer

  function renderHead(v) {
    const right = $(".head-right");
    const step = v.step || {};
    let content = "";
    if (v.phase === "lobby") content = `<span class="pill">${plural(v.players.length, "player", "players")}</span>`;
    if (v.phase === "party") content = `<span class="pill">Answers so far<b class="total">${v.total_answers}</b></span>`;
    if (v.phase === "grace") content = `<span class="pill timer-pill" data-deadline="${v.deadline}">Time's up in<b class="secs"></b></span>`;
    if (v.phase === "review") content = `<span class="pill">Mark the answers about you</span>`;
    if (step.kind === "highlight") content = `<span class="pill grape">Mind blown</span><span class="pill">Highlight ${step.number} of ${step.of}</span>`;
    if (step.kind === "award") content = `<span class="pill">Award ${step.number} of ${step.of}</span>`;
    if (step.kind === "podium" || step.kind === "leaderboard") content = `<span class="pill">And the winner is...</span>`;
    if (right.dataset.content !== content) {
      right.dataset.content = content;
      right.innerHTML = content;
      tick();
    }
  }

  const CONFIRM = {
    end: "End the party? Anyone holding a question gets 30 seconds to finish.",
    new_game: "Start a new game? Everyone will need to join again.",
  };

  function renderFoot(v) {
    const left = $(".foot-left");
    let text = "";
    if (v.phase === "lobby" && v.host_joined) text = `Scan the code to join. <b>Use your real name!</b>`;
    if (v.phase === "lobby" && !v.host_joined) text = `The host joins first, using the link in the PyCharm console.`;
    if (v.phase === "party") text = `Find them, chat, answer. <b>Every answer counts.</b>`;
    if (v.phase === "grace") text = `Finish your last answer. <b>No more new questions!</b>`;
    if (v.phase === "review") {
      text = `<div class="legend">${["correct:Correct", "partly:Partly right", "wrong:Wrong", "mind_blown:Mind blown"]
        .map((s) => { const [k, label] = s.split(":"); return `<span><i style="background:${COLOURS[k]}"></i>${label}</span>`; }).join("")}</div>`;
    }
    if (left.dataset.content !== text) { left.dataset.content = text; left.innerHTML = text ? `<span>${text}</span>` : ""; }

    const right = $(".foot-right");
    const buttons = v.controls.map((b) =>
      `<button class="btn ${b.action === "end" ? "ghost" : ""} ${b.enabled ? "pulse" : ""}" data-action="${b.action}" ${b.enabled ? "" : "disabled"}>${esc(b.label)}</button>`).join("");
    const key = buttons + Sound.isMuted();
    if (right.dataset.content === key) return;
    right.dataset.content = key;
    right.innerHTML = `${buttons}
      <button class="icon-btn mute" aria-label="Sound on or off">${Sound.isMuted() ? SPEAKER_OFF : SPEAKER_ON}</button>
      <button class="icon-btn full" aria-label="Full screen">${FULLSCREEN}</button>`;
    $$("[data-action]", right).forEach((btn) => {
      btn.onclick = () => {
        Sound.play("click");
        const action = btn.dataset.action;
        if (CONFIRM[action] && !confirm(CONFIRM[action])) return;
        MB.send("host", { action });
      };
    });
    $(".mute", right).onclick = () => { Sound.setMuted(!Sound.isMuted()); renderFoot(tv.view); Sound.play("click"); };
    $(".full", right).onclick = () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else document.documentElement.requestFullscreen().catch(() => {});
    };
  }

  // ---------------------------------------------------------------- lobby & tiles

  function renderQr(v) {
    const panel = $(".qr-panel");
    if (!panel || tv.qrShown === Boolean(v.qr)) return;
    tv.qrShown = Boolean(v.qr);
    const host = v.join_url.replace(/^https?:\/\//, "").replace(/\/$/, "");
    panel.innerHTML = v.qr
      ? `<div class="qr-card pop-in">${v.qr}</div><div class="big">Scan to join</div>
         <div class="url">or go to <b>${esc(host)}</b></div>`
      : `<div class="waiting-host breathe">Waiting for the host to join</div>
         <p>Host: open the link shown in the PyCharm console on your phone. The code for everyone else appears here once you're in.</p>`;
  }

  function tileHtml(p) {
    return `<div class="tile" data-id="${esc(p.id)}"><div class="face">${p.is_host ? CROWN : ""}${MB.face(p)}<div class="under"></div></div>
      <div class="nm">${esc(p.name)}</div></div>`;
  }

  function stackHtml(n) {
    const layers = Math.min(n, 4);
    let pages = "";
    for (let k = layers - 1; k >= 0; k--) {
      pages += `<div class="p" style="left:${k * 6}%;top:${k * 7}%;transform:rotate(${(k % 2 ? 1 : -1) * k * 2}deg)"></div>`;
    }
    return `<div class="ms">${pages}<div class="n">${n}</div></div>`;
  }

  function renderUnder(tile, p, phase) {
    let kind = "none";
    let markup = "";
    if (phase === "party" || phase === "grace") { kind = `cnt:${p.count}`; markup = `<div class="cnt">${p.count}</div>`; }
    if (phase === "review") {
      kind = p.to_mark ? `stack:${p.to_mark}` : "done";
      markup = p.to_mark ? stackHtml(p.to_mark) : `<div class="done-badge">${TICK}</div>`;
    }
    if (tile.dataset.under === kind) return;
    const under = $(".under", tile);
    const cnt = $(".cnt", under);
    if (cnt && kind.startsWith("cnt:")) cnt.textContent = p.count; // keep the element so its bounce plays
    else under.innerHTML = markup;
    tile.dataset.under = kind;
    tile.classList.toggle("has-under", kind !== "none");
  }

  function renderGrid(v) {
    const grid = $(".grid");
    if (!grid) return;
    const ids = new Set(v.players.map((p) => p.id));
    for (const [id, el] of tv.tiles) if (!ids.has(id)) { el.remove(); tv.tiles.delete(id); }
    v.players.forEach((p) => {
      let tile = tv.tiles.get(p.id);
      if (!tile) {
        tile = html(tileHtml(p));
        if (tv.animateJoins && v.phase === "lobby") tile.classList.add("enter");
        grid.appendChild(tile);
        tv.tiles.set(p.id, tile);
      }
      tile.classList.toggle("off", !p.connected);
      renderUnder(tile, p, v.phase);
    });
    tv.animateJoins = true;
    fitGrid();
  }

  /** Pick the biggest tile size that fits every player on screen. */
  function fitGrid() {
    const grid = $(".grid");
    if (!grid || !tv.view) return;
    const n = Math.max(1, tv.view.players.length);
    const W = grid.clientWidth;
    const H = grid.clientHeight;
    if (!W || !H) return;
    const rem = parseFloat(getComputedStyle(document.documentElement).fontSize);
    const rowHeight = tv.view.phase === "lobby" ? 1.4 : 1.62; // badges and stacks need room
    let size = 5 * rem;
    for (let s = 20 * rem; s >= 5 * rem; s -= 0.25 * rem) {
      const gap = s * 0.3;
      const cols = Math.floor((W + gap * 0.5) / (s * 1.3 + gap * 0.5));
      if (cols < 1) continue;
      const rows = Math.ceil(n / cols);
      if (rows * s * rowHeight + (rows - 1) * gap + s * 0.25 <= H) { size = s; break; }
    }
    grid.style.setProperty("--s", `${size}px`);
    grid.style.setProperty("--gap", `${size * 0.3}px`);
  }
  window.addEventListener("resize", fitGrid);

  function renderSide(v) {
    const side = $(".side");
    if (!side) return;
    if (v.phase === "party" || v.phase === "grace") {
      if (side.dataset.kind === "howto") return;
      side.dataset.kind = "howto";
      side.innerHTML = `<div class="card howto"><h3>How to play</h3>
        ${HOWTO.map(([t, d], i) => `<div class="st"><div class="num">${i + 1}</div><div><div class="t">${t}</div><div class="d">${d}</div></div></div>`).join("")}
        <div class="foot">Tap <b style="color:var(--burnt)">?</b> on your phone for help any time</div></div>`;
      return;
    }
    if (v.phase === "review") {
      side.dataset.kind = "marking";
      const names = v.still_marking || [];
      const body = names.length
        ? `<h3>Still marking</h3><div class="marking-list">${names.map((n) => `<span class="nm-chip">${esc(n)}</span>`).join("")}</div>`
        : `<h3>Everyone's done!</h3><div class="marking-list">Time for the highlights.</div>`;
      if (side.dataset.body !== body) { side.dataset.body = body; side.innerHTML = `<div class="card">${body}</div>`; }
    }
  }

  // ---------------------------------------------------------------- ending

  function renderCenter(v) {
    const stage = $(".center-stage");
    const step = v.step;
    if (!stage || !step) return;
    const isBoard = step.kind === "podium" || step.kind === "leaderboard";
    const key = isBoard ? "board" : `${step.kind}:${step.number}`;
    if (key !== tv.centerKey) {
      tv.centerKey = key;
      if (step.kind === "highlight") stage.replaceChildren(highlightEl(step));
      else if (step.kind === "award") stage.replaceChildren(awardEl(step));
      else stage.replaceChildren(html(`<div class="podium-wrap"><div class="podium"></div></div>`));
    }
    if (isBoard) updateBoard(step);
  }

  function highlightEl(step) {
    const el = html(`<div class="hl">
      <div class="who">${MB.face(step.subject)}<div class="nm">${esc(step.subject.name)}</div></div>
      <div class="mid"><div class="qtext">${MB.question(step.template, step.subject.name)}</div>
        <div class="bubble">"${esc(step.text)}"</div></div>
      <div class="who author"><div class="by">Answered by</div><div class="face-wrap"><div class="hl-burst">${MB.burstSvg("#C4B0FB")}</div>${MB.face(step.author)}</div>
        <div class="nm">${esc(step.author.name)}</div></div>
    </div>`);
    setTimeout(() => {
      if (el.isConnected) Sound.play("sparkle");
    }, 2000 * (parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--m")) || 1));
    return el;
  }

  function awardEl(step) {
    return html(`<div class="award-card">
      <div class="title">${esc(step.title)}</div>
      <div class="winners">${step.winners.map((w) => `<div class="w">${MB.face(w)}<div class="nm">${esc(w.name)}</div>
        <div class="sub">${esc(w.subtext)}</div></div>`).join("")}</div>
    </div>`);
  }

  function updateBoard(step) {
    const podium = $(".podium");
    const order = [2, 1, 3].map((place) => step.podium.find((p) => p.place === place)).filter(Boolean);
    order.forEach((p) => {
      let col = $(`.pcol.p${p.place}`, podium);
      if (!col) {
        col = html(`<div class="pcol p${p.place} hidden"><div class="who">
            <div class="faces ${p.players.length > 2 ? "many" : ""}">${p.players.map((x) => MB.face(x)).join("")}</div>
            <div class="nm">${p.players.map((x) => esc(x.name)).join(" & ")}</div>
            <div class="pts">${p.points} pts</div></div>
          <div class="pblock">${p.place}</div></div>`);
        podium.appendChild(col);
      }
      if (p.revealed && col.classList.contains("hidden")) {
        col.classList.remove("hidden");
        if (step.just_revealed === p.place) col.classList.add("rise");
      }
    });
    if (step.kind === "leaderboard" && !$(".lb-wrap")) {
      const MAX_ROWS = 24;
      const rows = step.rows.slice(0, MAX_ROWS);
      const more = step.rows.length - rows.length;
      const cls = step.rows.length > 10 ? "leaderboard two-cols" : "leaderboard";
      const board = html(`<div class="lb-wrap"><div class="${cls}">${rows.map((r, i) =>
        `<div class="lb-row" style="animation-delay:${i * 0.05}s"><span class="r">${r.rank}</span>${MB.face(r)}
          <span class="n">${esc(r.name)}</span><span class="p">${r.points}</span></div>`).join("")}</div>
        ${more > 0 ? `<div class="lb-more">and ${more} more</div>` : ""}</div>`);
      $(".podium-wrap").classList.add("with-board");
      $(".podium-wrap").appendChild(board);
    }
  }

  // ---------------------------------------------------------------- fx cues

  function onFx(fx) {
    switch (fx.type) {
      case "joined": Sound.play("pop"); break;
      case "start": Sound.play("jingle"); break;
      case "counter_up": {
        const tile = tv.tiles.get(fx.player_id);
        Motion.bump(tile && $(".cnt", tile));
        Motion.bump($(".total"));
        Sound.play("pop");
        break;
      }
      case "end_party": Sound.play("whistle"); break;
      case "times_up": Sound.play("gong"); break;
      case "mark": {
        const marker = tv.tiles.get(fx.marker_id);
        const author = tv.tiles.get(fx.author_id);
        const colour = COLOURS[fx.mark];
        Motion.flyPage(marker && $(".under", marker), colour);
        Motion.flash(author && $(".ring", author), colour);
        if (fx.mark === "mind_blown") Motion.burst(author && $(".ring", author));
        Sound.play("whoosh");
        setTimeout(() => Sound.play(fx.mark), 150);
        break;
      }
      case "undo": Sound.play("undo"); break;
      case "reveal": revealCue(fx.step); break;
      default: break;
    }
  }

  function revealCue(step) {
    if (!step) return;
    const m = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--m")) || 1;
    if (step.kind === "highlight") Sound.play("whoosh");
    if (step.kind === "award") Sound.play("jingle");
    if (step.kind === "leaderboard") Sound.play("jingle");
    if (step.kind === "podium") {
      Sound.play("drumroll");
      if (step.place === 1) setTimeout(() => { Sound.play("fanfare"); Motion.confetti(); }, 1500 * m);
      else setTimeout(() => Sound.play("pop"), 1500 * m);
    }
  }

  // ---------------------------------------------------------------- countdown

  function tick() {
    const pill = $("[data-deadline]");
    if (!pill) return;
    const left = MB.secondsLeft(Number(pill.dataset.deadline));
    $(".secs", pill).textContent = left;
    pill.classList.toggle("hurry", left <= 10);
    if (left <= 10 && left > 0 && left !== tv.lastTick) { tv.lastTick = left; Sound.play("tick"); }
  }
  setInterval(tick, 200);

  // ---------------------------------------------------------------- dev panel

  function renderDev(v) {
    const existing = $(".devpanel");
    if (!v.dev) { if (existing) existing.remove(); return; }
    if (existing) return;
    const panel = html(`<div class="devpanel closed"><button class="dev-toggle"><b>DEV TOOLS</b></button>
      <button data-dev="add_bots" data-count="1">Add 1 bot</button>
      <button data-dev="add_bots" data-count="5">Add 5 bots</button>
      <button data-dev="bots_now">Bots act now</button>
      <button data-dev="skip_timer">Skip timer</button>
      <button data-dev="mark_all">Mark all randomly</button>
      <button data-dev="reset">Reset game</button>
      <button class="slow">Slow motion</button>
      <select class="snd">${Sound.names.map((n) => `<option>${n}</option>`).join("")}</select>
      <button class="play">Play sound</button></div>`);
    document.body.appendChild(panel);
    $$("[data-dev]", panel).forEach((b) => {
      b.onclick = () => MB.send("dev", { action: b.dataset.dev, count: Number(b.dataset.count || 1) });
    });
    $(".slow", panel).onclick = (e) => {
      document.documentElement.classList.toggle("slow");
      e.currentTarget.classList.toggle("on");
    };
    $(".play", panel).onclick = () => Sound.play($(".snd", panel).value);
    $(".dev-toggle", panel).onclick = () => panel.classList.toggle("closed");
  }

  // ---------------------------------------------------------------- render

  function onView(v) {
    tv.view = v;
    const layout = layoutFor(v.phase);
    if (layout !== tv.layout) {
      tv.layout = layout;
      mountStage(layout);
    }
    renderHead(v);
    if (layout === "lobby") { renderQr(v); renderGrid(v); }
    if (layout === "grid") { renderSide(v); renderGrid(v); }
    if (layout === "ending") renderCenter(v);
    renderFoot(v);
    renderDev(v);
  }

  $(".tv-logo").innerHTML = MB.logo();
  MB.connect({ role: "tv", onView, onFx });
})();
