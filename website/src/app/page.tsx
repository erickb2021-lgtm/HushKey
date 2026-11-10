import About from "@/components/About";
import Chapters from "@/components/Chapters";
import Download, { Footer } from "@/components/Download";
import Faq from "@/components/Faq";
import Features from "@/components/Features";
import Gallery from "@/components/Gallery";
import Hero from "@/components/Hero";
import Nav from "@/components/Nav";
import Pricing from "@/components/Pricing";
import Trust from "@/components/Trust";

export default function Home() {
  return (
    <>
      <Nav />
      <main id="main">
        <Hero />
        <About />
        <Features />
        <Chapters />
        <Gallery />
        <Trust />
        <Pricing />
        <Faq />
        <Download />
      </main>
      <Footer />
    </>
  );
}
