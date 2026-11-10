import DownloadButtons from "@/components/DownloadButtons";
import LatestVersion from "@/components/LatestVersion";
import { OutlineRow } from "@/components/Outline";

/**
 * The hero: a black stage filled with rows of outline "HUSHKEY", and the solid
 * name in the middle. No 3D, no scripts, nothing that runs while you scroll:
 * it's text, so it's drawn once and stays sharp on any screen. The headline's
 * entrance is one short CSS animation (see `.rise` in globals.css). Below the
 * stage sit the real words and the download buttons.
 */
export default function Hero() {
  return (
    <section id="top" className="relative isolate overflow-hidden bg-black">
      {/* ---- the stage ---- */}
      <div className="hero-bg relative flex h-[calc(100svh-4rem)] min-h-[34rem] w-full flex-col items-center justify-center overflow-hidden pt-16">
        {/* rows above: brighter nearer the name */}
        <OutlineRow shift={-0.9} dim className="hidden md:block" />
        <OutlineRow shift={0.4} dim />
        <OutlineRow shift={-0.3} />

        <h1 className="rise text-grain relative z-10 -my-[0.1em] px-4 text-center text-hero">Hush Key</h1>

        {/* rows below */}
        <OutlineRow shift={0.6} />
        <OutlineRow shift={-0.5} dim />
        <OutlineRow shift={0.2} dim className="hidden md:block" />

        {/* ✦ sparkles, like the corners of a poster */}
        <span className="spark left-[6%] top-28" aria-hidden="true">✦</span>
        <span className="spark right-[6%] top-28" aria-hidden="true">✦</span>
        <span className="spark bottom-20 left-[6%]" aria-hidden="true">✦</span>
        <span className="spark bottom-20 right-[6%]" aria-hidden="true">✦</span>

        {/* corner labels */}
        <div className="page label pointer-events-none absolute inset-x-0 top-24 flex justify-between text-muted">
          <span>Free · Open source</span>
          <span>Windows · Mac</span>
        </div>
        <div className="page label pointer-events-none absolute inset-x-0 bottom-6 flex items-end justify-between text-muted">
          <span className="pointer-events-auto">
            <LatestVersion />
          </span>
          <span className="hidden sm:inline">Scroll ↓</span>
        </div>
      </div>

      {/* ---- the words and the buttons ---- */}
      <div className="page relative grid gap-8 border-t border-line bg-bg py-10 md:grid-cols-[1.2fr_1fr] md:items-center md:py-14">
        <div>
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
