import { AppleIcon, WindowsIcon } from "@/components/Icons";
import { DOWNLOAD_MAC, DOWNLOAD_WINDOWS } from "@/lib/site";

/** The two download buttons. They always fetch the newest release from GitHub. */
export default function DownloadButtons({ className = "" }: { className?: string }) {
  return (
    <div className={`flex flex-col gap-3 sm:flex-row sm:flex-wrap ${className}`}>
      <a className="btn btn-primary" href={DOWNLOAD_WINDOWS} data-hero-cta>
        <WindowsIcon size={18} />
        Download for Windows
      </a>
      <a className="btn btn-ghost" href={DOWNLOAD_MAC} data-hero-cta>
        <AppleIcon size={19} />
        Download for Mac
      </a>
    </div>
  );
}
