"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import gsap from "gsap";
import type { Flip as FlipPlugin } from "gsap/Flip";
import { useGSAP } from "@gsap/react";
import { useLenis } from "lenis/react";
import TiltedCard from "@/components/reactbits/TiltedCard";
import { CloseIcon } from "@/components/Icons";
import { MOTION_OK, Reveal, SectionHeading } from "@/components/Reveal";
import { asset } from "@/lib/site";

gsap.registerPlugin(useGSAP);

// WebGL carousel: its code is only fetched on desktops, when the section is near.
const CircularGallery = dynamic(() => import("@/components/reactbits/CircularGallery"), { ssr: false });

const CAN_ANIMATE = "(min-width: 1024px) and (pointer: fine) and (prefers-reduced-motion: no-preference)";

// Real screenshots of the app, taken with a made-up demo vault.
const SHOTS = [
  { file: "vault-aurora", title: "Your vault", text: "Every login with its logo. Click one to see its details on the right.", alt: "The HushKey vault with the Aurora Peaks background." },
  { file: "vault-neon", title: "Neon City", text: "One of 15 pixel-art backgrounds. You choose how see-through the boxes are.", alt: "The HushKey vault with the Neon City pixel-art background." },
  { file: "vault-cherry", title: "Cherry Blossom", text: "The same vault with another background.", alt: "The HushKey vault with the Cherry Blossom pixel-art background." },
  { file: "vault", title: "Plain and dark", text: "No background at all, if you like things simple.", alt: "The HushKey vault in plain dark mode." },
  { file: "security", title: "Security tips", text: "A vault score, plus optional tips for weak, reused or leaked passwords.", alt: "The Security tips screen showing a vault score of 98 and one suggestion." },
  { file: "appearance", title: "Appearance", text: "Theme, style, font, color and background, with a live preview.", alt: "The Appearance settings with a live preview of the vault." },
];

