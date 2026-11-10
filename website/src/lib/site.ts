// Everything about HushKey that the page repeats lives here, so a link or a
// name only has to change in one place.

export const REPO = "erickb2021-lgtm/HushKey";
export const GITHUB_URL = `https://github.com/${REPO}`;
export const RELEASES_URL = `${GITHUB_URL}/releases`;
export const ISSUES_URL = `${GITHUB_URL}/issues`;

// These always fetch the newest release, so the site never needs editing when a new version ships.
export const DOWNLOAD_WINDOWS = `${RELEASES_URL}/latest/download/HushKey-Windows.exe`;
export const DOWNLOAD_MAC = `${RELEASES_URL}/latest/download/HushKey-Mac.zip`;

/** Path to a file in /public that also works when the site is hosted under a sub-path. */
export const asset = (path: string) => `${process.env.NEXT_PUBLIC_BASE_PATH ?? ""}${path}`;

export const NAV_LINKS = [
  { href: "#features", label: "Features" },
  { href: "#security", label: "Security" },
  { href: "#screens", label: "Screens" },
  { href: "#pricing", label: "Pricing" },
  { href: "#faq", label: "FAQ" },
];
