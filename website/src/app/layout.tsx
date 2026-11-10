import type { Metadata, Viewport } from "next";
import { Anton, DM_Sans, JetBrains_Mono } from "next/font/google";
import SmoothScroll from "@/components/SmoothScroll";
import "./globals.css";

const display = Anton({
  variable: "--font-anton",
  subsets: ["latin"],
  weight: "400",
  display: "swap",
});

const mono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["500", "700"],
  display: "swap",
});

const body = DM_Sans({
  variable: "--font-dm-sans",
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "HushKey: a free password manager for Windows and Mac",
  description:
    "HushKey keeps your passwords encrypted on your own computer and syncs them between your computers. Free for Windows and Mac.",
  openGraph: {
    title: "HushKey: your passwords, kept hush",
    description:
      "A free password manager for Windows and Mac. Your logins are encrypted on your computer, and only you can open them.",
    type: "website",
  },
};

export const viewport: Viewport = {
  themeColor: "#050506",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${mono.variable} ${body.variable} antialiased`}>
      <body>
        <a
          href="#main"
          className="btn btn-primary fixed left-4 top-4 z-[100] -translate-y-24 focus-visible:translate-y-0"
        >
          Skip to content
        </a>
        <SmoothScroll>{children}</SmoothScroll>
        <div className="grain" aria-hidden="true" />
      </body>
    </html>
  );
}
