"use client";

import { useEffect, useState } from "react";
import { RELEASES_URL, REPO } from "@/lib/site";

/**
 * Shows the newest release number (e.g. "v2.0.19"), read from GitHub's public
 * release page when the visitor opens the site, so it's never out of date.
 * If GitHub can't be reached it just says "Release notes".
 */
export default function LatestVersion({ className = "" }: { className?: string }) {
  const [tag, setTag] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch(`https://api.github.com/repos/${REPO}/releases/latest`, { signal: controller.signal })
      .then(r => (r.ok ? r.json() : null))
      .then(data => {
        const name = typeof data?.tag_name === "string" ? data.tag_name : "";
        if (/^v?\d+(\.\d+){1,3}$/.test(name)) setTag(name.startsWith("v") ? name : `v${name}`);
      })
      .catch(() => {});
    return () => controller.abort();
  }, []);

  return (
    <a
      href={RELEASES_URL}
      className={`inline-flex min-h-11 items-center underline decoration-line-strong underline-offset-4 transition-colors duration-200 hover:text-fg ${className}`}
    >
      {tag ? `Latest ${tag}` : "Release notes"}
    </a>
  );
}
