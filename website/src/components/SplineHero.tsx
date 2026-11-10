"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import type { Application } from "@splinetool/runtime";
import { SPLINE_SCENE } from "@/lib/site";

// Spline's runtime is big, so it's only downloaded when the scene will really be shown.
const Spline = dynamic(() => import("@splinetool/react-spline"), { ssr: false });

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
 */
export default function SplineHero({ onReady }: { onReady: (ready: boolean) => void }) {
  const [live, setLive] = useState(false);
  const [shown, setShown] = useState(false);

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

  if (!live) return null;

  return (
    <div
      className={`absolute inset-0 transition-opacity duration-[1200ms] ease-out ${shown ? "opacity-100" : "opacity-0"}`}
      aria-hidden="true"
    >
      <Spline
        scene={SPLINE_SCENE}
        onLoad={app => {
          hideTemplateParts(app);
          setShown(true);
          onReady(true);
        }}
        className="size-full"
      />
    </div>
  );
}
