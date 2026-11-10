import type { ReactNode } from "react";
import { PlusIcon } from "@/components/Icons";
import { Reveal, SectionHeading } from "@/components/Reveal";

const QUESTIONS: { q: string; a: ReactNode }[] = [
  {
    q: "Is HushKey really free?",
    a: "Yes. There's one version, it has every feature, and it costs nothing. There are no ads.",
  },
  {
    q: "Can HushKey, or anyone else, read my passwords?",
    a: "No. Your logins are encrypted on your computer with a key made from your master password, and that password never leaves your computer. Sync only uploads the encrypted data, which the server can't read.",
  },
  {
    q: "What happens if I forget my master password?",
    a: "On the sign-in screen, click “Forgot master password?” and follow the steps. Nothing changes until you click “Reset password”. Because the reset goes through your email, protect your email account with 2-step verification.",
  },
  {
    q: "Why does my computer warn me the first time I open it?",
    a: (
      <>
        HushKey isn&apos;t signed with a paid certificate yet, so Windows and macOS warn you once. It doesn&apos;t mean there&apos;s a
        virus. On Windows, click <strong>More info</strong>, then <strong>Run anyway</strong>. On a Mac, open{" "}
        <strong>System Settings → Privacy &amp; Security</strong> and click <strong>Open Anyway</strong>.
      </>
    ),
  },
  {
    q: "Which computers does it run on?",
    a: "Windows 10 and 11, and Macs with Apple Silicon (M1 or newer). There's no phone app.",
  },
  {
    q: "How do I use it on a second computer?",
    a: "Install HushKey there and sign in with the same email and master password. Your logins come with you. In Settings you can see every computer that has opened your vault, and remove one you don't recognize.",
  },
  {
    q: "Can I bring my passwords from another password manager?",
    a: "Yes. HushKey imports from Google, Chrome, Bitwarden, LastPass, 1Password, Apple Passwords, Edge, Firefox and Dashlane. You can also export to an encrypted backup or a CSV file.",
  },
  {
    q: "Do I have to update it myself?",
    a: "No. After the first install, HushKey checks for new versions and updates itself.",
  },
];

/** Questions open and close with the browser's own <details>, so they work with a keyboard and without JavaScript. */
export default function Faq() {
  return (
    <section id="faq" className="section-pad relative" aria-labelledby="faq-title">
      <div className="page grid gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
        <SectionHeading id="faq-title" eyebrow="07 · FAQ" title="Questions people ask first." />

        <Reveal className="border-t border-line" stagger={0.05}>
          {QUESTIONS.map(item => (
            <details key={item.q} data-reveal className="group border-b border-line">
              <summary className="flex min-h-16 cursor-pointer items-center justify-between gap-6 py-4 text-lg font-bold text-fg transition-colors duration-200 hover:text-muted">
                {item.q}
                <span className="faq-mark flex size-9 shrink-0 items-center justify-center rounded-control border border-line-strong text-fg transition-transform duration-300 ease-out">
                  <PlusIcon size={18} />
                </span>
              </summary>
              <p className="max-w-2xl pb-6 pr-12 text-muted">{item.a}</p>
            </details>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
