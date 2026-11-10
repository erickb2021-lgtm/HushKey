"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { ReactLenis, useLenis, type LenisRef } from "lenis/react";
import "lenis/dist/lenis.css";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

/** Tells ScrollTrigger about every Lenis scroll, so scroll animations stay in step. */
function ScrollTriggerSync() {
  useLenis(() => ScrollTrigger.update());
  return null;
}

/**
 * Smooth scrolling for the whole site. Lenis is driven from GSAP's ticker
 * (one animation loop for both), and #anchor links scroll smoothly, stopping
 * just below the fixed header. Lenis switches itself off for people who ask
 * their system for reduced motion.
 */
export default function SmoothScroll({ children }: { children: ReactNode }) {
  const lenisRef = useRef<LenisRef>(null);

  useEffect(() => {
    const update = (time: number) => lenisRef.current?.lenis?.raf(time * 1000);
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    return () => gsap.ticker.remove(update);
  }, []);

  return (
    <ReactLenis root ref={lenisRef} options={{ autoRaf: false, lerp: 0.1, anchors: { offset: -72 } }}>
      <ScrollTriggerSync />
      {children}
    </ReactLenis>
  );
}
