/**
 * Mock dataset for the map view, ported 1:1 from the approved mockup
 * dashboard/design/map-c-skyrim.dc.html (its renderVals()). Location pixel
 * coordinates come from dashboard/map/whiterun_map.json (the real fixture);
 * the crop rect and projection match the mockup exactly so the Vue render
 * can be visually diffed against it.
 *
 * This fixture is the dev/CI stand-in until Lane 4's frame logs and Lane 6's
 * reader supply real state (M3).
 */

export type RumorStage = "unheard" | "heard" | "repeated" | "dormant" | "forgotten";
export type Glyph = "D" | "G" | "S" | "N";
export type Salience = "observer" | "story";

/** location_id -> pixel position in the 4096 bake (from whiterun_map.json) */
export const LOCATIONS: Record<string, [number, number]> = {
  dragonsreach: [2970, 285],
  gildergreen: [2088, 1631],
  temple: [1965, 1492],
  shrine: [2261, 1433],
  gray_mane: [1882, 1725],
  battle_born: [1444, 1428],
  jorrvaskr: [2631, 1656],
  skyforge: [2981, 1289],
  bannered: [2278, 2345],
  market: [2086, 2319],
  belethors: [1975, 2461],
  arcadias: [2121, 2501],
  warmaidens: [1295, 2441],
  ysoldas: [2090, 2774],
  stables: [683, 2897],
  main_gate: [995, 2304],
  olava: [1568, 2691],
};

/** crop rect of the 4096 bake shown by the mockup: (330,90,3000,3000) */
export const CROP = { x: 330, y: 90, size: 3000 };

/** pixel coords -> percent position within the cropped square */
export function toPct(px: number, py: number): [number, number] {
  return [(px - CROP.x) / (CROP.size / 100), (py - CROP.y) / (CROP.size / 100)];
}

export interface CastMember {
  name: string;
  location: keyof typeof LOCATIONS;
  stage: RumorStage;
  glyph: Glyph | null;
  selected?: boolean;
}

export const CAST: CastMember[] = [
  { name: "Irileth", location: "dragonsreach", stage: "repeated", glyph: "D" },
  { name: "Proventus Avenicci", location: "dragonsreach", stage: "repeated", glyph: "S" },
  { name: "Farengar", location: "dragonsreach", stage: "heard", glyph: null },
  { name: "Hrongar", location: "dragonsreach", stage: "repeated", glyph: "G" },
  { name: "Nazeem", location: "gildergreen", stage: "heard", glyph: null },
  { name: "Danica Pure-Spring", location: "temple", stage: "heard", glyph: "D" },
  { name: "Heimskr", location: "shrine", stage: "dormant", glyph: null },
  { name: "Olfina Gray-Mane", location: "gray_mane", stage: "heard", glyph: "N" },
  { name: "Idolaf Battle-Born", location: "battle_born", stage: "heard", glyph: "G" },
  { name: "Aela", location: "jorrvaskr", stage: "repeated", glyph: null },
  { name: "Farkas", location: "jorrvaskr", stage: "heard", glyph: null },
  { name: "Kodlak Whitemane", location: "jorrvaskr", stage: "unheard", glyph: null },
  { name: "Eorlund Gray-Mane", location: "skyforge", stage: "unheard", glyph: null },
  { name: "Hulda", location: "bannered", stage: "repeated", glyph: "S" },
  { name: "Mikael", location: "bannered", stage: "repeated", glyph: "S" },
  { name: "Sinmir", location: "bannered", stage: "heard", glyph: null },
  { name: "Fralia Gray-Mane", location: "market", stage: "repeated", glyph: null, selected: true },
  { name: "Carlotta Valentia", location: "market", stage: "heard", glyph: "N" },
  { name: "Belethor", location: "belethors", stage: "heard", glyph: null },
  { name: "Arcadia", location: "arcadias", stage: "heard", glyph: "N" },
  { name: "Adrianne Avenicci", location: "warmaidens", stage: "heard", glyph: null },
  { name: "Ulfberth War-Bear", location: "warmaidens", stage: "unheard", glyph: null },
  { name: "Ysolda", location: "ysoldas", stage: "heard", glyph: null },
  { name: "Skulvar Sable-Hilt", location: "stables", stage: "unheard", glyph: null },
  { name: "Gate Guard", location: "main_gate", stage: "unheard", glyph: null },
  { name: "Olava the Feeble", location: "olava", stage: "forgotten", glyph: null },
];

export const STAGE_STYLE: Record<RumorStage, { fill: string; ring: string; size: number }> = {
  unheard: { fill: "rgba(0,0,0,.12)", ring: "#9aa3ad", size: 9 },
  heard: { fill: "#e3b34c", ring: "#141008", size: 11 },
  repeated: { fill: "#ff5233", ring: "#ffe8d9", size: 13 },
  dormant: { fill: "#8fb4d9", ring: "#16202b", size: 10 },
  forgotten: { fill: "#565b63", ring: "#20242a", size: 7 },
};

