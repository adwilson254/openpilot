/* Duotone icon set: 1.5px rounded stroke, 24x24 viewBox. The secondary tone
   (.i2) renders in a dimmed stroke; the active state elevates it via CSS.
   Every icon takes size + standard SVG props; decorative usage passes
   aria-hidden, semantic usage gets a title/aria-label at the call site.
   The maneuverIcon lookup is a deliberate non-component export (unit-tested);
   fast-refresh granularity is a fine trade for one shared module. */
/* eslint-disable react-refresh/only-export-components */

const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.5,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
};

function I({ size = 24, children, ...props }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" {...base} {...props}>
      {children}
    </svg>
  );
}

/* navigation dock */
export const IconDrive = (p) => (
  <I {...p}><circle className="i2" cx="12" cy="12" r="8.5" /><path d="M12 12 L15.6 8.4" /><path d="M7.6 12 L8.7 12 M15.3 12 L16.4 12 M12 15.3 L12 16.4" opacity="0.6" /></I>
);
export const IconMap = (p) => (
  <I {...p}><path className="i2" d="M9 4.5 L4 6.5 L4 19.5 L9 17.5 L15 19.5 L20 17.5 L20 4.5 L15 6.5 Z" /><path d="M9 4.5 L9 17.5 M15 6.5 L15 19.5" /></I>
);
export const IconEnergy = (p) => (
  <I {...p}><path className="i2" d="M13.5 2.5 L6 13 L11 13 L10.5 21.5 L18 11 L13 11 Z" /></I>
);
export const IconTruck = (p) => (
  <I {...p}><path className="i2" d="M3.5 13 L5 8.5 A2 2 0 0 1 6.9 7 L15.5 7 L19 10.5 L20.5 11 A1.6 1.6 0 0 1 21.5 12.5 L21.5 15 L19.5 15" /><circle cx="7.8" cy="15.6" r="2.1" /><circle cx="16.4" cy="15.6" r="2.1" /><path d="M9.9 15.5 L14.3 15.5" /></I>
);
export const IconMore = (p) => (
  <I {...p}><path className="i2" d="M4.5 7.5 L19.5 7.5" /><path d="M4.5 12 L19.5 12 M4.5 16.5 L13.5 16.5" /></I>
);

/* status + controls */
export const IconGear = (p) => (
  <I {...p}><circle cx="12" cy="12" r="3.2" /><path className="i2" d="M12 3.6 L12 6 M12 18 L12 20.4 M3.6 12 L6 12 M18 12 L20.4 12 M6.1 6.1 L7.8 7.8 M16.2 16.2 L17.9 17.9 M17.9 6.1 L16.2 7.8 M7.8 16.2 L6.1 17.9" /></I>
);
export const IconPulse = (p) => (
  <I {...p}><path d="M3.5 13 L8.5 13 L10.5 7 L13.5 17 L15.5 13 L20.5 13" /></I>
);
export const IconRecenter = (p) => (
  <I {...p}><circle className="i2" cx="12" cy="12" r="7.5" /><path d="M12 2.5 L12 5.5 M12 18.5 L12 21.5 M2.5 12 L5.5 12 M18.5 12 L21.5 12" /><circle cx="12" cy="12" r="1.6" fill="currentColor" stroke="none" /></I>
);
export const IconPlus = (p) => <I {...p}><path d="M12 5.5 L12 18.5 M5.5 12 L18.5 12" /></I>;
export const IconMinus = (p) => <I {...p}><path d="M5.5 12 L18.5 12" /></I>;
export const IconClose = (p) => <I {...p}><path d="M6.5 6.5 L17.5 17.5 M17.5 6.5 L6.5 17.5" /></I>;
export const IconWarn = (p) => (
  <I {...p}><path className="i2" d="M12 3.4 L21.4 19.6 L2.6 19.6 Z" /><path d="M12 9.5 L12 14" /><circle cx="12" cy="16.7" r="0.4" fill="currentColor" /></I>
);
export const IconPin = (p) => (
  <I {...p}><path className="i2" d="M12 21 C12 21 5.5 14.8 5.5 10 A6.5 6.5 0 0 1 18.5 10 C18.5 14.8 12 21 12 21 Z" /><circle cx="12" cy="10" r="2.4" /></I>
);
export const IconClock = (p) => (
  <I {...p}><circle className="i2" cx="12" cy="12" r="8.5" /><path d="M12 7.5 L12 12 L15 13.8" /></I>
);
export const IconChevronR = (p) => <I {...p}><path d="M9 5.5 L15.5 12 L9 18.5" /></I>;

