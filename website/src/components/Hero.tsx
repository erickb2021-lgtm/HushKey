"use client";

import { useCallback, useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import DownloadButtons from "@/components/DownloadButtons";
import LatestVersion from "@/components/LatestVersion";
import { MOTION_OK } from "@/components/Reveal";
import SplineHero from "@/components/SplineHero";

gsap.registerPlugin(useGSAP);

const ROW = "HUSHKEY HUSHKEY HUSHKEY";

/**
 * The hero. The stage is the 3D Spline scene on desktops; until it loads, and
 * on phones, the same composition is drawn in HTML: outline rows, a huge grainy
 * "HUSHKEY", and ✦ sparkles. Below the stage sit the real words and the
 * download buttons, so they're never covered by the art.
 */
export default function Hero() {
  const root = useRef<HTMLElement>(null);
  const [sceneReady, setSceneReady] = useState(false);
  const onReady = useCallback((ready: boolean) => setSceneReady(ready), []);

  // One entrance, played once: the headline rises, then the copy and buttons follow.
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        if (performance.now() > 1500) return; // page was slow to get ready: just show everything
        const tl = gsap.timeline({ defaults: { ease: "power3.out", duration: 0.7 } });
        tl.from("[data-hero-title]", { yPercent: 30, autoAlpha: 0, duration: 1, ease: "expo.out" }, 0)
          .from("[data-hero-row]", { autoAlpha: 0, duration: 1 }, 0.2)
          .from("[data-hero-spark]", { scale: 0, autoAlpha: 0, stagger: 0.06, ease: "back.out(2)" }, 0.5)
          .from("[data-hero-label]", { autoAlpha: 0, stagger: 0.08 }, 0.6)
          .from("[data-hero-copy]", { y: 20, autoAlpha: 0 }, 0.7)
          .from("[data-hero-cta]", { y: 16, autoAlpha: 0, stagger: 0.07 }, 0.85);
      });
    },
    { scope: root },
  );

  return (
    <section ref={root} id="top" className="relative isolate overflow-hidden bg-bg">
      {/* ---- the stage ---- */}
      <div className="relative h-[calc(100svh-4rem)] min-h-[34rem] w-full pt-16">
        <div className="hero-fallback absolute inset-0" aria-hidden="true" />

        {/* HTML version of the scene */}
        <div
          className={`absolute inset-0 flex flex-col items-center justify-center overflow-hidden transition-opacity duration-700 ${
            sceneReady ? "pointer-events-none opacity-0" : "opacity-100"
          }`}
          data-scene-fallback
        >
          <p data-hero-row className="outline-text font-display text-hero uppercase whitespace-nowrap select-none" aria-hidden="true">
            {ROW}
          </p>
          <h1 data-hero-title className="text-grain relative -my-[0.12em] px-4 text-center text-hero">
            Hush Key
          </h1>
          <p data-hero-row className="outline-text font-display text-hero uppercase whitespace-nowrap select-none" aria-hidden="true">
            {ROW}
          </p>
          <span data-hero-spark className="spark left-[14%] top-[22%]" aria-hidden="true">✦</span>
          <span data-hero-spark className="spark right-[14%] top-[22%]" aria-hidden="true">✦</span>
          <span data-hero-spark className="spark left-1/2 top-[20%] -translate-x-1/2 text-xs" aria-hidden="true">×</span>
          <span data-hero-spark className="spark bottom-[18%] left-[14%]" aria-hidden="true">✦</span>
          <span data-hero-spark className="spark bottom-[18%] right-[14%]" aria-hidden="true">✦</span>
        </div>

        {/* the 3D scene, desktops only */}
        <SplineHero onReady={onReady} />

        {/* corner labels, like the scene's own */}
        <div className="page label pointer-events-none absolute inset-x-0 top-24 flex justify-between text-muted">
          <span data-hero-label>Free · Open source</span>
          <span data-hero-label>Windows · Mac</span>
        </div>
        {/* bottom row: version left, "scroll" centre; the right corner is left free for Spline's own badge */}
        <div className="page label pointer-events-none absolute inset-x-0 bottom-6 grid grid-cols-[1fr_auto_1fr] items-end text-muted">
          <span data-hero-label className="pointer-events-auto">
            <LatestVersion />
          </span>
          <span data-hero-label className="hidden sm:inline">
            Scroll ↓
          </span>
          <span />
        </div>
      </div>

      {/* ---- the words and the buttons ---- */}
      <div className="page relative grid gap-8 border-t border-line py-10 md:grid-cols-[1.2fr_1fr] md:items-center md:py-14">
        <div data-hero-copy>
          <p className="text-h3 font-bold text-fg">Your passwords, kept hush.</p>
          <p className="mt-3 max-w-xl text-lead text-muted">
            HushKey is a free password manager for Windows and Mac. Your logins are encrypted on your own computer,
            and only you can open them.
          </p>
        </div>
        <DownloadButtons className="md:justify-end" />
      </div>
    </section>
  );
}
