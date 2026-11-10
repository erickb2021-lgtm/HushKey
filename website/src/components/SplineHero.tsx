"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { Application } from "@splinetool/runtime";
import { SPLINE_SCENE } from "@/lib/site";

// Spline's runtime is big, so it's only downloaded when the scene will really be shown.
const Spline = dynamic(() => import("@splinetool/react-spline"), { ssr: false });

/** The scene is drawn at this fraction of the stage's size and scaled up (fewer pixels to shade). */
const RENDER_SCALE = 0.5;

/**
 * If a visitor's computer can't draw the scene at this many frames per second
 * (checked over the first few seconds), the scene is switched off and the HTML
 * headline takes its place. Better a still hero than a stuttering one.
 */
const MIN_FPS = 30;

/** Wide screen, a real mouse, and no request for reduced motion. */
const CAN_ANIMATE = "(min-width: 768px) and (pointer: fine) and (prefers-reduced-motion: no-preference)";

/**
 * Parts of the scene that belong to the Spline template, not to HushKey: its own
 * menu (HOME / ABOUT / PRODUCT), the "2024 / 20XX" dates, the "FROM EARTH / TARGET
 * MARS" labels and the "Scroll Down" globe (Group 100 and 88). They're switched off when the scene
 * loads. Everything else (the letters, the glass cube, the outline rows, the ✦
 * sparkles, and the HUSH KEY text) stays. If you delete these in Spline instead, this list does nothing.
 */
const TEMPLATE_PARTS = [
  "Group 98.png", "Group 98.png 2", "Group 98.png 3", "Group 98.png 4", "Group 98.png 5",
  "Group 99.png", "Group 100.png", "Group 88.png", "Group 3", "Group 4",
  "Text", "Text 2", "Text 3", "Text 4", "Text 5", "Text 7", "Text 8",
];
// "Text 6" is the HUSH KEY headline itself, so it is deliberately not in the list above.

function hideTemplateParts(app: Application) {
  for (const object of app.getAllObjects()) {
    if (TEMPLATE_PARTS.includes(object.name)) object.visible = false;
  }
}

function hasWebGL2() {
  try {
    return !!document.createElement("canvas").getContext("webgl2");
  } catch {
    return false;
  }
}

/**
 * The 3D hero scene (Spline). On desktops it fades in over the HTML headline
 * once the page is idle and the scene has loaded; `onReady` tells the hero to
 * fade that headline out. Phones, reduced-motion and browsers without WebGL2
 * never load it and keep the HTML headline.
 *
 * The scene only renders while it's on screen: as soon as the visitor scrolls
 * past the hero, or switches tabs, it pauses, so the rest of the page scrolls
 * without the 3D work running in the background.
 */
export default function SplineHero({ onReady }: { onReady: (ready: boolean) => void }) {
  const [live, setLive] = useState(false);
  const [shown, setShown] = useState(false);
  const [tooSlow, setTooSlow] = useState(false);
  const stage = useRef<HTMLDivElement>(null);
  const app = useRef<Application | null>(null);
  const onScreen = useRef(true);

  useEffect(() => {
    if (!SPLINE_SCENE) return;
    const query = window.matchMedia(CAN_ANIMATE);
    let idle = 0;
    let timer = 0;

    const decide = () => {
      if (!query.matches) {
        setLive(false);
        setShown(false);
        onReady(false);
        return;
      }
      const start = () => {
        if (!hasWebGL2()) return; // tested here, while the page is idle, because the test itself is slow
        setLive(true);
      };
      if (typeof window.requestIdleCallback === "function") idle = window.requestIdleCallback(start, { timeout: 2000 });
      else timer = window.setTimeout(start, 600);
    };

    decide();
    query.addEventListener("change", decide);
    return () => {
      query.removeEventListener("change", decide);
      if (idle && typeof window.cancelIdleCallback === "function") window.cancelIdleCallback(idle);
      window.clearTimeout(timer);
    };
  }, [onReady]);

  // pause the scene while it can't be seen
  useEffect(() => {
    if (!live || !stage.current) return;
    const sync = () => {
      const a = app.current;
      if (!a) return;
      if (onScreen.current && document.visibilityState === "visible") a.play();
      else a.stop();
    };
    const observer = new IntersectionObserver(
      entries => {
        onScreen.current = entries.some(e => e.isIntersecting);
        sync();
      },
      { threshold: 0.05 },
    );
    observer.observe(stage.current);
    document.addEventListener("visibilitychange", sync);
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", sync);
    };
  }, [live]);

  // watch the frame rate for a few seconds after the scene appears
  useEffect(() => {
    if (!shown || tooSlow) return;
    let frames = 0;
    let raf = 0;
    const started = performance.now();
    const tick = () => {
      frames += 1;
      const elapsed = performance.now() - started;
      if (elapsed < 4000) {
        raf = requestAnimationFrame(tick);
        return;
      }
      if (onScreen.current && document.visibilityState === "visible" && frames / (elapsed / 1000) < MIN_FPS) {
        app.current?.stop();
        setTooSlow(true);
        onReady(false);
      }
    };
    const delay = window.setTimeout(() => {
      raf = requestAnimationFrame(tick);
    }, 1500); // skip the first moments, while the scene is still settling
    return () => {
      window.clearTimeout(delay);
      cancelAnimationFrame(raf);
    };
  }, [shown, tooSlow, onReady]);

  if (!live || tooSlow) return null;

  return (
    <div
      ref={stage}
      className={`absolute inset-0 transition-opacity duration-[1200ms] ease-out ${shown ? "opacity-100" : "opacity-0"}`}
      aria-hidden="true"
    >
      <div
        className="absolute left-0 top-0 origin-top-left"
        style={{
          width: `${100 / RENDER_SCALE}%`,
          height: `${100 / RENDER_SCALE}%`,
          transform: `scale(${RENDER_SCALE})`,
        }}
      >
        <Spline
          scene={SPLINE_SCENE}
          onLoad={loaded => {
            app.current = loaded;
            hideTemplateParts(loaded);
            if (!onScreen.current) loaded.stop();
            setShown(true);
            onReady(true);
          }}
          className="size-full"
        />
      </div>
    </div>
  );
}
