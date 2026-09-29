import { useEffect, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from "react-leaflet";
import { Wind } from "lucide-react";
import type { GeoPoint } from "../types/workspaces";

type Geometry = {
  aerodrome: "VEBS"; runway: "14/32"; threshold_14: GeoPoint; threshold_32: GeoPoint;
  midpoint: GeoPoint; approach_14: GeoPoint; approach_32: GeoPoint;
  approach_distance_km: number; true_bearing_14_deg: number; source: string; source_date: string;
};
type Result = {
  status: "USER_SUPPLIED_CALCULATION";
  approach_headwind_m_s: number; runway_headwind_m_s: number;
  approach_crosswind_m_s: number; runway_crosswind_m_s: number;
  delta_headwind_m_s: number; delta_vector_m_s: number; delta_vector_kt: number;
  threshold_m_s: number; threshold_exceeded: boolean; source_description: string; limitation: string;
};
const point = (value: GeoPoint): [number, number] => [value.lat, value.lon];

export function AirfieldRunwayTwin() {
  const [geometry, setGeometry] = useState<Geometry | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [direction, setDirection] = useState<"14" | "32">("14");
  const [values, setValues] = useState({ approachEast: "", approachNorth: "", runwayEast: "", runwayNorth: "" });
  const [source, setSource] = useState("");
  const [result, setResult] = useState<Result | null>(null);
  useEffect(() => {
    fetch("/api/v1/airfield/vebs").then(async (response) => { if (!response.ok) throw new Error("Runway geometry unavailable"); return response.json() as Promise<Geometry>; }).then(setGeometry).catch((caught: unknown) => setError(caught instanceof Error ? caught.message : "Runway geometry unavailable"));
  }, []);
  const calculate = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setResult(null);
    try {
      const response = await fetch("/api/v1/airfield/wind-shear", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({
        runway_direction: direction, source_description: source,
        approach_wind: { east_m_s: Number(values.approachEast), north_m_s: Number(values.approachNorth) },
        runway_wind: { east_m_s: Number(values.runwayEast), north_m_s: Number(values.runwayNorth) },
      }) });
      if (!response.ok) throw new Error(`Wind calculation rejected (${response.status})`);
      setResult(await response.json() as Result);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Calculation failed"); }
  };
  return <div className="grid h-full min-h-0 gap-4 overflow-y-auto p-4 xl:grid-cols-[minmax(0,1fr)_360px]">
    <section className="relative min-h-[480px] overflow-hidden border border-slate-700 bg-[#090d16]">
      {geometry && <MapContainer center={point(geometry.midpoint)} zoom={13} scrollWheelZoom className="h-full w-full"><TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" /><Polyline positions={[point(geometry.threshold_14), point(geometry.threshold_32)]} pathOptions={{ color: "#67e8f9", weight: 7 }}><Tooltip>VEBS RWY 14/32 / AAI AIP</Tooltip></Polyline><Polyline positions={[point(geometry.approach_14), point(geometry.threshold_14)]} pathOptions={{ color: "#34d399", weight: 2, dashArray: "5 6" }} /><Polyline positions={[point(geometry.threshold_32), point(geometry.approach_32)]} pathOptions={{ color: "#34d399", weight: 2, dashArray: "5 6" }} />{(["threshold_14", "midpoint", "threshold_32", "approach_14", "approach_32"] as const).map((name) => <CircleMarker key={name} center={point(geometry[name])} radius={5} pathOptions={{ color: "#a5f3fc", fillColor: "#0f172a", fillOpacity: 1 }}><Tooltip>{name.replaceAll("_", " ").toUpperCase()} / {geometry.approach_distance_km} km gates are computed WGS84 projections</Tooltip></CircleMarker>)}</MapContainer>}
      <div className="pointer-events-none absolute left-3 top-3 z-[500] border border-slate-700 bg-[#090d16]/95 px-3 py-2"><h2 className="text-sm font-semibold">VEBS runway twin</h2><p className="mt-1 font-mono text-[10px] text-slate-400">AAI AIP RWY 14/32 / 3 KM GEODESIC APPROACH GATES</p></div>
    </section>
    <section className="min-w-0 space-y-4 border border-slate-700 bg-[#0f172a] p-4"><div className="flex items-center gap-2"><Wind size={18} className="text-cyan-300" /><h2 className="text-sm font-semibold">Runway-relative wind vector</h2></div><p className="text-xs text-slate-400">No radar radial velocity or aerodrome wind feed is connected. Enter two measured east/north vectors to test the calculation; this is not a microburst detection product.</p>
      <form onSubmit={(event) => void calculate(event)} className="space-y-3"><label className="block text-xs text-slate-300">Runway direction<select value={direction} onChange={(event) => { setDirection(event.target.value as "14" | "32"); setResult(null); }} className="mt-1 w-full border border-slate-600 bg-[#090d16] p-2"><option value="14">RWY 14</option><option value="32">RWY 32</option></select></label>
        <div className="grid grid-cols-2 gap-2">{([ ["approachEast", "Approach east m/s"], ["approachNorth", "Approach north m/s"], ["runwayEast", "Runway east m/s"], ["runwayNorth", "Runway north m/s"] ] as const).map(([key, label]) => <label key={key} className="text-[11px] text-slate-300">{label}<input required type="number" min={-100} max={100} step="any" value={values[key]} onChange={(event) => { setValues({ ...values, [key]: event.target.value }); setResult(null); }} className="mt-1 w-full border border-slate-600 bg-[#090d16] p-2 font-mono" /></label>)}</div>
        <label className="block text-[11px] text-slate-300">Measurement provenance<input required minLength={3} value={source} onChange={(event) => { setSource(event.target.value); setResult(null); }} placeholder="Instrument / timestamp / operator" className="mt-1 w-full border border-slate-600 bg-[#090d16] p-2" /></label><button type="submit" className="w-full border border-cyan-700 bg-cyan-900/30 p-2 text-xs font-semibold text-cyan-100">Calculate vector difference</button></form>
      {error && <p className="text-xs text-rose-300">{error}</p>}
      {result ? <div className="border-t border-slate-700 pt-3"><p className="font-mono text-[10px] text-amber-300">{result.status} / {result.source_description}</p><div className="mt-3 grid grid-cols-2 gap-2 font-mono text-xs"><span>Approach headwind<br /><b>{result.approach_headwind_m_s.toFixed(1)} m/s</b></span><span>Runway headwind<br /><b>{result.runway_headwind_m_s.toFixed(1)} m/s</b></span><span>Delta headwind<br /><b>{result.delta_headwind_m_s.toFixed(1)} m/s</b></span><span>Vector difference<br /><b>{result.delta_vector_m_s.toFixed(1)} m/s / {result.delta_vector_kt.toFixed(1)} kt</b></span></div><p className={`mt-3 border p-2 font-mono text-xs ${result.threshold_exceeded ? "border-rose-700 text-rose-300" : "border-emerald-800 text-emerald-300"}`}>{result.threshold_exceeded ? "ILLUSTRATIVE 15 m/s THRESHOLD EXCEEDED" : "BELOW ILLUSTRATIVE 15 m/s THRESHOLD"}</p><p className="mt-2 text-[11px] text-slate-400">{result.limitation}</p></div> : <p className="font-mono text-xs text-slate-500">LLWS: NOT_COMPUTABLE / NO WIND VECTORS</p>}
      <div className="grid grid-cols-3 gap-2 border-t border-slate-700 pt-3 font-mono text-[11px] text-slate-400">{["Pressure hPa", "Surface °C", "CAPE J/kg"].map((label) => <div key={label}>{label}<p className="mt-1 text-slate-500">NO FEED</p></div>)}</div>
      {geometry && <a href={geometry.source} target="_blank" rel="noreferrer" className="block text-[11px] text-cyan-300 underline">AAI runway geometry / {geometry.source_date}</a>}
    </section>
  </div>;
}
