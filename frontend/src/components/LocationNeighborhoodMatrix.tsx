import { ArrowUpRight } from "lucide-react";
import type { LocationNeighborhoodCell } from "../types/location";

type Props = {
  cells: LocationNeighborhoodCell[];
  onInspect: (cell: LocationNeighborhoodCell) => void;
};

export function LocationNeighborhoodMatrix({ cells, onInspect }: Props) {
  if (!cells.length) return null;
  const gated = cells.every((cell) => cell.status === "NOT_COMPUTABLE");

  return (
    <section className="border border-cyan-900/30 bg-slate-950/45 p-3" aria-label="One kilometre location neighborhood impact matrix">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div>
          <h2 className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-300">1 km neighborhood</h2>
          <p className="mt-1 font-mono text-[9px] text-slate-500">{gated ? "WGS84 GATE / NO POLYGON QUERIES" : "9 polygon queries / forecast-backed"}</p>
        </div>
        <span className="font-mono text-[9px] text-cyan-300">N ↑</span>
      </div>
      <div className="grid grid-cols-3 gap-px border border-slate-800 bg-slate-800">
        {cells.map((cell) => {
          const impacts = cell.result?.impacts ?? [];
          const intersects = impacts.some((impact) => impact.spatial_relation === "INTERSECTS" || impact.spatial_relation === "WITHIN");
          const eta = impacts
            .map((impact) => impact.eta.eta_minutes)
            .filter((minutes): minutes is number => minutes !== null)
            .sort((a, b) => a - b)[0];
          const peakDbz = impacts
            .filter((impact) => impact.hazard === "MAX_REFLECTIVITY_DBZ" && impact.value !== null)
            .reduce<number | null>((peak, impact) => peak === null ? impact.value : Math.max(peak, impact.value!), null);
          const distance = impacts
            .map((impact) => impact.distance_km)
            .filter((km): km is number => km !== null)
            .sort((a, b) => a - b)[0];
          const visualState = cell.status === "COMPUTED"
            ? intersects ? "text-emerald-300" : "text-slate-300"
            : cell.status === "NOT_COMPUTABLE" ? "text-amber-300" : "text-slate-500";

          return (
            <button
              key={cell.id}
              type="button"
              onClick={() => cell.result && onInspect(cell)}
              disabled={!cell.result}
              aria-label={`${cell.label} neighborhood cell, ${cell.status}`}
              className="group flex min-h-[82px] min-w-0 flex-col justify-between bg-[#050b18] p-2 text-left transition hover:bg-cyan-950/30 disabled:cursor-default"
            >
              <span className="flex items-center justify-between font-mono text-[9px] font-bold text-slate-500">
                {cell.label}
                {cell.result ? <ArrowUpRight className="h-3 w-3 text-cyan-700 group-hover:text-cyan-300" /> : null}
              </span>
              <span className={`truncate font-mono text-[10px] font-bold ${visualState}`}>
                {cell.status === "LOADING" ? "QUERYING" : cell.status === "ERROR" ? "ERROR" : cell.status === "NOT_COMPUTABLE" ? "NOT COMPUTABLE" : intersects ? "INTERSECTS" : "CLEAR"}
              </span>
              <span className="truncate font-mono text-[9px] text-slate-400">
                {cell.status !== "COMPUTED" ? cell.status === "ERROR" ? cell.error ?? "API ERROR" : "WGS84 GATE" : `${peakDbz === null ? "PEAK --" : `PEAK ${peakDbz.toFixed(0)} dBZ`} / ${eta === undefined ? distance === undefined ? "NO ETA" : `${distance.toFixed(1)} km` : `ETA ${eta.toFixed(1)}m`}`}
              </span>
            </button>
          );
        })}
      </div>
      <p className="mt-2 font-mono text-[9px] leading-4 text-slate-500">Tiles report spatial relation from LocationImpact. Reflectivity, ETA, and range appear only when returned by the engine.</p>
    </section>
  );
}
