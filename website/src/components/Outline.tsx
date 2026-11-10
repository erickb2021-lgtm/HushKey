/**
 * The site's one motif: "HUSHKEY" repeated as white outline letters on black,
 * like the title rows of a film poster. It's plain text, drawn once by the
 * browser and never redrawn, so it costs nothing while the page scrolls.
 */

// joined with no-break spaces, so the row can never wrap into several lines
const WORDS = Array.from({ length: 10 }, () => "HUSHKEY").join("  ");

/** One full-width row of outline letters. `shift` nudges it sideways so stacked rows don't line up. */
export function OutlineRow({
  shift = 0,
  dim = false,
  small = false,
  className = "",
}: {
  shift?: number;
  dim?: boolean;
  /** Section-divider size instead of hero size, and centred so both ends are cut evenly. */
  small?: boolean;
  className?: string;
}) {
  return (
    <div
      className={`pointer-events-none flex w-full shrink-0 select-none overflow-hidden ${small ? "justify-center" : ""} ${className}`}
      aria-hidden="true"
    >
      <p
        className={`${dim ? "outline-text-dim" : "outline-text"} ${small ? "text-band" : "text-hero"} font-display uppercase leading-none whitespace-nowrap`}
        style={shift ? { transform: `translateX(${shift}em)` } : undefined}
      >
        {WORDS}
      </p>
    </div>
  );
}

/**
 * A band of outline letters between two sections: a hairline above and below,
 * a little breathing room, one row of letters. Used three times down the page
 * so the hero's look carries through the whole site.
 */
export function OutlineBand({ shift = 0, className = "" }: { shift?: number; className?: string }) {
  return (
    <div className={`border-y border-line bg-black py-5 sm:py-7 ${className}`} aria-hidden="true">
      <OutlineRow shift={shift} small />
    </div>
  );
}
