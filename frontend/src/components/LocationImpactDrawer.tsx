import { Clock3, Crosshair, FileSearch, X } from "lucide-react";
import type { LocationQueryResult } from "../types/location";

type Props = {
  name: string;
  coordinates: { lat: number; lon: number };
  result: LocationQueryResult;
  onClose: () => void;
};

const relationTone: Record<string, string> = {
  INTERSECTS: "text-emerald-300",
  WITHIN: "text-emerald-300",
  APPROACHING: "text-amber-300",
  RECEDING: "text-slate-300",
  NO_RELATION: "text-slate-500",
};

export function LocationImpactDrawer({ name, coordinates, result, onClose }: Props) {
  const impacts = [...result.impacts].sort((a, b) => a.lead_minutes - b.lead_minutes);
  const intersection = impacts.find((impact) => impact.spatial_relation === "INTERSECTS" || impact.spatial_relation === "WITHIN");
  const computedEta = impacts
    .map((impact) => impact.eta.eta_minutes)
    .filter((minutes): minutes is number => minutes !== null)
    .sort((a, b) => a - b)[0];
  const method = intersection?.method ?? impacts[0]?.method ?? result.model_status ?? "NOT_COMPUTABLE";

  return (
    <div className="fixed inset-0 z-[1200] bg-black/55 backdrop-blur-[2px]" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <aside role="dialog" aria-modal="true" aria-labelledby="impact-drawer-title" className="absolute inset-y-0 right-0 flex w-full max-w-[480px] flex-col border-l border-cyan-800/40 bg-[#030916]/[0.98] shadow-2xl shadow-black/60">
        <header className="flex items-start justify-between gap-4 border-b border-cyan-900/40 bg-slate-950/80 p-4">
          <div className="flex min-w-0 items-start gap-3">
            <div className="grid h-9 w-9 shrink-0 place-items-center border border-cyan-700/40 bg-cyan-950/30 text-cyan-300"><FileSearch className="h-4 w-4" /></div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 id="impact-drawer-title" className="text-xs font-black uppercase tracking-[0.16em] text-slate-100">Location impact report</h2>
                <span className={`border px-1.5 py-0.5 font-mono text-[9px] ${result.evidence_status === "SIMULATED" ? "border-amber-700/50 text-amber-300" : "border-slate-700 text-slate-300"}`}>{result.evidence_status}</span>
              </div>
              <p className="mt-1 truncate font-mono text-[10px] text-cyan-200">{name} / {coordinates.lat.toFixed(5)}, {coordinates.lon.toFixed(5)}</p>
            </div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close location impact report" title="Close report" className="grid h-8 w-8 shrink-0 place-items-center border border-slate-700 text-slate-400 hover:border-cyan-700 hover:text-white"><X className="h-4 w-4" /></button>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
          <section className="grid grid-cols-2 gap-px border border-slate-800 bg-slate-800">
            <ReportStat label="Spatial result" value={result.status === "NOT_COMPUTABLE" ? "NOT COMPUTABLE" : intersection?.spatial_relation ?? "CLEAR"} />
            <ReportStat label="Earliest ETA" value={computedEta === undefined ? intersection?.eta.status ?? "UNKNOWN" : `T+${computedEta.toFixed(1)} MIN`} />
            <ReportStat label="Issue time" value={formatDate(result.issue_time)} />
            <ReportStat label="Forecast method" value={method} />
          </section>

          <section className="border border-slate-800 bg-slate-950/50 p-3">
            <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.15em] text-slate-400"><Crosshair className="h-3.5 w-3.5 text-cyan-300" /> Engine response</div>
            <p className="mt-2 text-xs leading-5 text-slate-300">{result.message}</p>
            <p className="mt-2 break-all font-mono text-[9px] text-slate-500">QUERY {result.query_id} / MODEL {result.model_version ?? "NONE"} / {result.model_status ?? "NO MODEL"}</p>
          </section>

          <section>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3 className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">Forecast impact sequence</h3>
              <span className="font-mono text-[9px] text-slate-500">{impacts.length} RECORDS</span>
            </div>
            {impacts.length ? (
              <div className="divide-y divide-slate-800 border-y border-slate-800">
                {impacts.map((impact) => (
                  <div key={impact.impact_id} className="grid grid-cols-[54px_minmax(0,1fr)_auto] items-start gap-2 py-2.5 font-mono">
                    <span className="pt-0.5 text-[10px] text-cyan-300">T+{String(impact.lead_minutes).padStart(2, "0")}</span>
                    <div className="min-w-0">
                      <p className={`truncate text-[10px] font-bold ${relationTone[impact.spatial_relation] ?? "text-slate-300"}`}>{impact.spatial_relation} / {impact.cell_id}</p>
                      <p className="mt-1 break-words text-[9px] leading-4 text-slate-500">{impact.method} / {impact.evidence_status}{impact.source_ids.length ? ` / ${impact.source_ids.join(", ")}` : " / NO SOURCE IDS"}</p>
                      <p className="mt-1 text-[9px] text-slate-500"><Clock3 className="mr-1 inline h-3 w-3" />{formatDate(impact.valid_time)} / {impact.forecast_id ?? "NO FORECAST ID"}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[10px] text-slate-200">{impact.value === null ? "--" : `${impact.value.toFixed(1)} ${impact.unit}`}</p>
                      <p className="mt-1 text-[9px] text-slate-500">{impact.eta.status === "COMPUTED" ? `ETA ${impact.eta.eta_minutes?.toFixed(1)}m` : impact.eta.status}{impact.distance_km === null ? "" : ` / ${impact.distance_km.toFixed(1)} km`}</p>
                      {impact.eta.not_computable_reason ? <p className="mt-1 max-w-[120px] text-[9px] leading-4 text-amber-300">{impact.eta.not_computable_reason}</p> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="border border-amber-700/40 bg-amber-950/15 p-3 font-mono text-[10px] leading-5 text-amber-200">NO GEOREFERENCED IMPACT RECORDS / {result.status} / ETA REMAINS GATED</div>
            )}
          </section>

          <p className="border-l-2 border-cyan-700/50 pl-3 font-mono text-[9px] leading-4 text-slate-500">The ETA shown above comes from the nested ETAResult. No score, probability, or sensor field is inferred by this panel.</p>
        </div>
      </aside>
    </div>
  );
}

function ReportStat({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0 bg-[#050b18] p-3"><p className="text-[9px] font-bold uppercase tracking-[0.12em] text-slate-500">{label}</p><p className="mt-1 break-words font-mono text-[10px] font-bold text-slate-200">{value}</p></div>;
}

function formatDate(value: string | null) {
  if (!value) return "--";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toISOString().replace("T", " ").replace(".000Z", "Z");
}
