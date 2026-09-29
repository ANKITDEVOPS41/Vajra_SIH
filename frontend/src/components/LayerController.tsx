import { useState } from "react";
import { Layers3, X } from "lucide-react";

const unavailable = [
  ["INSAT-3DR thermal IR", "No aligned raster in replay bundle"],
  ["Lightning density", "No georeferenced strike feed"],
  ["AWS stations", "No authorized station feed"],
  ["Terrain / drainage", "No verified basin mask"],
] as const;

export function LayerController({ radarEnabled, onRadarEnabled, opacity, onOpacity, radarStatus }: {
  radarEnabled: boolean;
  onRadarEnabled: (enabled: boolean) => void;
  opacity: number;
  onOpacity: (opacity: number) => void;
  radarStatus: string;
}) {
  const [open, setOpen] = useState(false);
  return <div className="absolute right-4 top-28 z-[510]">
    <button type="button" title="Map layers" aria-label="Map layers" aria-expanded={open} onClick={() => setOpen(!open)} className="border border-slate-700 bg-[#0f172a]/95 p-2 text-cyan-200"><Layers3 size={18} /></button>
    {open && <div className="mt-2 w-[280px] border border-slate-700 bg-[#0f172a]/95 p-3 shadow-lg">
      <div className="mb-3 flex items-center justify-between"><h3 className="text-xs font-semibold uppercase text-slate-200">Operational layers</h3><button type="button" title="Close layers" aria-label="Close layers" onClick={() => setOpen(false)}><X size={16} /></button></div>
      <label className="flex items-center gap-2 text-xs text-slate-100"><input type="checkbox" checked={radarEnabled} onChange={(event) => onRadarEnabled(event.target.checked)} className="accent-cyan-400" /> Simulated reflectivity raster</label>
      <p className="mt-1 font-mono text-[10px] text-slate-400">{radarStatus} / dBZ / NOT IMD DWR</p>
      <label className="mt-3 block text-[10px] uppercase text-slate-400">Opacity {Math.round(opacity * 100)}%</label>
      <input type="range" min="0" max="100" value={Math.round(opacity * 100)} onChange={(event) => onOpacity(Number(event.target.value) / 100)} disabled={!radarEnabled} aria-label="Radar opacity" className="w-full accent-cyan-400" />
      <div className="mt-2 divide-y divide-slate-800 border-t border-slate-800">{unavailable.map(([name, reason]) => <div key={name} className="py-2"><p className="text-xs text-slate-500">{name} <span className="font-mono text-[9px]">UNAVAILABLE</span></p><p className="text-[10px] text-slate-600">{reason}</p></div>)}</div>
    </div>}
  </div>;
}