/* "more" sheet destinations */
export const IconCamp = (p) => (
  <I {...p}><path className="i2" d="M12 4 L20 20 L4 20 Z" /><path d="M12 11 C10.5 13.5 10.8 15.4 12 16.8 C13.2 15.4 13.5 13.5 12 11 Z" /></I>
);
export const IconDrives = (p) => (
  <I {...p}><path className="i2" d="M6 20 C6 12 18 12 18 4" /><path d="M6 20 L6 19 M6 16.5 L6 15.5 M17.4 8.5 L17.8 7.5 M18 4.8 L18 4" opacity="0.65" /><circle cx="6" cy="20" r="1.6" /><circle cx="18" cy="4" r="1.6" /></I>
);
export const IconDevice = (p) => (
  <I {...p}><rect className="i2" x="4" y="5" width="16" height="12" rx="2.5" /><path d="M9.5 20.5 L14.5 20.5 M8 9 L11 9 M8 12 L13 12" /></I>
);
export const IconSignals = (p) => (
  <I {...p}><path className="i2" d="M4 19.5 L20 19.5" /><path d="M5.5 15.5 L8.5 10.5 L11.5 13.5 L15 6.5 L18.5 11" /></I>
);
export const IconSettings = (p) => (
  <I {...p}><path className="i2" d="M5 8 L19 8 M5 16 L19 16" /><circle cx="9.5" cy="8" r="2" /><circle cx="14.5" cy="16" r="2" /></I>
);
export const IconInfo = (p) => (
  <I {...p}><circle className="i2" cx="12" cy="12" r="8.5" /><path d="M12 11 L12 16" /><circle cx="12" cy="8" r="0.5" fill="currentColor" /></I>
);

/* maneuver arrows (Valhalla type buckets) */
export const IconTurnRight = (p) => (
  <I {...p}><path d="M6 21 L6 10 A3.5 3.5 0 0 1 9.5 6.5 L17 6.5" /><path d="M13.5 2.8 L17.4 6.5 L13.5 10.2" /></I>
);
export const IconTurnLeft = (p) => (
  <I {...p}><path d="M18 21 L18 10 A3.5 3.5 0 0 0 14.5 6.5 L7 6.5" /><path d="M10.5 2.8 L6.6 6.5 L10.5 10.2" /></I>
);
export const IconStraight = (p) => (
  <I {...p}><path d="M12 21 L12 5" /><path d="M8 8.5 L12 4.5 L16 8.5" /></I>
);
export const IconArrive = (p) => (
  <I {...p}><path className="i2" d="M12 21 C12 21 5.5 14.8 5.5 10 A6.5 6.5 0 0 1 18.5 10 C18.5 14.8 12 21 12 21 Z" /><path d="M9.5 10 L11.3 11.8 L14.8 8.3" /></I>
);

// Maneuver type -> arrow. Valhalla types: 4/5/6 destination, 8 continue,
// 9/10 slight-right/right, 14/15 left/slight-left, 26/27 roundabout.
export function maneuverIcon(type) {
  if (type === 4 || type === 5 || type === 6) return IconArrive;
  if (type >= 9 && type <= 13) return IconTurnRight;
  if (type >= 14 && type <= 18) return IconTurnLeft;
  return IconStraight;
}

// Render-safe wrapper (the purity lint forbids component-returning calls in
// render scope; branching to static JSX inside a component is equivalent).
export function ManeuverIcon({ type, ...props }) {
  if (type === 4 || type === 5 || type === 6) return <IconArrive {...props} />;
  if (type >= 9 && type <= 13) return <IconTurnRight {...props} />;
  if (type >= 14 && type <= 18) return <IconTurnLeft {...props} />;
  return <IconStraight {...props} />;
}
