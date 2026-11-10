import { Reveal, SectionHeading } from "@/components/Reveal";
import { asset } from "@/lib/site";

const FACTS = [
  { value: "$0", label: "Free, with every feature included" },
  { value: "5,000+", label: "Logos and icons for your logins" },
  { value: "9", label: "Password managers you can import from" },
];

export default function About() {
  return (
    <section id="about" className="section-pad relative" aria-labelledby="about-title">
      <span className="spark left-[6%] top-24 hidden lg:block" aria-hidden="true">✦</span>
      <div className="page relative grid items-center gap-14 lg:grid-cols-[1.1fr_0.9fr] lg:gap-20">
        <div>
          <SectionHeading
            id="about-title"
            eyebrow="01 · What it is"
            title="One quiet place for every password."
            intro="HushKey remembers your logins so you don't have to. You remember one master password, and it unlocks the rest."
          />
          <Reveal className="mt-8 max-w-xl space-y-5 text-muted">
            <p data-reveal>
              Add a login, pick its logo, and it&apos;s saved in your vault. Usernames and passwords stay hidden until you
              ask to see them. When you copy one, HushKey clears it from your clipboard after 20 seconds.
            </p>
            <p data-reveal>
              Sign in on another computer with the same email and master password, and your logins come with you.
            </p>
          </Reveal>

          <Reveal as="ul" className="mt-12 grid gap-6 sm:grid-cols-3" stagger={0.1}>
            {FACTS.map(fact => (
              <li key={fact.label} data-reveal className="border-t border-line-strong pt-5">
                <span className="block font-display text-5xl text-fg">{fact.value}</span>
                <span className="label mt-3 block text-muted">{fact.label}</span>
              </li>
            ))}
          </Reveal>
        </div>

        {/* The real "Add a Login" window, as a picture */}
        <Reveal className="mx-auto w-full max-w-[25rem]">
          <div data-reveal className="overflow-hidden rounded-card border border-line-strong bg-surface shadow-card">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={asset("/shots/logos.webp")}
              alt="Adding a login in HushKey and choosing its logo from the Airlines and travel category."
              width={500}
              height={640}
              loading="lazy"
              decoding="async"
              className="block aspect-[500/640] w-full object-cover"
            />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
