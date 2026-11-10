# HushKey website

The website for HushKey, built with Next.js (App Router) and Tailwind. It exports to plain
static files, so it can be hosted free on GitHub Pages or any web host.

## Run it on your computer

```bash
npm install
npm run dev
```

Then open http://localhost:3000.

## Build the files to upload

```bash
npm run build
```

The finished site is in the `out` folder. Upload that folder to your host.
If the site lives under a sub-path such as `https://you.github.io/HushKey/`, build with
`NEXT_PUBLIC_BASE_PATH=/HushKey npm run build` instead.

## Where things are

- `src/lib/site.ts` — the GitHub repo, download links and menu links. Everything that repeats on the
  page lives here.
- `src/app/globals.css` — the design tokens (colors, type sizes, radius, shadows) and shared styles.
- `src/components/` — one file per section: `Hero`, `About`, `Features`, `Chapters` (how it protects you),
  `Gallery` (screenshots), `Trust`, `Pricing`, `Faq`, `Download` (with the footer), plus `Nav`.
- `src/components/Outline.tsx` — the outline "HUSHKEY" rows used in the hero and as bands between sections.
- `src/components/reactbits/` — components from [React Bits](https://reactbits.dev) (MIT), copied into the
  project so they can be edited.
- `public/shots/` — real screenshots of the app, taken with a made-up demo vault.

## The look

Black, with "HUSHKEY" repeated in white outline letters: in the hero and in three bands down the page.
It's plain text, so it costs nothing to scroll past. There is no 3D scene and no WebGL anywhere on the
site any more: the earlier glass-cube hero and the 3D screenshot carousel redrew themselves constantly and
made the page stutter on ordinary computers.
