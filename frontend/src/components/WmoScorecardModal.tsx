import { useEffect, useState } from "react";
import { ClipboardCopy, X } from "lucide-react";
import type { Scorecard } from "../types/workspaces";

function metric(value: number | null): string { return value === null ? "N/C" : value.toFixed(3); }

function exportText(card: Scorecard, format: "Markdown" | "CSV"): string {
  const header = ["Lead", "Status", "Hits", "Misses", "FA", "CN", "POD", "FAR", "CSI", "HSS", "Reason"];
  const rows = card.leads.map((row) => [
    `+${row.lead_minutes}m`, row.status, row.hits ?? "", row.misses ?? "", row.false_alarms ?? "", row.correct_negatives ?? "",
    metric(row.pod), metric(row.far), metric(row.csi), metric(row.hss), row.reason ?? "",
  ].map(String));
  if (format === "CSV") return [header, ...rows].map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(",")).join("\n");
  return [
    `# VAJRA retrospective scorecard — ${card.event_id}`,
    `${card.source} / ${card.method} / ${card.evidence_status} / ${card.forecast_validation_status}`,
    `${card.field} >= ${card.threshold} ${card.threshold_unit}; observations: ${card.observation_source}`,
    `| ${header.join(" | ")} |`, `| ${header.map(() => "---").join(" | ")} |`,
    ...rows.map((row) => `| ${row.join(" | ")} |`),
    "", ...card.limitations,
  ].join("\n");
}

export function WmoScorecardModal({ source, onClose }: { source: "SYNTHETIC" | "SEVIR"; onClose: () => void }) {
  const [card, setCard] = useState<Scorecard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [format, setFormat] = useState<"Markdown" | "CSV">("Markdown");
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let cancelled = false;
    fetch(`/api/v1/replay/wmo-scorecard?source=${source}`)
      .then(async (response) => { if (!response.ok) throw new Error(`Scorecard unavailable (${response.status})`); return response.json() as Promise<Scorecard>; })
      .then((data) => { if (!cancelled) setCard(data); })
      .catch((caught: unknown) => { if (!cancelled) setError(caught instanceof Error ? caught.message : "Scorecard unavailable"); });
    return () => { cancelled = true; };
  }, [source]);
  useEffect(() => {
    const handle = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [onClose]);
  return <div role="presentation" className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/75 p-3" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section role="dialog" aria-modal="true" aria-label="WMO verification scorecard" className="max-h-[90vh] w-full max-w-5xl overflow-auto border border-slate-600 bg-[#0f172a] p-5 shadow-xl">
      <div className="flex items-start justify-between gap-3"><div><h2 className="text-lg font-semibold">Multi-horizon verification scorecard</h2><p className="mt-1 font-mono text-xs text-amber-300">RETROSPECTIVE REPLAY / UNVALIDATED FORECAST SKILL</p></div><button type="button" onClick={onClose} aria-label="Close scorecard" title="Close scorecard"><X size={20} /></button></div>
      {error && <p className="mt-5 text-sm text-rose-300">{error}</p>}
      {!card && !error && <p className="mt-5 text-sm text-slate-400">Calculating contingency scores…</p>}
      {card && <><div className="mt-4 grid gap-2 border-y border-slate-700 py-3 font-mono text-[11px] text-slate-300 sm:grid-cols-2 lg:grid-cols-4"><span>{card.source} / {card.evidence_status}</span><span>{card.method}</span><span>{card.field} {" >= "} {card.threshold} {card.threshold_unit}</span><span>{card.georeferenced ? "WGS84" : "PIXEL SPACE"}</span></div>
        <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[680px] text-left font-mono text-[11px]"><thead className="border-b border-slate-600 text-slate-400"><tr>{["Lead", "Status", "H", "M", "FA", "CN", "POD", "FAR", "CSI", "HSS"].map((head) => <th key={head} className="px-2 py-2 font-medium">{head}</th>)}</tr></thead><tbody>{card.leads.map((row) => <tr key={row.lead_minutes} title={row.reason ?? undefined} className="border-b border-slate-800"><td className="px-2 py-2 text-cyan-200">+{row.lead_minutes}m</td><td className={row.status === "COMPUTED" ? "px-2 text-emerald-300" : "px-2 text-slate-500"}>{row.status}</td>{[row.hits, row.misses, row.false_alarms, row.correct_negatives].map((count, index) => <td key={index} className="px-2">{count ?? "—"}</td>)}{[row.pod, row.far, row.csi, row.hss].map((value, index) => <td key={index} className="px-2">{metric(value)}</td>)}</tr>)}</tbody></table></div>
        <p className="mt-3 text-xs text-slate-400">{card.leads.filter((row) => row.status === "NOT_COMPUTABLE").map((row) => `T+${row.lead_minutes}: ${row.reason}`).join("  •  ")}</p>
        <div className="mt-5 flex flex-wrap items-center gap-2"><div className="flex border border-slate-600">{(["Markdown", "CSV"] as const).map((choice) => <button key={choice} type="button" aria-pressed={format === choice} onClick={() => { setFormat(choice); setCopied(false); }} className={`px-3 py-2 text-xs ${format === choice ? "bg-cyan-900/50 text-cyan-100" : "text-slate-400"}`}>{choice}</button>)}</div><button type="button" onClick={() => void navigator.clipboard.writeText(exportText(card, format)).then(() => setCopied(true))} className="flex items-center gap-2 border border-cyan-700 px-3 py-2 text-xs text-cyan-100"><ClipboardCopy size={14} /> {copied ? "Copied" : "Copy Scorecard Summary"}</button></div>
        <p className="mt-4 text-xs text-slate-500">{card.limitations.join(" ")}</p></>}
    </section>
  </div>;
}
