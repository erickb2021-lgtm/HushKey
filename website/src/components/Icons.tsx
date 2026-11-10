import type { SVGProps } from "react";

// Small inline SVG icons (no icon font, no emoji). All are decorative:
// the text next to them carries the meaning, so they're hidden from screen readers.

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Stroke({ size = 24, children, ...rest }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...rest}
    >
      {children}
    </svg>
  );
}

function Solid({ size = 24, children, ...rest }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false" {...rest}>
      {children}
    </svg>
  );
}

export const WindowsIcon = (p: IconProps) => (
  <Solid {...p}>
    <path d="M0 0h11.377v11.372H0Zm12.623 0H24v11.372H12.623ZM0 12.623h11.377V24H0Zm12.623 0H24V24H12.623Z" />
  </Solid>
);

export const AppleIcon = (p: IconProps) => (
  <Solid {...p}>
    <path d="M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701" />
  </Solid>
);

export const GitHubIcon = (p: IconProps) => (
  <Solid {...p}>
    <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
  </Solid>
);

export const LockIcon = (p: IconProps) => (
  <Stroke {...p}>
    <rect x="4.5" y="10.5" width="15" height="10.5" rx="2.5" />
    <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
    <path d="M12 14.5v2.5" />
  </Stroke>
);

export const SyncIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M20 11a8 8 0 0 0-14.3-4.9L4 8" />
    <path d="M4 4v4h4" />
    <path d="M4 13a8 8 0 0 0 14.3 4.9L20 16" />
    <path d="M20 20v-4h-4" />
  </Stroke>
);

export const DeviceIcon = (p: IconProps) => (
  <Stroke {...p}>
    <rect x="3" y="4" width="18" height="12" rx="2" />
    <path d="M8.5 20h7M12 16v4" />
    <path d="m9.5 10 1.8 1.8L14.8 8.3" />
  </Stroke>
);

export const GridIcon = (p: IconProps) => (
  <Stroke {...p}>
    <rect x="3.5" y="3.5" width="7" height="7" rx="1.8" />
    <rect x="13.5" y="3.5" width="7" height="7" rx="1.8" />
    <rect x="3.5" y="13.5" width="7" height="7" rx="1.8" />
    <circle cx="17" cy="17" r="3.5" />
  </Stroke>
);

export const HealthIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M12 3 4.5 6v5.5c0 4.5 3.1 8 7.5 9.5 4.4-1.5 7.5-5 7.5-9.5V6Z" />
    <path d="m8.8 12 2.2 2.2 4.2-4.4" />
  </Stroke>
);

export const PaletteIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M12 3a9 9 0 1 0 0 18c1.4 0 2-1 2-2 0-1.6-1-2 0-3.300.7-.9 2-.7 3.500-.7A3.500 3.500 0 0 0 21 11.500C21 6.800 17 3 12 3Z" />
    <circle cx="7.800" cy="11.500" r="1" />
    <circle cx="10.500" cy="7.500" r="1" />
    <circle cx="15" cy="7.800" r="1" />
  </Stroke>
);

export const ImportIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M12 3v11" />
    <path d="m7.500 10 4.500 4.500L16.500 10" />
    <path d="M4 16v2.500A2.500 2.500 0 0 0 6.500 21h11a2.500 2.500 0 0 0 2.500-2.500V16" />
  </Stroke>
);

export const UpdateIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M12 3v5M12 16v5M3 12h5M16 12h5" />
    <path d="m5.600 5.600 3.200 3.200M15.200 15.200l3.200 3.200M5.600 18.400l3.200-3.200M15.200 8.800l3.200-3.200" />
  </Stroke>
);

export const EyeOffIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M3 3l18 18" />
    <path d="M10.600 6.200A9.700 9.700 0 0 1 12 6c5 0 8.500 4 9.500 6-.4.900-1.300 2.200-2.600 3.400M6.300 7.700C4.400 9 3.100 10.800 2.500 12c1 2 4.500 6 9.500 6 1.500 0 2.800-.3 4-.9" />
    <path d="M9.900 9.900a3 3 0 0 0 4.200 4.200" />
  </Stroke>
);

export const CodeIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="m8 7-5 5 5 5M16 7l5 5-5 5M13.500 5l-3 14" />
  </Stroke>
);

export const SealIcon = (p: IconProps) => (
  <Stroke {...p}>
    <circle cx="12" cy="10" r="6" />
    <path d="m8.500 15-1.500 6 5-2.500 5 2.500-1.500-6" />
    <path d="m9.800 10 1.600 1.600 3-3.200" />
  </Stroke>
);

export const CheckIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="m5 12.500 4.500 4.500L19 7.500" />
  </Stroke>
);

export const ArrowIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Stroke>
);

export const PlusIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M12 5v14M5 12h14" />
  </Stroke>
);

export const CloseIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Stroke>
);

export const MenuIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Stroke>
);
