"use client";

import { useRef, type ReactNode } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useGSAP } from "@gsap/react";
import { DeviceIcon, LockIcon } from "@/components/Icons";
import { asset } from "@/lib/site";

gsap.registerPlugin(ScrollTrigger, useGSAP);

/** The pinned version needs room side by side and a visitor who is fine with motion. */
const PINNED = "(min-width: 1024px) and (min-height: 700px) and (prefers-reduced-motion: no-preference)";

// Made-up examples for the pictures. Nothing here is a real password or real vault data.
const CIPHER = ["gAAAAABnK3vQ8xY2mJ4tR7wLp0sVd9", "ZfH1cN6uEoB5aXi3yTqM8kWjU2rGsD", "7hPzC4lAeO0nVbF9xItY6wQmKuR1=="];

function Frame({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`panel p-6 shadow-card sm:p-8 ${className}`}>
      {children}
    </div>
  );
}

function Cipher() {
  return (
    <p className="text-gradient break-all font-mono text-sm leading-relaxed">
      <span className="sr-only">Encrypted text that nobody can read.</span>
      {CIPHER.map(line => (
        <span key={line} className="block" aria-hidden="true">
          {line}
        </span>
      ))}
    </p>
  );
}

const SCENES: { step: string; title: string; text: string; visual: ReactNode }[] = [
  {
    step: "Lock",
    title: "Locked on your computer.",
    text: "Before anything is saved, HushKey encrypts it with a key made from your master password. The master password itself never leaves your computer.",
    visual: (
      <Frame>
        <p className="label text-muted">What you type</p>
        <p className="mt-2 font-mono text-lg text-fg">Sunny-Otter-42-Lake</p>
        <div className="my-6 flex items-center gap-3 text-accent">
          <span className="h-px flex-1 bg-line-strong" />
          <span className="flex size-11 items-center justify-center rounded-control border border-line-strong text-fg">
            <LockIcon size={20} />
          </span>
          <span className="h-px flex-1 bg-line-strong" />
        </div>
        <p className="label text-muted">What gets saved</p>
        <div className="mt-2">
          <Cipher />
        </div>
      </Frame>
    ),
  },
  {
    step: "Sync",
    title: "Synced, and still locked.",
    text: "Sync uploads only encrypted data. The server can't read it, and every download is checked to make sure nobody changed it on the way.",
    visual: (
      <Frame>
        <div className="flex items-center justify-between gap-3">
          <div className="flex flex-col items-center gap-2 text-center text-sm text-muted">
            <span className="flex size-14 items-center justify-center rounded-card border border-line-strong bg-raised text-fg">
              <DeviceIcon size={26} />
            </span>
            This computer
          </div>
          <div className="relative flex-1 border-t border-dashed border-line-strong">
            <span className="label absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 items-center gap-1.5 border border-line-strong bg-bg px-3 py-1 text-fg">
              <LockIcon size={14} />
              encrypted
            </span>
          </div>
          <div className="flex flex-col items-center gap-2 text-center text-sm text-muted">
            <span className="flex size-14 items-center justify-center rounded-card border border-line-strong bg-raised text-fg">
              <DeviceIcon size={26} />
            </span>
            Your other computer
          </div>
        </div>
        <p className="label mt-8 text-muted">All the server ever holds</p>
        <div className="mt-2">
          <Cipher />
        </div>
      </Frame>
    ),
  },
  {
    step: "Unlock",
    title: "Opened only by you.",
    text: "Your master password is the only key. Inside the vault, usernames and passwords stay hidden until you click Show, and anything you copy is cleared from your clipboard after 20 seconds.",
    visual: (
      <div className="overflow-hidden rounded-card border border-line-strong shadow-card">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={asset("/shots/signin-sm.webp")}
          width={800}
          height={500}
          loading="lazy"
          decoding="async"
          alt="The HushKey sign-in screen, asking for an email and master password."
          className="block h-auto w-full"
        />
      </div>
    ),
  },
];

