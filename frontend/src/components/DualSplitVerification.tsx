import { useEffect, useMemo, useRef, useState } from "react";
import type { Map as LeafletMap } from "leaflet";
import { MapContainer, Polygon, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import { Pause, Play, SkipBack, SkipForward } from "lucide-react";
import type { IsochroneReport } from "../types/analytics";
import type { ForecastPolygon } from "../types/workspaces";
import { RadarFieldLayer, useRadarFrame } from "./RadarFieldLayer";

function SyncViewport({ peer, own }: { peer: React.MutableRefObject<LeafletMap | null>; own: React.MutableRefObject<LeafletMap | null> }) {
  const map = useMap();
  useEffect(() => { own.current = map; map.invalidateSize(); return () => { own.current = null; }; }, [map, own]);
  useMapEvents({ moveend: () => {
    const other = peer.current;
    if (!other) return;
    const center = map.getCenter();
    if (other.getZoom() !== map.getZoom() || other.getCenter().distanceTo(center) > 1) other.setView(center, map.getZoom(), { animate: false });
  } });
  return null;
}

function bandPolygons(band: IsochroneReport["bands"][number]): [number, number][][] {
  const geometry = band.geometry;
  const rings = geometry.type === "Polygon" ? [geometry.coordinates[0]] : geometry.coordinates.map((polygon) => polygon[0]);
  return rings.map((ring) => ring.map(([lon, lat]) => [lat, lon]));
}

export function DualSplitVerification({ forecastCells, currentCells, isochrones, forecastMode, observedOffsets }: {
  forecastCells: ForecastPolygon[];
  currentCells: ForecastPolygon[];
  isochrones: IsochroneReport | null;
  forecastMode: "BASELINE" | "LEARNED";
  observedOffsets: number[];
}) {
  const [minute, setMinute] = useState(0);
  const [playing, setPlaying] = useState(false);
  const left = useRef<LeafletMap | null>(null);
  const right = useRef<LeafletMap | null>(null);
  const observed = observedOffsets.includes(minute);
  const { frame, status } = useRadarFrame(observed ? minute : null);
  const visibleForecast = useMemo(() => minute === 0 ? currentCells : forecastCells.filter((cell) => cell.lead_minutes === minute), [minute, currentCells, forecastCells]);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => setMinute((value) => {
      if (value >= 60) { setPlaying(false); return 60; }
      return value + 5;
    }), 700);
    return () => window.clearInterval(timer);
  }, [playing]);
  const mapClass = "h-full min-h-[360px] w-full bg-[#090d16]";
  const label = `T${minute >= 0 ? "+" : ""}${minute}m`;
  return <div className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-4">
    <div className="flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-lg font-semibold text-slate-100">Dual-screen verification</h2><p className="mt-1 text-xs text-slate-400">Retrospective replay comparison. Forecast and observation are separate issue-time roles.</p></div><span className="font-mono text-xs text-amber-300">{forecastMode === "LEARNED" ? "LEARNED VIL / NOT GEOREFERENCED" : "SIMULATED WGS84 BASELINE"}</span></div>
    <div className="grid min-h-[440px] flex-1 grid-cols-1 gap-3 xl:grid-cols-2">
      <div className="relative min-h-[420px] overflow-hidden border border-slate-700"><MapContainer center={[20.3, 85.82]} zoom={11} scrollWheelZoom className={mapClass}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <SyncViewport own={left} peer={right} />
        {forecastMode === "BASELINE" && minute >= 0 && visibleForecast.map((cell) => <Polygon key={`${cell.cell_id}-${minute}`} positions={cell.polygon.map((point) => [point.lat, point.lon])} pathOptions={{ color: "#66d9e8", weight: 2, fillOpacity: 0.16 }}><Tooltip>{cell.cell_id} / {cell.max_reflectivity_dbz.toFixed(1)} dBZ / SIMULATED {minute === 0 ? "OBSERVED AT ISSUE" : "CONSTANT VELOCITY FORECAST"}</Tooltip></Polygon>)}
        {forecastMode === "BASELINE" && minute > 0 && isochrones?.status === "COMPUTED" && isochrones.bands.filter((band) => band.lead_minutes <= minute).flatMap((band) => bandPolygons(band).map((polygon, index) => <Polygon key={`${band.lead_minutes}-${index}`} positions={polygon} pathOptions={{ color: "#34d399", weight: 1, fillOpacity: 0.04, dashArray: "5 6" }}><Tooltip>T+{band.lead_minutes} swept footprint / {band.method} / {band.evidence_status}</Tooltip></Polygon>))}
      </MapContainer><div className="pointer-events-none absolute left-3 top-3 z-[500] border border-cyan-700/60 bg-[#090d16]/95 px-2 py-1 font-mono text-[10px] text-cyan-200">NOWCAST PREDICTION / BASELINE ALGORITHM</div><div className="pointer-events-none absolute bottom-3 left-3 z-[500] border border-slate-700 bg-[#090d16]/95 px-2 py-1 font-mono text-[10px] text-slate-300">{forecastMode === "LEARNED" ? "NOT_COMPUTABLE / NO WGS84" : minute < 0 ? "NOT ISSUED AT THIS TIME" : visibleForecast.length ? `${visibleForecast.length} CELL FOOTPRINTS / ${label}` : "NO FORECAST FOOTPRINT"}</div></div>
      <div className="relative min-h-[420px] overflow-hidden border border-slate-700"><MapContainer center={[20.3, 85.82]} zoom={11} scrollWheelZoom className={mapClass}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <SyncViewport own={right} peer={left} />
        {observed && frame?.offset_minutes === minute && <RadarFieldLayer frame={frame} opacity={0.9} />}
      </MapContainer><div className="pointer-events-none absolute left-3 top-3 z-[500] border border-emerald-700/60 bg-[#090d16]/95 px-2 py-1 font-mono text-[10px] text-emerald-200">OBSERVED GROUND TRUTH / SIMULATED RADAR REPLAY</div><div className="pointer-events-none absolute bottom-3 left-3 z-[500] border border-slate-700 bg-[#090d16]/95 px-2 py-1 font-mono text-[10px] text-slate-300">{observed ? frame?.offset_minutes === minute ? `${frame.frame_id} / ${frame.method}` : status : "NO OBSERVATION AT THIS LEAD"}</div></div>
    </div>
    <div className="flex items-center gap-2 border border-slate-700 bg-[#0f172a] p-3"><button type="button" title="Jump to T-30" aria-label="Jump to T-30" onClick={() => setMinute(-30)}><SkipBack size={17} /></button><button type="button" title={playing ? "Pause" : "Play"} aria-label={playing ? "Pause" : "Play"} onClick={() => setPlaying(!playing)}>{playing ? <Pause size={17} /> : <Play size={17} />}</button><button type="button" title="Next five minutes" aria-label="Next five minutes" onClick={() => setMinute(Math.min(60, minute + 5))}><SkipForward size={17} /></button><input aria-label="Verification replay time" type="range" min={-30} max={60} step={5} value={minute} onChange={(event) => setMinute(Number(event.target.value))} className="min-w-0 flex-1 accent-cyan-400" /><span className="w-16 text-right font-mono text-xs text-cyan-200">{label}</span></div>
  </div>;
}
