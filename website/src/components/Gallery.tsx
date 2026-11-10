"use client";

import { useEffect, useRef, useState } from "react";
import { CloseIcon } from "@/components/Icons";
import { Reveal, SectionHeading } from "@/components/Reveal";
import { asset } from "@/lib/site";

/** Keeps the page from scrolling behind the dialog. Returns the function that lets it scroll again. */
function lockPageScroll() {
  const style = document.documentElement.style;
  const previous = style.overflow;
  style.overflow = "hidden";
  return () => {
    style.overflow = previous;
  };
}

// Real screenshots of the app, taken with a made-up demo vault.
const SHOTS = [
  { file: "vault-aurora", title: "Your vault", text: "Every login with its logo. Click one to see its details on the right.", alt: "The HushKey vault with the Aurora Peaks background." },
  { file: "vault-neon", title: "Neon City", text: "One of 15 pixel-art backgrounds. You choose how see-through the boxes are.", alt: "The HushKey vault with the Neon City pixel-art background." },
  { file: "vault-cherry", title: "Cherry Blossom", text: "The same vault with another background.", alt: "The HushKey vault with the Cherry Blossom pixel-art background." },
  { file: "vault", title: "Plain and dark", text: "No background at all, if you like things simple.", alt: "The HushKey vault in plain dark mode." },
  { file: "security", title: "Security tips", text: "A vault score, plus optional tips for weak, reused or leaked passwords.", alt: "The Security tips screen showing a vault score of 98 and one suggestion." },
  { file: "appearance", title: "Appearance", text: "Theme, style, font, color and background, with a live preview.", alt: "The Appearance settings with a live preview of the vault." },
];

/**
 * The screenshots: a plain grid of pictures. Click one and it opens large in a
 * simple lightbox. Nothing here runs while the page scrolls: the old 3D
 * carousel redrew itself sixty times a second, which is what made this part
 * of the page stutter.
 */
export default function Gallery() {
  const closeButton = useRef<HTMLButtonElement>(null);
  const thumbs = useRef<(HTMLButtonElement | null)[]>([]);
  const lastOpened = useRef<number | null>(null);
  const [active, setActive] = useState<number | null>(null);

  const open = (index: number) => {
    lastOpened.current = index;
    setActive(index);
  };
  const close = () => setActive(null);

  // while the lightbox is open: stop the page scrolling behind it, keep focus inside it, let Escape close it
  useEffect(() => {
    if (active === null) {
      if (lastOpened.current !== null) thumbs.current[lastOpened.current]?.focus({ preventScroll: true });
      return;
    }
    closeButton.current?.focus({ preventScroll: true });
    const unlock = lockPageScroll();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActive(null);
      if (event.key === "Tab") {
        event.preventDefault(); // the close button is the only control in the dialog
        closeButton.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      unlock();
      window.removeEventListener("keydown", onKey);
    };
  }, [active]);

  const shot = active !== null ? SHOTS[active] : null;

  return (
    <section id="screens" className="section-pad relative" aria-labelledby="screens-title">
      <div className="page relative">
        <SectionHeading
          id="screens-title"
          eyebrow="04 · Inside the app"
          title="See it before you install it."
          intro="These are real screenshots of HushKey, taken with a made-up demo vault."
          align="center"
        />

        <Reveal as="ul" className="mt-14 grid gap-5 sm:grid-cols-2 lg:mt-16 lg:grid-cols-3" stagger={0.06}>
          {SHOTS.map((s, i) => (
            <li key={s.file} data-reveal>
              <button
                ref={node => {
                  thumbs.current[i] = node;
                }}
                type="button"
                onClick={() => open(i)}
                className="group block w-full cursor-pointer rounded-card text-left"
                aria-haspopup="dialog"
                aria-label={`${s.title}: view larger`}
              >
                <span className="block aspect-[16/10] overflow-hidden rounded-card border border-line bg-surface transition-[border-color] duration-200 group-hover:border-fg/60">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={asset(`/shots/${s.file}-sm.webp`)}
                    width={800}
                    height={500}
                    loading="lazy"
                    decoding="async"
                    alt={s.alt}
                    className="block size-full object-cover"
                  />
                </span>
                <span className="label mt-4 block text-fg">{s.title}</span>
                <span className="mt-1.5 block text-sm text-muted">{s.text}</span>
              </button>
            </li>
          ))}
        </Reveal>
      </div>

      {shot && (
        <div
          className="fade-in fixed inset-0 z-[70] flex flex-col items-center justify-center p-4 sm:p-8"
          role="dialog"
          aria-modal="true"
          aria-label={shot.title}
        >
          <div className="absolute inset-0 bg-black/90" onClick={close} aria-hidden="true" />
          <button
            ref={closeButton}
            type="button"
            onClick={close}
            className="absolute right-4 top-4 z-10 flex size-12 cursor-pointer items-center justify-center rounded-control border border-line-strong bg-surface text-fg transition-colors duration-200 hover:bg-raised"
            aria-label="Close"
          >
            <CloseIcon />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={asset(`/shots/${shot.file}.webp`)}
            alt={shot.alt}
            width={1600}
            height={1000}
            decoding="async"
            className="relative aspect-[16/10] w-full max-w-[min(72rem,calc((100svh-12rem)*1.6))] rounded-card border border-line-strong object-cover shadow-card"
          />
          <p className="relative mt-5 max-w-2xl text-center text-fg">
            <span className="font-bold">{shot.title}.</span> <span className="text-muted">{shot.text}</span>
          </p>
        </div>
      )}
    </section>
  );
}
