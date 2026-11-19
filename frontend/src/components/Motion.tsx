import { useEffect, useRef, useState } from "react";

const reduced = () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Appelle cb une seule fois quand l'élément devient visible. */
function onVisible(el: Element, cb: () => void, threshold = 0.25) {
  if (typeof IntersectionObserver === "undefined") { cb(); return () => {}; }
  const io = new IntersectionObserver((e) => { if (e[0].isIntersecting) { cb(); io.disconnect(); } }, { threshold });
  io.observe(el);
  return () => io.disconnect();
}

const ICONS: Record<string, string[]> = {
  cap: ["M2 9l10-5 10 5-10 5z", "M6 11v5c3 2 9 2 12 0v-5", "M22 9v6"],
  wheat: ["M12 22V8", "M12 8c-3 0-4-2-4-4 3 0 4 2 4 4z", "M12 8c3 0 4-2 4-4-3 0-4 2-4 4z", "M12 14c-3 0-4-2-4-4", "M12 14c3 0 4-2 4-4", "M12 19c-3 0-4-2-4-4", "M12 19c3 0 4-2 4-4"],
  school: ["M3 21h18", "M5 21V10l7-5 7 5v11", "M10 21v-6h4v6"],
  target: ["M12 2a10 10 0 100 20 10 10 0 000-20z", "M12 7a5 5 0 100 10 5 5 0 000-10z", "M12 11.2a.8.8 0 100 1.6.8.8 0 000-1.6z"],
  bulb: ["M9 18h6", "M10 21h4", "M12 3a6 6 0 00-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0012 3z"],
  link: ["M10 13a5 5 0 007 0l3-3a5 5 0 00-7-7l-1 1", "M14 11a5 5 0 00-7 0l-3 3a5 5 0 007 7l1-1"],
  globe: ["M12 2a10 10 0 100 20 10 10 0 000-20z", "M2 12h20", "M12 2c3 3 4 6 4 10s-1 7-4 10c-3-3-4-6-4-10s1-7 4-10z"],
  lock: ["M6 11h12v10H6z", "M8 11V7a4 4 0 118 0v4"],
  search: ["M11 4a7 7 0 100 14 7 7 0 000-14z", "M21 21l-5-5"],
  sprout: ["M12 22V12", "M12 12c0-4-3-6-7-6 0 4 3 6 7 6z", "M12 14c0-3 2-5 6-5 0 3-2 5-6 5z"],
};

/** Icône SVG dont le tracé se dessine en JavaScript quand elle apparaît à l'écran. */
export function Icon({ name }: { name: string }) {
  const ref = useRef<SVGSVGElement>(null);
  useEffect(() => {
    const svg = ref.current; if (!svg || reduced()) return;
    const paths = Array.from(svg.querySelectorAll("path"));
    paths.forEach((p) => { const l = p.getTotalLength(); p.style.strokeDasharray = `${l}`; p.style.strokeDashoffset = `${l}`; });
    return onVisible(svg, () => paths.forEach((p, i) => {
      const l = p.getTotalLength();
      p.animate([{ strokeDashoffset: l }, { strokeDashoffset: 0 }], { duration: 1100, delay: i * 140, easing: "ease-out", fill: "forwards" });
    }), 0.4);
  }, [name]);
  return (
    <svg ref={ref} viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {(ICONS[name] || []).map((d, i) => <path key={i} d={d} />)}
    </svg>
  );
}

/** Compteur animé (requestAnimationFrame) pour les statistiques. */
export function CountUp({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const [n, setN] = useState(reduced() ? value : 0);
  useEffect(() => {
    if (reduced() || !ref.current) { setN(value); return; }
    return onVisible(ref.current, () => {
      const t0 = performance.now(), dur = 1200;
      const tick = (t: number) => { const k = Math.min(1, (t - t0) / dur); setN(Math.round(value * (1 - Math.pow(1 - k, 3)))); if (k < 1) requestAnimationFrame(tick); };
      requestAnimationFrame(tick);
    }, 0.3);
  }, [value]);
  return <span ref={ref}>{n}</span>;
}

/** Mot qui change toutes les 2,4 s avec un fondu. */
export function RotatingWord({ words }: { words: string[] }) {
  const [i, setI] = useState(0);
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (reduced()) return;
    const id = setInterval(() => {
      ref.current?.animate([{ opacity: 1, transform: "translateY(0)" }, { opacity: 0, transform: "translateY(-10px)" }], { duration: 220, fill: "forwards" })
        .finished.then(() => { setI((x) => (x + 1) % words.length); ref.current?.animate([{ opacity: 0, transform: "translateY(10px)" }, { opacity: 1, transform: "translateY(0)" }], { duration: 260, fill: "forwards" }); });
    }, 2400);
    return () => clearInterval(id);
  }, [words.length]);
  return <em ref={ref} className="rot">{words[i]}</em>;
}

/** Fait apparaître en fondu les blocs de la page quand on défile. À appeler une fois (App). */
export function useScrollReveal(key: string) {
  useEffect(() => {
    if (reduced()) return;
    const scan = () => document.querySelectorAll<HTMLElement>(".block,.feat,.actor,.step,.stat-card,.opp,.chip,details,.cta-band").forEach((el) => {
      if (el.dataset.rv) return;
      el.dataset.rv = "1"; el.style.opacity = "0";
      onVisible(el, () => { el.animate([{ opacity: 0, transform: "translateY(26px)" }, { opacity: 1, transform: "translateY(0)" }], { duration: 650, easing: "cubic-bezier(.2,.7,.2,1)", fill: "forwards" }); }, 0.12);
    });
    const timers = [setTimeout(scan, 60), setTimeout(scan, 700), setTimeout(scan, 1800)];
    return () => timers.forEach(clearTimeout);
  }, [key]);
}