export const GLYPH_COLOR: Record<Glyph, string> = {
  D: "#ffd166",
  G: "#e05252",
  S: "#ff9a3d",
  N: "#7fd1b9",
};

/** deterministic per-location jitter ring (mockup's RING) */
export const JITTER_RING: [number, number][] = [
  [0, 0],
  [1.5, -0.7],
  [-1.4, 0.9],
  [0.8, 1.5],
  [-1.1, -1.4],
];

export interface MapMarker {
  name: string;
  left: number; // percent within the crop
  top: number;
  fill: string;
  ring: string;
  size: number;
  glyph: Glyph | null;
  glyphColor: string;
  selected: boolean;
}

export function buildMarkers(stainLens: boolean, showGlyphs: boolean): MapMarker[] {
  const seen: Record<string, number> = {};
  return CAST.map((c) => {
    const [px, py] = LOCATIONS[c.location];
    const k = (seen[c.location] = (seen[c.location] ?? -1) + 1);
    const [jx, jy] = JITTER_RING[k % JITTER_RING.length];
    const [lx, ty] = toPct(px, py);
    const st = STAGE_STYLE[c.stage];
    return {
      name: `${c.name} — ${c.stage}`,
      left: +(lx + jx).toFixed(1),
      top: +(ty + jy).toFixed(1),
      fill: stainLens ? st.fill : "#79828e",
      ring: stainLens ? st.ring : "#3a414c",
      size: st.size,
      glyph: showGlyphs ? c.glyph : null,
      glyphColor: c.glyph ? GLYPH_COLOR[c.glyph] : "#888",
      selected: !!c.selected,
    };
  });
}

export interface TimelineEvent {
  pos: number; // percent along the bar
  color: string;
  label: string;
  story: boolean;
}

const EVENTS: [number, string, string, boolean][] = [
  [2.2, "#d9a441", 'C-102 born: "Nazeem bought Chillfurrow"', false],
  [3.6, "#e05252", "grudge: Sinmir → Mikael", true],
  [8.02, "#e8e2d4", "death: Jarl Balgruuf", true],
  [8.08, "#d9a441", 'C-114 born: "Jarl Balgruuf is dead"', true],
  [8.55, "#c678dd", "C-114 v2: assassin→Imperial agents (Mikael)", true],
  [9.15, "#c678dd", "C-114 v3: Imperial→Thalmor (Idolaf)", true],
  [9.5, "#e05252", "grudge: Hrongar → unknown assassin", true],
  [10.3, "#58c1d4", "carrier departs: Ri'saad → Markarth", true],
  [12.9, "#9d7fd1", "threshold: Irileth lockdown ends", false],
  [14.1, "#58c1d4", "carrier arrives: Markarth", true],
];

export const TIMELINE_SPAN_DAYS = 15.7;

export function buildEvents(salience: Salience): TimelineEvent[] {
  return EVENTS.filter((e) => (salience === "story" ? e[3] : true)).map((e) => ({
    pos: +((e[0] / TIMELINE_SPAN_DAYS) * 100).toFixed(1),
    color: e[1],
    label: `t ${Math.round(e[0] * 2880).toLocaleString()} · ${e[2]}`,
    story: e[3],
  }));
}

export const DAY_TICKS = Array.from({ length: 15 }, (_, i) => ({
  pos: +(((i + 1) / TIMELINE_SPAN_DAYS) * 100).toFixed(1),
  n: i + 1,
}));

export const STAGE_LEGEND: { name: RumorStage; count: number; fill: string; ring: string; sw: number }[] = (
  [
    ["unheard", 5],
    ["heard", 12],
    ["repeated", 7],
    ["dormant", 1],
    ["forgotten", 1],
  ] as [RumorStage, number][]
).map(([name, count]) => ({
  name,
  count,
  fill: STAGE_STYLE[name].fill,
  ring: STAGE_STYLE[name].ring,
  sw: STAGE_STYLE[name].size - 3,
}));

export const MAP_LABELS = [
  ["DRAGONSREACH", 88, 9.5],
  ["JORRVASKR", 76.7, 55],
  ["SKYFORGE", 88.4, 42.5],
  ["THE BANNERED MARE", 64.9, 78.2],
  ["MARKET", 56, 71.5],
  ["TEMPLE OF KYNARETH", 54.5, 43.8],
  ["MAIN GATE", 22.2, 76.6],
  ["STABLES", 11.8, 96.2],
  ["WARMAIDEN’S", 32.2, 81.2],
] as const;

/** LIVE-dock display states, ported from the mockup's docked/detached pair */
export const LIVE_STATES = {
  docked: {
    phPos: 96.8,
    phColor: "#ff8a80",
    phLabel: "t 45,187 · D15 17:10 ▸ advancing",
    line1: "LIVE — docked · following newest frame",
    line2: "+38 events since D14 · scrub to detach",
  },
  detached: {
    phPos: 70.1,
    phColor: "#e8e2d4",
    phLabel: "t 31,442 · D11 06:20",
    line1: "LIVE · t 45,187",
    line2: "detached — scrubbed to D11 · ⇥ dock",
  },
} as const;
