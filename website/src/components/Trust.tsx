import type { ReactNode } from "react";
import { CodeIcon, EyeOffIcon, LockIcon, SealIcon, SyncIcon } from "@/components/Icons";
import { Reveal, SectionHeading } from "@/components/Reveal";
import { GITHUB_URL } from "@/lib/site";

// This section stands where customer quotes would normally go. HushKey has no
// published reviews yet, so it lists checkable facts instead of invented praise.
// When you have real reviews (with permission to quote them), add them here.

const PROMISES: { icon: ReactNode; title: string; text: string }[] = [
  {
    icon: <LockIcon />,
    title: "Only you can read your vault",
    text: "Your logins are encrypted on your computer with a key made from your master password (PBKDF2-SHA256, 600,000 rounds).",
  },
  {
    icon: <SyncIcon />,
    title: "Sync is zero-knowledge",
    text: "The server only ever stores encrypted data, and every download is tamper-checked.",
  },
  {
    icon: <EyeOffIcon />,
    title: "The leak check is private",
    text: "It sends only the first 5 characters of a scrambled version of each password, so nobody learns your passwords. You can turn it off.",
  },
  {
    icon: <SealIcon />,
    title: "A tamper seal on your vault",
    text: "If anyone changes your vault file, HushKey refuses to open it and warns you.",
  },
  {
    icon: <CodeIcon />,
    title: "Built in public",
    text: "The code is on GitHub. Every download is built there from that code and comes with a SHA-256 fingerprint.",
  },
];

const LIMITS = [
  "HushKey is a personal project. It hasn't had an outside security audit.",
  "A long master password is your best protection. Four or more random words works well.",
  "Someone with your vault file and your email could reset your master password, so protect your email with 2-step verification.",
  "Nothing can protect you from malware that's already on your computer.",
];

export default function Trust() {
  return (
    <section id="trust" className="section-pad relative" aria-labelledby="trust-title">
      <div className="page grid gap-14 lg:grid-cols-[0.85fr_1.15fr] lg:gap-20">
        <div className="lg:sticky lg:top-28 lg:self-start">
          <SectionHeading
            id="trust-title"
            eyebrow="05 · Why trust it"
            title="Don't take our word for it. Check."
            intro="A password manager asks for a lot of trust. Here is exactly what HushKey does with your data, and what it can't promise."
          />
          <Reveal className="mt-8">
            <a
              data-reveal
              href={GITHUB_URL}
              className="label inline-flex min-h-11 items-center gap-2 text-fg underline decoration-line-strong underline-offset-4 transition-colors duration-200 hover:decoration-fg"
            >
              Read the code on GitHub
            </a>
          </Reveal>
        </div>

        <div>
          <Reveal as="ul" className="divide-y divide-line border-y border-line" stagger={0.07}>
            {PROMISES.map(item => (
              <li key={item.title} data-reveal className="flex gap-5 py-7">
                <span className="mt-0.5 flex size-11 shrink-0 items-center justify-center rounded-control border border-line text-fg">
                  {item.icon}
                </span>
                <div>
                  <h3 className="text-lg font-bold text-fg">{item.title}</h3>
                  <p className="mt-2 text-muted">{item.text}</p>
                </div>
              </li>
            ))}
          </Reveal>

          <Reveal className="mt-10">
            <div data-reveal className="rounded-card border border-key/40 p-6 sm:p-7">
              <h3 className="label text-key">The honest limits</h3>
              <ul className="mt-4 space-y-3 text-[0.9375rem] text-fg/85">
                {LIMITS.map(limit => (
                  <li key={limit} className="flex gap-3">
                    <span className="mt-[0.6em] size-1.5 shrink-0 rounded-full bg-key" aria-hidden="true" />
                    {limit}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
