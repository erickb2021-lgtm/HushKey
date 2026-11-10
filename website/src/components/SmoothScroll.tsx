"use client";

import { useEffect, type ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/**
 * Scrolling is the browser's own: no smoothing library, so the page moves the
 * instant the wheel does. Anchor links (#features and so on) still glide, via
 * CSS `scroll-behavior: smooth` in globals.css. This component only makes sure
 * GSAP's ScrollTrigger re-measures the page once fonts and images have settled.
 */
export default function SmoothScroll({ children }: { children: ReactNode }) {
  useEffect(() => {
    ScrollTrigger.config({ ignoreMobileResize: true });
    const refresh = () => ScrollTrigger.refresh();
    document.fonts?.ready.then(refresh);
    window.addEventListener("load", refresh, { once: true });
    return () => window.removeEventListener("load", refresh);
  }, []);

  return <>{children}</>;
}
