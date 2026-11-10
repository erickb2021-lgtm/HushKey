import DownloadButtons from "@/components/DownloadButtons";
import { AppleIcon, ArrowIcon, GitHubIcon, WindowsIcon } from "@/components/Icons";
import { Wordmark } from "@/components/Nav";
import { Reveal, SectionHeading } from "@/components/Reveal";
import { GITHUB_URL, ISSUES_URL, NAV_LINKS, RELEASES_URL } from "@/lib/site";

export default function Download() {
  return (
    <section id="download" className="section-pad relative overflow-hidden" aria-labelledby="download-title">
      <span className="spark left-[8%] top-24 hidden lg:block" aria-hidden="true">✦</span>
      <span className="spark right-[8%] top-24 hidden lg:block" aria-hidden="true">✦</span>

      <div className="page">
        <SectionHeading
          id="download-title"
          eyebrow="08 · Download"
          title="Get HushKey."
          intro="Free for Windows and Mac. After the first install, it updates itself."
          align="center"
        />
        <Reveal className="mt-10 flex justify-center">
          <div data-reveal>
            <DownloadButtons className="justify-center" />
          </div>
        </Reveal>

        <Reveal className="mx-auto mt-16 grid max-w-4xl gap-5 md:grid-cols-2" stagger={0.1}>
          <div data-reveal className="panel p-6 sm:p-7">
            <h3 className="flex items-center gap-3 text-lg font-bold text-fg">
              <WindowsIcon size={18} />
              Windows, first time only
            </h3>
            <ol className="mt-4 list-decimal space-y-2 pl-5 text-[0.9375rem] text-muted marker:font-bold marker:text-fg">
              <li>
                If Edge says the file “isn&apos;t commonly downloaded”, choose <strong className="text-fg">Keep</strong>, then{" "}
                <strong className="text-fg">Keep anyway</strong>.
              </li>
              <li>
                On “Windows protected your PC”, click <strong className="text-fg">More info</strong>, then{" "}
                <strong className="text-fg">Run anyway</strong>.
              </li>
              <li>Follow the installer. HushKey opens when it&apos;s done.</li>
            </ol>
          </div>
          <div data-reveal className="panel p-6 sm:p-7">
            <h3 className="flex items-center gap-3 text-lg font-bold text-fg">
              <AppleIcon size={19} />
              Mac, first time only
            </h3>
            <ol className="mt-4 list-decimal space-y-2 pl-5 text-[0.9375rem] text-muted marker:font-bold marker:text-fg">
              <li>
                Unzip the download and drag <strong className="text-fg">HushKey</strong> into Applications.
              </li>
              <li>
                Open it. When the warning appears, click <strong className="text-fg">Done</strong>.
              </li>
              <li>
                In <strong className="text-fg">System Settings → Privacy &amp; Security</strong>, click{" "}
                <strong className="text-fg">Open Anyway</strong>.
              </li>
            </ol>
          </div>
        </Reveal>

        {/* Contact */}
        <Reveal className="mx-auto mt-16 max-w-2xl text-center">
          <div data-reveal>
            <h3 className="font-display text-4xl uppercase text-fg">Questions, or found a bug?</h3>
            <p className="mt-3 text-muted">
              HushKey is built in the open. Ask a question or report a problem on GitHub.
            </p>
            <a href={ISSUES_URL} className="btn btn-ghost mt-6">
              <GitHubIcon size={18} />
              Open an issue on GitHub
              <ArrowIcon size={18} />
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="page flex flex-col gap-8 py-10 md:flex-row md:items-center md:justify-between">
        <div>
          <Wordmark size={24} />
          <p className="label mt-3 text-muted">A personal project · Free for Windows and Mac</p>
        </div>
        <nav aria-label="Footer">
          <ul className="label flex flex-wrap gap-x-6 gap-y-1">
            {[...NAV_LINKS, { href: RELEASES_URL, label: "Release notes" }, { href: GITHUB_URL, label: "GitHub" }].map(link => (
              <li key={link.href}>
                <a href={link.href} className="flex min-h-11 min-w-11 items-center text-muted transition-colors duration-200 hover:text-fg">
                  {link.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