export default function Gallery() {
  const root = useRef<HTMLElement>(null);
  const detail = useRef<HTMLDivElement>(null);
  const backdrop = useRef<HTMLDivElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const thumbs = useRef<(HTMLElement | null)[]>([]);
  const flip = useRef<typeof FlipPlugin | null>(null); // GSAP Flip, fetched when the section comes near
  const flipFrom = useRef<Flip.FlipState | null>(null);
  const lastOpened = useRef<number | null>(null);
  const skewTo = useRef<((value: number) => void) | null>(null);

  const [active, setActive] = useState<number | null>(null);
  const [carousel, setCarousel] = useState(false);
  const [labelFont, setLabelFont] = useState("700 24px sans-serif");
  const lenis = useLenis();

  const motionOK = () => window.matchMedia(MOTION_OK).matches;

  // ---- the WebGL carousel: desktop only, loaded when the section comes near ----
  useEffect(() => {
    if (!window.matchMedia(CAN_ANIMATE).matches || !root.current) return;
    // No separate WebGL test here (creating a throwaway context causes a visible hitch):
    // the carousel itself quietly shows nothing if the browser has no WebGL2.
    const observer = new IntersectionObserver(
      entries => {
        if (!entries.some(e => e.isIntersecting)) return;
        observer.disconnect();
        const family = getComputedStyle(document.documentElement).getPropertyValue("--font-space-grotesk").trim();
        if (family) setLabelFont(`700 24px ${family}`);
        setCarousel(true);
      },
      { rootMargin: "600px 0px" },
    );
    observer.observe(root.current);
    return () => observer.disconnect();
  }, []);

  // ---- GSAP Flip is only needed here, so it's fetched when this section comes near ----
  useEffect(() => {
    if (!root.current) return;
    const observer = new IntersectionObserver(
      entries => {
        if (!entries.some(e => e.isIntersecting)) return;
        observer.disconnect();
        import("gsap/Flip").then(plugin => {
          gsap.registerPlugin(plugin.Flip);
          flip.current = plugin.Flip;
        });
      },
      { rootMargin: "100% 0px" },
    );
    observer.observe(root.current);
    return () => observer.disconnect();
  }, []);

  // ---- cards lean with the scroll speed (Lenis velocity), and settle when you stop ----
  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(`(min-width: 768px) and ${MOTION_OK}`, () => {
        skewTo.current = gsap.quickTo("[data-skew]", "skewY", { duration: 0.5, ease: "power3.out" });
        return () => {
          skewTo.current = null;
        };
      });
    },
    { scope: root },
  );
  useLenis(({ velocity }) => skewTo.current?.(gsap.utils.clamp(-4, 4, velocity * 0.1)));

  // ---- grid <-> detail, morphed with GSAP Flip ----
  const open = (index: number) => {
    const thumb = thumbs.current[index];
    flipFrom.current = thumb && flip.current && motionOK() ? flip.current.getState(thumb) : null;
    lastOpened.current = index;
    setActive(index);
  };

  const close = () => {
    flipFrom.current = detail.current && flip.current && motionOK() ? flip.current.getState(detail.current) : null;
    setActive(null);
  };

  useGSAP(
    () => {
      const state = flipFrom.current;
      flipFrom.current = null;
      if (active !== null) {
        closeButton.current?.focus({ preventScroll: true });
        if (state && detail.current && flip.current) {
          flip.current.from(state, { targets: detail.current, duration: 0.65, ease: "power2.inOut", scale: true });
          gsap.from(backdrop.current, { autoAlpha: 0, duration: 0.4, ease: "power1.out" });
          gsap.from("[data-detail-text]", { autoAlpha: 0, y: 16, duration: 0.4, delay: 0.35, ease: "power2.out" });
        }
      } else if (lastOpened.current !== null) {
        const thumb = thumbs.current[lastOpened.current];
        thumb?.closest("button")?.focus({ preventScroll: true });
        if (state && thumb && flip.current) {
          flip.current.from(state, { targets: thumb, duration: 0.55, ease: "power2.inOut", scale: true, zIndex: 60 });
        }
      }
    },
    { dependencies: [active], scope: root },
  );

  // while the detail is open: stop the page scrolling behind it, and let Escape close it
  useEffect(() => {
    if (active === null) return;
    lenis?.stop();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") close();
      if (event.key === "Tab") {
        event.preventDefault(); // the close button is the only control in the dialog
        closeButton.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      lenis?.start();
      window.removeEventListener("keydown", onKey);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, lenis]);

  const shot = active !== null ? SHOTS[active] : null;

  return (
    <section ref={root} id="screens" className="section-pad relative overflow-x-clip" aria-labelledby="screens-title">
      <div className="page relative">
        <SectionHeading
          id="screens-title"
          eyebrow="04 · Inside the app"
          title="See it before you install it."
          intro="These are real screenshots of HushKey, taken with a made-up demo vault."
          align="center"
        />
      </div>

      {/* The carousel's space is always reserved on wide screens, so nothing below it moves when it loads. */}
      <div className="relative mt-8 hidden h-[36rem] lg:block">
        {carousel && (
          /* React Bits CircularGallery, showing the app's own screens. Drag it, or use the arrow keys. */
          <CircularGallery
            items={SHOTS.map(s => ({ image: asset(`/shots/${s.file}.webp`), text: s.title, description: s.text, alt: s.alt }))}
            bend={1.6}
            itemAspect={1.6}
            itemSize={1.25}
            gap={0.2}
            wave={0.6}
            borderRadius={0.012}
            fadeEdges={0.16}
            shadow={0.4}
            scrollSpeed={1.6}
            scrollEase={0.07}
            textColor="#eef1f6"
            font={labelFont}
            dpr={1}
            aria-label="HushKey screenshots. Drag, or use the arrow keys, to turn the gallery."
          />
        )}
      </div>

      <div className="page relative">
        <Reveal as="ul" className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3" stagger={0.06}>
          {SHOTS.map((s, i) => (
            <li key={s.file} data-reveal>
              <div data-skew className="will-change-transform">
                <button
                  type="button"
                  onClick={() => open(i)}
                  className="group block w-full cursor-pointer rounded-card text-left"
                  aria-haspopup="dialog"
                  aria-label={`${s.title}: view larger`}
                >
                  <span
                    ref={node => {
                      thumbs.current[i] = node;
                    }}
                    data-flip-id={active === i ? undefined : `shot-${i}`}
                    className={`block aspect-[16/10] overflow-hidden rounded-card border border-line bg-surface transition-[border-color] duration-200 group-hover:border-fg/60 ${
                      active === i ? "invisible" : ""
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={asset(`/shots/${s.file}-sm.webp`)}
                      width={800}
                      height={500}
                      loading="lazy"
                      decoding="async"
                      alt={s.alt}
                      className="block size-full object-cover transition-transform duration-300 ease-out group-hover:scale-[1.03]"
                    />
                  </span>
                  <span className="label mt-4 block text-fg">{s.title}</span>
                  <span className="mt-1.5 block text-sm text-muted">{s.text}</span>
                </button>
              </div>
            </li>
          ))}
        </Reveal>
      </div>

      {shot && active !== null && (
        <div
          className="fixed inset-0 z-[70] flex flex-col items-center justify-center p-4 sm:p-8"
          role="dialog"
          aria-modal="true"
          aria-label={shot.title}
          data-lenis-prevent
        >
          <div ref={backdrop} className="absolute inset-0 bg-bg/85 backdrop-blur-md" onClick={close} aria-hidden="true" />
          <button
            ref={closeButton}
            type="button"
            onClick={close}
            className="absolute right-4 top-4 z-10 flex size-12 cursor-pointer items-center justify-center rounded-control border border-line-strong bg-surface text-fg transition-colors duration-200 hover:bg-raised"
            aria-label="Close"
          >
            <CloseIcon />
          </button>
          <div
            ref={detail}
            data-flip-id={`shot-${active}`}
            className="relative aspect-[16/10] w-full max-w-[min(72rem,calc((100svh-12rem)*1.6))]"
          >
            {/* React Bits TiltedCard: the big screenshot leans toward the cursor */}
            <TiltedCard
              imageSrc={asset(`/shots/${shot.file}.webp`)}
              altText={shot.alt}
              containerWidth="100%"
              containerHeight="100%"
              imageWidth="100%"
              imageHeight="100%"
              radius={6}
              rotateAmplitude={5}
              scaleOnHover={1.01}
              glare={0.18}
              glareColor="#ffffff"
              shadow={0.7}
              showTooltip={false}
              flipOnClick={false}
              gyroscope={false}
              intro={false}
            />
          </div>
          <p data-detail-text className="relative mt-5 max-w-2xl text-center text-fg">
            <span className="font-bold">{shot.title}.</span> <span className="text-muted">{shot.text}</span>
          </p>
        </div>
      )}
    </section>
  );
}
