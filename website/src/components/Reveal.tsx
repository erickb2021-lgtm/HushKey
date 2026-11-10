"use client";

import { useEffect, useRef, useState, type ElementType, type ReactNode, type RefObject } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import type { SplitText } from "gsap/SplitText";
import { useGSAP } from "@gsap/react";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/** People who haven't asked their system to reduce motion. */
export const MOTION_OK = "(prefers-reduced-motion: no-preference)";

/**
 * True once the element is within a screen or so of the viewport. Scroll
 * animations are set up then, not all at once when the page loads, which
 * keeps the first seconds light on phones.
 */
function useNear(ref: RefObject<HTMLElement | null>) {
  const [near, setNear] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || near) return;
    const observer = new IntersectionObserver(
      entries => {
        if (entries.some(e => e.isIntersecting)) {
          setNear(true);
          observer.disconnect();
        }
      },
      { rootMargin: "60% 0px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [ref, near]);
  return near;
}

/**
 * Where a block's reveal starts: when its top is 82% of the way down the window.
 * If it's already past that point when the animation is set up (the page jumped
 * straight there: a reload that restores the scroll position, or Back), the
 * reveal plays at once instead of waiting for a scroll that already happened.
 */
const START = "top 82%";
const alreadyInView = (el: HTMLElement | null) => !!el && el.getBoundingClientRect().top < window.innerHeight * 0.82;
const trigger = (el: HTMLElement | null) => (alreadyInView(el) ? undefined : { trigger: el, start: START, once: true });

/**
 * Fades and lifts its `[data-reveal]` children in, one after another, the
 * first time the block scrolls into view. With reduced motion nothing is
 * hidden or moved: the content is simply there.
 */
export function Reveal({
  children,
  className,
  as: Tag = "div",
  stagger = 0.08,
}: {
  children: ReactNode;
  className?: string;
  as?: ElementType;
  stagger?: number;
}) {
  const root = useRef<HTMLElement>(null);
  const near = useNear(root);

  useGSAP(
    () => {
      if (!near) return;
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const items = gsap.utils.toArray<HTMLElement>("[data-reveal]", root.current);
        if (!items.length) return;
        gsap.from(items, {
          y: 36,
          autoAlpha: 0,
          duration: 0.8,
          ease: "power3.out",
          stagger,
          scrollTrigger: trigger(root.current),
        });
      });
    },
    { scope: root, dependencies: [near] },
  );

  return (
    <Tag ref={root} className={className}>
      {children}
    </Tag>
  );
}

/**
 * A section's small label, big heading and intro line. The heading is split
 * into lines that slide up from behind a mask (GSAP SplitText) on scroll.
 */
export function SectionHeading({
  eyebrow,
  title,
  intro,
  align = "left",
  id,
}: {
  eyebrow: string;
  title: ReactNode;
  intro?: ReactNode;
  align?: "left" | "center";
  id?: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const near = useNear(root);

  useGSAP(
    () => {
      if (!near) return;
      const mm = gsap.matchMedia();
      mm.add(MOTION_OK, () => {
        const heading = root.current?.querySelector<HTMLElement>("h2");
        if (!heading) return;
        const rest = gsap.utils.toArray<HTMLElement>("[data-heading-fade]", root.current);
        gsap.set([heading, ...rest], { autoAlpha: 0 });
        let split: SplitText | undefined;
        let cancelled = false;

        // SplitText is fetched here, the first time a heading comes near, so it isn't part of the
        // code the page needs to start. Also wait for the web font, or the lines would be
        // measured with the wrong letter widths.
        Promise.all([import("gsap/SplitText"), document.fonts.ready]).then(([plugin]) => {
          if (cancelled) return;
          gsap.registerPlugin(plugin.SplitText);
          gsap.set(heading, { autoAlpha: 1 });
          split = plugin.SplitText.create(heading, {
            type: "lines",
            mask: "lines",
            autoSplit: true,
            onSplit: self =>
              gsap.from(self.lines, {
                yPercent: 110,
                duration: 0.9,
                ease: "expo.out",
                stagger: 0.09,
                scrollTrigger: trigger(root.current),
              }),
          });
          gsap.to(rest, {
            autoAlpha: 1,
            duration: 0.8,
            ease: "power2.out",
            stagger: 0.1,
            scrollTrigger: trigger(root.current),
          });
        });

        return () => {
          cancelled = true;
          split?.revert();
        };
      });
    },
    { scope: root, dependencies: [near] },
  );

  return (
    <div ref={root} className={align === "center" ? "mx-auto max-w-4xl text-center" : "max-w-4xl"}>
      <p className="eyebrow" data-heading-fade>
        {eyebrow}
      </p>
      <h2 id={id} className="mt-5 text-h2 text-fg">
        {title}
      </h2>
      {intro && (
        <p className="mt-6 text-lead text-muted" data-heading-fade>
          {intro}
        </p>
      )}
    </div>
  );
}
