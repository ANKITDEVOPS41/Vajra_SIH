import { useEffect, useState } from "react";
import type { ChangeEvent } from "react";
import { FileUp, PanelRightOpen } from "lucide-react";
import type { AssetTriageEntry, AssetTriageReport } from "../types/analytics";

type Props = {
  issueTime: string | null;
  horizonMinutes: number;
  forecastMode: "BASELINE" | "LEARNED";
  onReport: (report: AssetTriageReport | null) => void;
  onInspect: (asset: AssetTriageEntry) => void;
};

export function ThreatTriageBoard({ issueTime, horizonMinutes, forecastMode, onReport, onInspect }: Props) {
  const [collection, setCollection] = useState<unknown>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [report, setReport] = useState<AssetTriageReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!collection || !issueTime) return;
    const controller = new AbortController();
    setReport(null);
    onReport(null);
    setLoading(true);
    setError(null);
    const run = async () => {
      try {
        const response = await fetch("/api/v1/location/triage", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          signal: controller.signal,
          body: JSON.stringify({
            feature_collection: collection,
            issue_time: issueTime,
            horizon_minutes: horizonMinutes,
            forecast_mode: forecastMode,
          }),
        });
        if (!response.ok) {
          const detail = (await response.json()) as { detail?: string | { msg: string }[] };
          throw new Error(typeof detail.detail === "string" ? detail.detail : detail.detail?.map((item) => item.msg).join("; ") || `Asset query failed (${response.status}).`);
        }
        const next = (await response.json()) as AssetTriageReport;
        if (!controller.signal.aborted) {
          setReport(next);
          onReport(next);
        }
      } catch (caught) {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "Asset query failed.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    };
    void run();
    return () => controller.abort();
  }, [collection, issueTime, horizonMinutes, forecastMode, onReport]);

  const loadFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setCollection(null);
    setReport(null);
    setFilename(null);
    onReport(null);
    if (file.size > 1_000_000) {
      setError("GeoJSON file exceeds the 1 MB local upload limit.");
      return;
    }
    try {
      const parsed: unknown = JSON.parse(await file.text());
      if (!parsed || typeof parsed !== "object" || (parsed as { type?: string }).type !== "FeatureCollection") {
        throw new Error("Choose a GeoJSON FeatureCollection of asset Points, Lines, or Polygons.");
      }
      setFilename(file.name);
      setCollection(parsed);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Invalid GeoJSON file.");
    }
  };

  return (
    <section className="border border-cyan-900/30 bg-slate-950/40 p-3" aria-label="Threat triage board">
      <div className="flex items-center justify-between gap-2">
        <div>
          <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-300">Threat triage board</h2>
          <p className="mt-1 font-mono text-[9px] text-slate-500">{report ? `${report.assets.length} ASSETS / ${report.evidence_status}` : filename ?? "GEOJSON ASSET LIST"}</p>
        </div>
        <label className="flex shrink-0 cursor-pointer items-center gap-1.5 border border-cyan-800/70 px-2 py-1.5 font-mono text-[9px] font-bold uppercase text-cyan-200 hover:bg-cyan-950/40">
          <FileUp className="h-3.5 w-3.5" /> Load GeoJSON
          <input className="sr-only" type="file" accept=".geojson,.json,application/geo+json,application/json" onChange={(event) => void loadFile(event)} aria-label="Load Blue Force asset GeoJSON" />
        </label>
      </div>
      {loading ? <p className="mt-3 font-mono text-[10px] text-cyan-200">QUERYING ASSET GEOMETRIES...</p> : null}
      {error ? <p role="alert" className="mt-3 break-words font-mono text-[10px] text-red-300">{error}</p> : null}
      {report ? (
        <div className="mt-3 divide-y divide-slate-800 border-t border-slate-800">
          {report.assets.map((asset, index) => (
            <div key={asset.asset_id} className="grid grid-cols-[20px_minmax(0,1fr)_auto] items-center gap-2 py-2 font-mono text-[10px]">
              <span className="text-slate-500">{String(index + 1).padStart(2, "0")}</span>
              <div className="min-w-0">
                <p className="truncate text-slate-200" title={asset.name}>{asset.name}</p>
                <p className="truncate text-[9px] text-slate-500">{asset.geometry_type} / {asset.result.status} / {asset.result.evidence_status}</p>
              </div>
              <button type="button" onClick={() => onInspect(asset)} aria-label={`Inspect ${asset.name} impact report`} className="flex items-center gap-1 text-right text-cyan-200 hover:text-white">
                <span className={asset.eta_status === "ARRIVED" || asset.eta_status === "COMPUTED" ? "text-red-300" : "text-amber-300"}>
                  {asset.eta_status === "ARRIVED" ? "ARRIVED" : asset.eta_minutes !== null ? `T+${asset.eta_minutes.toFixed(1)}m` : asset.eta_status === "NOT_COMPUTABLE" ? "N/C" : "NO ETA"}
                </span>
                <PanelRightOpen className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      ) : !loading && !error ? <p className="mt-3 font-mono text-[10px] leading-4 text-slate-500">NO ASSETS LOADED</p> : null}
      {report?.status === "NOT_COMPUTABLE" ? <p className="mt-2 font-mono text-[9px] text-amber-300">NOT_COMPUTABLE / NO GEOREFERENCED LEARNED FORECAST</p> : null}
    </section>
  );
}
