import SpotlightCard from "@/components/reactbits/SpotlightCard";
import DownloadButtons from "@/components/DownloadButtons";
import { CheckIcon } from "@/components/Icons";
import { Reveal, SectionHeading } from "@/components/Reveal";

const INCLUDED = [
  "Every feature on this page",
  "Sync between your computers",
  "15 backgrounds, 21 colors and 4 fonts",
  "Import from 9 other password managers",
  "Automatic updates",
  "No ads",
];

export default function Pricing() {
  return (
    <section id="pricing" className="section-pad relative" aria-labelledby="pricing-title">
      <div className="page">
        <SectionHeading
          id="pricing-title"
          eyebrow="06 · Pricing"
          title="Free. That is the price list."
          intro="There's one version of HushKey, and it costs nothing."
          align="center"
        />

        <Reveal className="mx-auto mt-14 max-w-3xl">
          <div data-reveal>
            <SpotlightCard
              className="!rounded-card !p-7 sm:!p-10"
              spotlightColor="#eceae4"
              intensity={0.1}
              spotlightSize={380}
              borderGlow={0.9}
              ambient
              style={
                {
                  "--spotlight-card-surface": "var(--color-surface)",
                  "--spotlight-card-border": "var(--color-line-strong)",
                  "--spotlight-card-shadow": "var(--shadow-card)",
                } as React.CSSProperties
              }
            >
              <div className="grid gap-10 sm:grid-cols-[auto_1fr] sm:gap-14">
                <div>
                  <h3 className="label text-muted">HushKey</h3>
                  <p className="mt-3 font-display text-8xl leading-none text-fg">$0</p>
                  <p className="label mt-4 text-muted">For Windows and Mac</p>
                </div>
                <ul className="grid gap-3.5 self-center sm:grid-cols-2">
                  {INCLUDED.map(item => (
                    <li key={item} className="flex items-start gap-3 text-fg">
                      <span className="mt-0.5 text-fg">
                        <CheckIcon size={20} />
                      </span>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <DownloadButtons className="mt-10 border-t border-line pt-8" />
            </SpotlightCard>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
