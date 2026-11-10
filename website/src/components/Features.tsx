import type { ReactNode } from "react";
import SpotlightCard from "@/components/reactbits/SpotlightCard";
import {
  DeviceIcon,
  GridIcon,
  HealthIcon,
  ImportIcon,
  LockIcon,
  PaletteIcon,
  SyncIcon,
  UpdateIcon,
} from "@/components/Icons";
import { Reveal, SectionHeading } from "@/components/Reveal";

const FEATURES: { icon: ReactNode; title: string; text: string }[] = [
  {
    icon: <LockIcon />,
    title: "Encrypted on your computer",
    text: "Your logins are locked with a key made from your master password. That password never leaves your computer.",
  },
  {
    icon: <SyncIcon />,
    title: "Sync between your computers",
    text: "Sign in on another computer and your logins are there. Only encrypted data is ever uploaded.",
  },
  {
    icon: <DeviceIcon />,
    title: "Remember this device",
    text: "On a computer you trust, HushKey can open straight to your vault for 30 days.",
  },
  {
    icon: <GridIcon />,
    title: "A logo for every login",
    text: "Over 5,000 logos and icons for banks, airlines, stores, streaming, games and more. Or use your own picture.",
  },
  {
    icon: <HealthIcon />,
    title: "Security tips",
    text: "A vault score and optional tips point out weak, reused or leaked passwords.",
  },
  {
    icon: <PaletteIcon />,
    title: "Make it yours",
    text: "Light and dark mode, 21 accent colors, 4 fonts, a compact view and 15 pixel-art backgrounds.",
  },
  {
    icon: <ImportIcon />,
    title: "Bring your passwords",
    text: "Import from Google, Chrome, Bitwarden, LastPass, 1Password, Apple Passwords, Edge, Firefox or Dashlane.",
  },
  {
    icon: <UpdateIcon />,
    title: "Updates itself",
    text: "HushKey checks for new versions while it's open and installs them for you.",
  },
];

export default function Features() {
  return (
    <section id="features" className="section-pad relative" aria-labelledby="features-title">
      <div className="page">
        <SectionHeading
          id="features-title"
          eyebrow="02 · Features"
          title="Everything a password manager should do."
          intro="No paid tier and no locked features. This is all of it."
        />

        <Reveal as="ul" className="mt-14 grid gap-px border border-line bg-line sm:grid-cols-2 lg:mt-16 xl:grid-cols-4" stagger={0.06}>
          {FEATURES.map(feature => (
            <li key={feature.title} data-reveal className="h-full">
              {/* React Bits SpotlightCard, relit in HushKey green */}
              <SpotlightCard
                className="h-full !rounded-none !p-6"
                spotlightColor="#eceae4"
                intensity={0.1}
                spotlightSize={260}
                borderGlow={0.8}
                proximity={0}
                style={
                  {
                    "--spotlight-card-surface": "var(--color-bg)",
                    "--spotlight-card-border": "transparent",
                    "--spotlight-card-shadow": "none",
                    borderRadius: 0,
                  } as React.CSSProperties
                }
              >
                <span className="flex size-11 items-center justify-center rounded-control border border-line text-fg">
                  {feature.icon}
                </span>
                <h3 className="mt-5 text-lg font-bold text-fg">{feature.title}</h3>
                <p className="mt-2.5 text-[0.9375rem] leading-relaxed text-muted">{feature.text}</p>
              </SpotlightCard>
            </li>
          ))}
        </Reveal>
      </div>
    </section>
  );
}