/**
 * "How it protects you", told in three steps. On a desktop the section pins
 * to the screen and scrolling plays the steps one after another (the site's
 * one pinned, scrubbed chapter). On phones, short windows and with reduced
 * motion, the same three steps are simply stacked down the page.
 */
export default function Chapters() {
  const root = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const mm = gsap.matchMedia();
      mm.add(PINNED, () => {
        const scenes = gsap.utils.toArray<HTMLElement>("[data-scene]", root.current);
        const dots = gsap.utils.toArray<HTMLElement>("[data-step]", root.current);
        const part = (scene: HTMLElement, name: string) => scene.querySelector(`[data-scene-${name}]`);

        scenes.slice(1).forEach(scene => {
          gsap.set(scene, { autoAlpha: 0 });
          gsap.set(part(scene, "text"), { y: 48 });
          gsap.set(part(scene, "visual"), { y: 70, scale: 0.94, rotateX: 10 });
        });
        gsap.set(dots[0], { color: "var(--color-fg)" });

        const tl = gsap.timeline({
          defaults: { ease: "power2.inOut", duration: 0.5 },
          scrollTrigger: {
            trigger: "[data-pin]",
            start: "top top",
            end: "+=220%",
            pin: true,
            scrub: 0.8,
            anticipatePin: 1,
            invalidateOnRefresh: true,
          },
        });

        scenes.forEach((scene, i) => {
          if (i === 0) return;
          const prev = scenes[i - 1];
          const at = i; // each step gets one "second" of the scrubbed timeline
          tl.to(part(prev, "text"), { y: -48 }, at)
            .to(part(prev, "visual"), { y: -60, scale: 0.96, rotateX: -8 }, at)
            .to(prev, { autoAlpha: 0 }, at)
            .to(scene, { autoAlpha: 1 }, at + 0.25)
            .to(part(scene, "text"), { y: 0 }, at + 0.25)
            .to(part(scene, "visual"), { y: 0, scale: 1, rotateX: 0 }, at + 0.25)
            .to(dots[i - 1], { color: "var(--color-muted)" }, at + 0.25)
            .to(dots[i], { color: "var(--color-fg)" }, at + 0.25);
        });
        tl.to("[data-progress]", { scaleX: 1, ease: "none", duration: tl.duration() + 0.5 }, 0);
      });
    },
    { scope: root },
  );

  return (
    <section ref={root} id="security" className="relative" aria-labelledby="security-title">
      <div
        data-pin
        className="relative flex flex-col justify-center overflow-hidden py-24 pinned:h-svh pinned:py-20"
      >
        <span className="spark right-[6%] top-28 hidden lg:block" aria-hidden="true">✦</span>
        <div className="page relative">
          <p className="eyebrow">03 · How it protects you</p>
          <h2 id="security-title" className="mt-5 max-w-4xl text-h2 text-fg">
            Three steps between your passwords and everyone else.
          </h2>

          {/* which step you're on (only shown with the pinned version) */}
          <div className="mt-8 hidden max-w-md pinned:block" aria-hidden="true">
            <ol className="label flex justify-between text-muted">
              {SCENES.map((scene, i) => (
                <li key={scene.step} data-step>
                  {i + 1}. {scene.step}
                </li>
              ))}
            </ol>
            <div className="mt-3 h-px bg-line-strong">
              <div data-progress className="h-full origin-left scale-x-0 bg-fg" />
            </div>
          </div>

          <div className="mt-12 grid gap-16 pinned:mt-10 pinned:gap-0">
            {SCENES.map(scene => (
              <article
                key={scene.step}
                data-scene
                className="grid items-center gap-8 lg:grid-cols-2 lg:gap-16 pinned:[grid-area:1/1]"
              >
                <div data-scene-text className="max-w-xl">
                  <h3 className="font-display text-4xl uppercase text-fg sm:text-5xl">{scene.title}</h3>
                  <p className="mt-4 text-lead text-muted">{scene.text}</p>
                </div>
                <div className="[perspective:1200px]">
                  <div data-scene-visual className="mx-auto w-full max-w-lg">
                    {scene.visual}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
