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

- `src/lib/site.ts` — the GitHub repo, download links, menu links and the **Spline scene link**.
  Everything that repeats on the page lives here.
- `src/app/globals.css` — the design tokens (colors, type sizes, radius, shadows) and shared styles.
- `src/components/` — one file per section: `Hero`, `About`, `Features`, `Chapters` (how it protects you),
  `Gallery` (screenshots), `Trust`, `Pricing`, `Faq`, `Download` (with the footer), plus `Nav`.
- `src/components/SplineHero.tsx` — loads the 3D hero scene on desktops and hides the template's own
  menu and labels.
- `src/components/reactbits/` — components from [React Bits](https://reactbits.dev) (MIT), copied into the
  project so they can be edited.
- `public/shots/` — real screenshots of the app, taken with a made-up demo vault.

## The 3D hero scene

The hero is a Spline scene (`SPLINE_SCENE` in `src/lib/site.ts`). It only loads on desktops with a mouse
and no "reduce motion" setting; everyone else sees the same composition drawn in HTML. To change the
scene, edit it in Spline and export again; the link stays the same.
