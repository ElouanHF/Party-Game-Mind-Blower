/* Sound effects, made in the browser with the Web Audio API. No audio files, no music.
   Browsers only allow sound after a tap, so the first tap anywhere switches it on. */
(function () {
  const MB = (window.MB = window.MB || {});
  let ctx = null;
  let master = null;
  let volume = 0.8;
  let muted = MB.store ? MB.store.get("mb_muted") === "1" : false;

  function audio() {
    if (!ctx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return null;
      ctx = new AC();
      master = ctx.createGain();
      master.gain.value = volume;
      master.connect(ctx.destination);
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  ["pointerdown", "keydown"].forEach((ev) => document.addEventListener(ev, audio, { capture: true }));

  /** One note with a quick fade in and a smooth fade out. */
  function tone({ freq, to, type = "sine", dur = 0.15, vol = 0.3, delay = 0 }) {
    const t0 = ctx.currentTime + delay;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (to) osc.frequency.exponentialRampToValueAtTime(to, t0 + dur);
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(vol, t0 + 0.008);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(gain).connect(master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.05);
  }

  /** A burst of filtered noise, for whooshes, shutters and drums. */
  function noise({ dur = 0.2, vol = 0.3, freq = 1000, to, filter = "bandpass", delay = 0 }) {
    const t0 = ctx.currentTime + delay;
    const buffer = ctx.createBuffer(1, Math.ceil(ctx.sampleRate * dur), ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < data.length; i++) data[i] = Math.random() * 2 - 1;
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    const f = ctx.createBiquadFilter();
    f.type = filter;
    f.frequency.setValueAtTime(freq, t0);
    if (to) f.frequency.exponentialRampToValueAtTime(to, t0 + dur);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, t0);
    gain.gain.exponentialRampToValueAtTime(vol, t0 + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    src.connect(f).connect(gain).connect(master);
    src.start(t0);
  }

  const arpeggio = (notes, gap, opts = {}) =>
    notes.forEach((freq, i) => tone({ freq, dur: 0.25, vol: 0.18, type: "triangle", ...opts, delay: (opts.delay || 0) + i * gap }));

  const SOUNDS = {
    click: () => tone({ freq: 900, to: 600, type: "triangle", dur: 0.05, vol: 0.12 }),
    pop: () => tone({ freq: 280, to: 900, dur: 0.12, vol: 0.35 }),
    shutter: () => { noise({ dur: 0.05, vol: 0.4, freq: 3000, filter: "highpass" }); noise({ dur: 0.06, vol: 0.3, freq: 2000, filter: "highpass", delay: 0.08 }); },
    ding: () => { tone({ freq: 1320, dur: 0.5, vol: 0.22 }); tone({ freq: 1980, dur: 0.3, vol: 0.06 }); },
    swoop: () => tone({ freq: 900, to: 220, dur: 0.25, vol: 0.22 }),
    plink: () => tone({ freq: 1600, to: 2100, type: "triangle", dur: 0.1, vol: 0.18 }),
    whistle: () => { tone({ freq: 2100, to: 2300, dur: 0.2, vol: 0.16 }); tone({ freq: 2100, to: 2500, dur: 0.45, vol: 0.16, delay: 0.25 }); },
    tick: () => tone({ freq: 1250, type: "square", dur: 0.03, vol: 0.06 }),
    gong: () => [110, 221, 331, 442].forEach((freq, i) => tone({ freq, dur: 2.2, vol: 0.28 / (i + 1) })),
    whoosh: () => noise({ dur: 0.35, vol: 0.25, freq: 500, to: 3500 }),
    correct: () => { tone({ freq: 880, dur: 0.15, vol: 0.22, type: "triangle" }); tone({ freq: 1318, dur: 0.32, vol: 0.22, type: "triangle", delay: 0.1 }); },
    partly: () => { tone({ freq: 620, dur: 0.15, vol: 0.2, type: "triangle" }); tone({ freq: 700, dur: 0.22, vol: 0.2, type: "triangle", delay: 0.14 }); },
    wrong: () => tone({ freq: 240, to: 150, dur: 0.3, vol: 0.28, type: "triangle" }),
    mind_blown: () => { tone({ freq: 90, to: 40, dur: 0.7, vol: 0.5 }); noise({ dur: 0.5, vol: 0.22, freq: 400, filter: "lowpass" }); arpeggio([1046, 1318, 1568, 2093], 0.06, { delay: 0.12 }); },
    sparkle: () => arpeggio([1568, 2093, 2637, 3136], 0.05, { vol: 0.12 }),
    jingle: () => arpeggio([784, 988, 1175, 1568], 0.09),
    drumroll: () => { for (let i = 0; i < 22; i++) noise({ dur: 0.06, vol: 0.12 + i * 0.006, freq: 220, filter: "lowpass", delay: i * 0.065 }); },
    fanfare: () => {
      [[523, 659, 784], [587, 740, 880], [784, 988, 1175, 1568]].forEach((chord, i) =>
        chord.forEach((freq) => tone({ freq, dur: i === 2 ? 0.9 : 0.22, vol: 0.12, type: "triangle", delay: i * 0.22 })));
    },
    undo: () => tone({ freq: 300, to: 800, dur: 0.18, vol: 0.18 }),
  };

  MB.Sound = {
    names: Object.keys(SOUNDS),
    play(name) {
      if (muted || !SOUNDS[name]) return;
      try { if (audio()) SOUNDS[name](); } catch (e) { /* never let sound break the game */ }
    },
    setVolume(v) { volume = v; if (master) master.gain.value = v; },
    isMuted: () => muted,
    setMuted(value) { muted = value; if (MB.store) MB.store.set("mb_muted", value ? "1" : "0"); },
  };
})();
