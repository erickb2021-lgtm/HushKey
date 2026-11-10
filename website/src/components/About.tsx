import TiltedCard from "@/components/reactbits/TiltedCard";
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

        {/* The real "Add a Login" window. It tilts toward the cursor (React Bits TiltedCard). */}
        <Reveal className="mx-auto w-full max-w-[25rem]">
          <div data-reveal className="aspect-[500/640] w-full">
            <TiltedCard
              imageSrc={asset("/shots/logos.webp")}
              altText="Adding a login in HushKey and choosing its logo from the Airlines and travel category."
              containerWidth="100%"
              containerHeight="100%"
              imageWidth="100%"
              imageHeight="100%"
              radius={6}
              rotateAmplitude={9}
              scaleOnHover={1.03}
              glare={0.22}
              glareColor="#ffffff"
              shadow={0.6}
              showTooltip={false}
              flipOnClick={false}
              gyroscope={false}
              intro={false}
            />
          </div>
        </Reveal>
      </div>
    </section>
  );
}
