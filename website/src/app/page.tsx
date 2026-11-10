import About from "@/components/About";
import Chapters from "@/components/Chapters";
import Download, { Footer } from "@/components/Download";
import Faq from "@/components/Faq";
import Features from "@/components/Features";
import Gallery from "@/components/Gallery";
import Hero from "@/components/Hero";
import Nav from "@/components/Nav";
import { OutlineBand } from "@/components/Outline";
import Pricing from "@/components/Pricing";
import Trust from "@/components/Trust";

export default function Home() {
  return (
    <>
      <Nav />
      <main id="main">
        <Hero />
        <About />
        <OutlineBand shift={0.4} />
        <Features />
        <Chapters />
        <Gallery />
        <OutlineBand shift={-0.7} />
        <Trust />
        <Pricing />
        <Faq />
        <OutlineBand shift={0.2} />
        <Download />
      </main>
      <Footer />
    </>
  );
}
