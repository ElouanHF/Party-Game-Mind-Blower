/* Shared animations: bump, flash, fly-away pages, starbursts and confetti. */
(function () {
  const MB = (window.MB = window.MB || {});

  function layer() {
    let el = document.querySelector(".fx-layer");
    if (!el) { el = MB.html('<div class="fx-layer" aria-hidden="true"></div>'); document.body.appendChild(el); }
    return el;
  }
  const speed = () => parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--m")) || 1;

  MB.Motion = {
    /** Restart a CSS animation class on an element. */
    replay(el, cls) {
      if (!el) return;
      el.classList.remove(cls);
      void el.offsetWidth; // force a reflow so the animation starts again
      el.classList.add(cls);
      el.addEventListener("animationend", () => el.classList.remove(cls), { once: true });
    },
    bump(el) { MB.Motion.replay(el, "bump"); },
    flash(el, color) {
      if (!el) return;
      el.style.setProperty("--flash", color);
      MB.Motion.replay(el, "flash");
    },

    /** A page lifts off an element and flutters away, tinted with a colour. */
    flyPage(fromEl, color) {
      if (!fromEl) return;
      const r = fromEl.getBoundingClientRect();
      const page = MB.html(`<div class="fx-page" style="--c:${color}"></div>`);
      page.style.left = `${r.left + r.width / 2 - 23}px`;
      page.style.top = `${r.top + r.height / 2 - 29}px`;
      layer().appendChild(page);
      const drift = (Math.random() * 2 - 1) * 120;
      page.animate([
        { transform: "translate(0,0) rotate(0deg)", opacity: 1 },
        { transform: `translate(${drift * 0.4}px,-60px) rotate(${drift / 6}deg)`, opacity: 1, offset: 0.35 },
        { transform: `translate(${drift}px,-240px) rotate(${drift / 2}deg)`, opacity: 0 },
      ], { duration: 1100 * speed(), easing: "cubic-bezier(.3,.6,.4,1)" }).onfinish = () => page.remove();
    },

    /** A starburst that pops out behind the centre of an element. */
    burst(el, color = "#C4B0FB", size = 260) {
      if (!el) return;
      const r = el.getBoundingClientRect();
      const b = MB.html(`<div class="fx-burst" style="width:${size}px;height:${size}px">${MB.burstSvg(color)}</div>`);
      b.style.left = `${r.left + r.width / 2}px`;
      b.style.top = `${r.top + r.height / 2}px`;
      layer().appendChild(b);
      b.animate([
        { transform: "translate(-50%,-50%) scale(0.2) rotate(0deg)", opacity: 0.95 },
        { transform: "translate(-50%,-50%) scale(1.15) rotate(60deg)", opacity: 0.9, offset: 0.5 },
        { transform: "translate(-50%,-50%) scale(1.4) rotate(90deg)", opacity: 0 },
      ], { duration: 1300 * speed(), easing: "ease-out" }).onfinish = () => b.remove();
    },

    /** Confetti in the theme colours falling across the screen. */
    confetti(count = 120) {
      const colors = ["#FF8A3D", "#FFB020", "#8B5CF6", "#2FBF71", "#F2545B", "#FFD9BD"];
      const root = layer();
      for (let i = 0; i < count; i++) {
        const w = 8 + Math.random() * 8;
        const piece = MB.html(`<div class="fx-confetti" style="left:${Math.random() * 100}vw;width:${w}px;height:${w * (Math.random() < 0.5 ? 1 : 1.8)}px;background:${colors[i % colors.length]}"></div>`);
        root.appendChild(piece);
        const fall = window.innerHeight + 60;
        piece.animate([
          { transform: `translate(0,0) rotate(0deg)` },
          { transform: `translate(${(Math.random() * 2 - 1) * 160}px,${fall}px) rotate(${Math.random() * 900}deg)` },
        ], { duration: (2200 + Math.random() * 2200) * speed(), delay: Math.random() * 900, easing: "cubic-bezier(.25,.4,.5,1)", fill: "backwards" })
          .onfinish = () => piece.remove();
      }
    },
  };
})();
