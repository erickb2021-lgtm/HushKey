"use client";

import { useEffect, useState } from "react";
import { CloseIcon, MenuIcon } from "@/components/Icons";
import { asset, NAV_LINKS } from "@/lib/site";

export function Wordmark({ size = 26 }: { size?: number }) {
  return (
    <span className="inline-flex items-center gap-2.5 font-display text-2xl uppercase tracking-wide">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={asset("/logo.png")} alt="" width={size} height={size} />
      <span>
        <span className="text-accent">Hush</span>
        <span className="text-key">Key</span>
      </span>
    </span>
  );
}

export default function Nav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-50 transition-[background-color,border-color] duration-300 ${
        scrolled || open ? "border-b border-line bg-bg/95" : "border-b border-transparent"
      }`}
    >
      <nav className="page flex h-16 items-center justify-between" aria-label="Main">
        <a href="#top" className="flex min-h-11 items-center" aria-label="HushKey, back to top">
          <Wordmark />
        </a>

        <ul className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map(link => (
            <li key={link.href}>
              <a
                href={link.href}
                className="label flex min-h-11 items-center px-3.5 text-muted transition-colors duration-200 hover:text-fg"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2">
          <a href="#download" className="btn btn-primary hidden min-h-11 px-4 py-2 shadow-none sm:inline-flex">
            Download
          </a>
          <button
            type="button"
            className="flex size-11 items-center justify-center text-fg md:hidden"
            aria-expanded={open}
            aria-controls="mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            onClick={() => setOpen(v => !v)}
          >
            {open ? <CloseIcon /> : <MenuIcon />}
          </button>
        </div>
      </nav>

      {open && (
        <div id="mobile-menu" className="page border-t border-line pb-5 md:hidden">
          <ul className="flex flex-col py-2">
            {NAV_LINKS.map(link => (
              <li key={link.href}>
                <a
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="flex min-h-12 items-center font-display text-2xl uppercase text-fg"
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
          <a href="#download" onClick={() => setOpen(false)} className="btn btn-primary w-full">
            Download
          </a>
        </div>
      )}
    </header>
  );
}
