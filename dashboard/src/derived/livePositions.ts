/**
 * Live NPC positions (ChronicleBridge's spatial-streamer slice,
 * docs/design/chronicle-bridge-spatial-streamer.md) -- a real-time,
 * non-canonical feed, architecturally separate from the frame-log-backed
 * `mapMarkers.ts`/`RunReader` path: no tick, no belief state, no rumor
 * stage. An actor absent from a snapshot is simply outside/indoors right
 * now, per the design doc's "no stale position, no placeholder" rule --
 * this module never carries a marker forward from a previous snapshot.
 *
 * Wire contract: adapters/skyrim/contracts/chronicle-bridge.openapi.yaml.
 * `x`/`y` are raw WhiterunWorld coordinates (no transform applied on the
 * plugin side) -- `worldToPercent` below applies the same two-stage
 * projection the rest of the map already uses: whiterun_map.json's
 * world->pixel `transform` block, then fixtures/whiterunMock.ts's
 * `CROP`/`toPct` pixel->percent-of-crop-square conversion. Verified
 * against whiterun_map.json's own baked `locations[*].pixel` fields
 * (e.g. amrens_house: world [21934.3, -3923.3] -> pixel [1519.9, 1603.7]).
 */
import { toPct } from "../fixtures/whiterunMock";
import mapJson from "../../map/whiterun_map.json";

export interface LiveNpcPosition {
  id: string;
  /** The actor's in-game display name (e.g. "Idolaf Battle-Born") -- display-only, never a stable identity. Empty string if the game reported none. */
  name: string;
  x: number;
  y: number;
}

export interface LivePositionSnapshot {
  wall_ts: number;
  npcs: LiveNpcPosition[];
}

export interface LiveMarker {
  id: string;
  name: string;
  left: number;
  top: number;
}

const { scale, offsX, offsY } = mapJson.transform;
const [imageWidth, imageHeight] = mapJson.image_size;

/** WhiterunWorld raw (x, y) -> percent within the map's cropped square. */
export function worldToPercent(x: number, y: number): [number, number] {
  const px = scale * x + offsX + imageWidth / 2;
  const py = -scale * y + offsY + imageHeight / 2;
  return toPct(px, py);
}

/** A snapshot's npcs -> render-ready markers. Skips any NPC that projects outside the crop square (0-100%) rather than clamping it onto the map's edge. */
export function deriveLiveMarkers(snapshot: LivePositionSnapshot | null): LiveMarker[] {
  if (snapshot === null) return [];
  const markers: LiveMarker[] = [];
  for (const npc of snapshot.npcs) {
    const [left, top] = worldToPercent(npc.x, npc.y);
    if (left < 0 || left > 100 || top < 0 || top > 100) continue;
    markers.push({ id: npc.id, name: npc.name, left, top });
  }
  return markers;
}
