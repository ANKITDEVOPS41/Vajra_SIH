import { useEffect, useMemo, useState } from "react";
import { Bell, ClipboardCopy, Download, MapPinned, Pause, Play, ShieldAlert } from "lucide-react";
import type { LocationQueryResult } from "../types/location";
import type { GeoPoint } from "../types/workspaces";

type Shelter = { name: string; point: GeoPoint; verifiedAt: string; source: string; status: "OPEN" };
const copy = {
  en: { headline: "Convective cell replay near your location", shelter: "Seek a sturdy building. Avoid waterlogged underpasses and contact with electrical equipment in standing water. Follow official local advisories.", locale: "English" },
  hi: { headline: "आपके स्थान के पास संवहनीय बादल का रिप्ले", shelter: "पक्के भवन में शरण लें। जलभराव वाले अंडरपास और पानी में बिजली के उपकरणों से दूर रहें। स्थानीय आधिकारिक सलाह का पालन करें।", locale: "Hindi · draft translation" },
  or: { headline: "ଆପଣଙ୍କ ସ୍ଥାନ ନିକଟରେ ବଜ୍ରମେଘ ରିପ୍ଲେ", shelter: "ପକ୍କା ଘରେ ଆଶ୍ରୟ ନିଅନ୍ତୁ। ଜଳମଗ୍ନ ଅଣ୍ଡରପାସ୍ ଓ ପାଣି ଭିତରେ ବିଦ୍ୟୁତ୍ ଉପକରଣଠାରୁ ଦୂରେଇ ରୁହନ୍ତୁ। ସରକାରୀ ସୂଚନା ଅନୁସରଣ କରନ୍ତୁ।", locale: "Odia · draft translation" },
} as const;
type Language = keyof typeof copy;
const xml = (value: string) => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&apos;");
function distanceKm(a: GeoPoint, b: GeoPoint): number {
  const rad = Math.PI / 180;
  const deltaLat = (b.lat - a.lat) * rad;
  const deltaLon = (b.lon - a.lon) * rad;
  const h = Math.sin(deltaLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(deltaLon / 2) ** 2;
  return 6371.0088 * 2 * Math.asin(Math.sqrt(h));
}
function capXml(result: LocationQueryResult, place: string, text: typeof copy[Language], eta: number): string {
  const impact = result.impacts.find((item) => item.eta.eta_minutes === eta);
  const sent = new Date(result.issue_time).toISOString();
  const eventTime = impact?.valid_time ? new Date(impact.valid_time).toISOString() : sent;
  return `<?xml version="1.0" encoding="UTF-8"?>\n<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">\n  <identifier>${xml(`vajra-replay-${result.query_id}`)}</identifier>\n  <sender>vajra.local</sender>\n  <sent>${sent}</sent>\n  <status>Test</status>\n  <msgType>Alert</msgType>\n  <scope>Private</scope>\n  <note>Unissued replay simulator draft. Not an NDMA, IMD, or Sachet message.</note>\n  <info>\n    <language>${text === copy.hi ? "hi-IN" : text === copy.or ? "or-IN" : "en-IN"}</language>\n    <category>Met</category>\n    <event>Simulated convective cell intersection</event>\n    <urgency>Unknown</urgency>\n    <severity>Unknown</severity>\n    <certainty>Unknown</certainty>\n    <effective>${sent}</effective>\n    <expires>${eventTime}</expires>\n    <headline>${xml(text.headline)}</headline>\n    <description>${xml(`${text.shelter} Baseline ETA T+${eta.toFixed(1)} minutes, retrospective simulation only.`)}</description>\n    <instruction>${xml(text.shelter)}</instruction>\n    <area><areaDesc>${xml(place)} (queried point only; no authorized alert polygon)</areaDesc></area>\n  </info>\n</alert>`;
}

export function SachetMobileSimulator({ result, location, place, replayOffset, forecastMode }: {
  result: LocationQueryResult | null; location: GeoPoint; place: string; replayOffset: number;
  forecastMode: "BASELINE" | "LEARNED";
}) {
  const [language, setLanguage] = useState<Language>("en");
  const [showXml, setShowXml] = useState(false);
  const [clockOffset, setClockOffset] = useState(replayOffset);
  const [clockRunning, setClockRunning] = useState(false);
  const [exportStatus, setExportStatus] = useState("");
  const [shelters, setShelters] = useState<Shelter[]>([]);
  const [importStatus, setImportStatus] = useState("NO VERIFIED SHELTER CATALOGUE");
  const eta = forecastMode === "BASELINE" && result?.status === "COMPUTED" ? result.impacts.filter((item) => (item.spatial_relation === "INTERSECTS" || item.spatial_relation === "WITHIN") && item.eta.status === "COMPUTED").map((item) => item.eta.eta_minutes).filter((value): value is number => value !== null).sort((a, b) => a - b)[0] : undefined;
  const remaining = eta === undefined ? null : Math.max(0, eta - clockOffset);
  const nearest = useMemo(() => shelters.map((shelter) => ({ ...shelter, distance: distanceKm(location, shelter.point) })).sort((a, b) => a.distance - b.distance)[0], [shelters, location]);
  const draft = eta !== undefined && result ? capXml(result, place, copy[language], eta) : null;
  useEffect(() => {
    if (!clockRunning) return;
    const timer = window.setInterval(() => setClockOffset((offset) => {
      if (offset >= 60 || (eta !== undefined && offset + 1 >= eta)) { setClockRunning(false); return Math.min(60, offset + 1); }
      return offset + 1;
    }), 1000);
    return () => window.clearInterval(timer);
  }, [clockRunning, eta]);
  const downloadCap = () => {
    if (!draft) return;
    const url = URL.createObjectURL(new Blob([draft], { type: "application/xml" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `vajra-replay-test-${result?.query_id ?? "draft"}.xml`;
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
  const importShelters = async (file: File | undefined) => {
    if (!file) return;
    try {
      const data: unknown = JSON.parse(await file.text());
      if (!data || typeof data !== "object" || !("type" in data) || data.type !== "FeatureCollection" || !("features" in data) || !Array.isArray(data.features)) throw new Error("Expected a GeoJSON FeatureCollection.");
      const valid = data.features.flatMap((feature: unknown) => {
        if (!feature || typeof feature !== "object" || !("geometry" in feature) || !("properties" in feature)) return [];
        const item = feature as { geometry: { type?: string; coordinates?: unknown }; properties: Record<string, unknown> };
        const coordinates = item.geometry.coordinates;
        if (item.geometry.type !== "Point" || !Array.isArray(coordinates) || coordinates.length < 2 || !coordinates.slice(0, 2).every((n) => typeof n === "number" && Number.isFinite(n))) return [];
        const [lon, lat] = coordinates as number[];
        const { name, status, verified_at, source } = item.properties;
        if (Math.abs(lat) > 90 || Math.abs(lon) > 180 || typeof name !== "string" || status !== "OPEN" || typeof verified_at !== "string" || Number.isNaN(Date.parse(verified_at)) || typeof source !== "string" || !source.trim()) return [];
        return [{ name, point: { lat, lon }, verifiedAt: verified_at, source, status: "OPEN" as const }];
      });
      if (!valid.length) throw new Error("No OPEN point shelters with name, source and verified_at were found.");
      setShelters(valid);
      setImportStatus(`${valid.length} USER-SUPPLIED OPEN SHELTERS / NOT INDEPENDENTLY VERIFIED`);
    } catch (caught) { setShelters([]); setImportStatus(caught instanceof Error ? caught.message : "Shelter import failed"); }
  };
  return <div className="grid h-full min-h-0 gap-4 overflow-y-auto p-4 lg:grid-cols-[minmax(320px,460px)_minmax(0,1fr)]">
    <div className="mx-auto w-full max-w-[390px] self-start border-[7px] border-slate-700 bg-[#0f172a] p-4 shadow-xl"><div className="mx-auto mb-5 h-1 w-20 rounded-full bg-slate-600" /><div className="flex items-center justify-between text-xs text-slate-400"><span>VAJRA / PUBLIC ALERT PREVIEW</span><Bell size={16} /></div><div className="mt-5 border border-amber-700/50 bg-amber-950/20 p-3 font-mono text-[10px] text-amber-200">SIMULATION ONLY · NOT AN NDMA / IMD / SACHET ALERT</div><div className="mt-4 flex gap-1" role="group" aria-label="Alert language">{(["en", "or", "hi"] as const).map((lang) => <button key={lang} type="button" aria-pressed={language === lang} onClick={() => setLanguage(lang)} className={`flex-1 border px-2 py-1.5 text-xs ${language === lang ? "border-cyan-600 bg-cyan-900/40 text-cyan-100" : "border-slate-700 text-slate-400"}`}>{lang === "or" ? "ଓଡ଼ିଆ" : lang === "hi" ? "हिन्दी" : "English"}</button>)}</div>
      <p className="mt-5 text-[10px] uppercase text-slate-400">{copy[language].locale} / {place}</p><h2 className="mt-2 text-lg font-semibold leading-snug text-slate-100">{copy[language].headline}</h2><div className="mt-4 border-y border-slate-700 py-4"><p className="text-[10px] uppercase text-slate-400">Replay impact countdown</p><p className="mt-1 font-mono text-3xl text-cyan-200">{remaining === null ? "NOT_COMPUTABLE" : remaining === 0 ? "ARRIVED" : `${remaining.toFixed(1)} min`}</p><p className="mt-1 font-mono text-[10px] text-slate-500">{eta === undefined ? "QUERY A WGS84 LOCATION IN SPATIAL NOWCAST" : `T+${eta.toFixed(1)} FROM ISSUE / CURRENT REPLAY T${clockOffset >= 0 ? "+" : ""}${clockOffset}`}</p><button type="button" disabled={remaining === null || remaining === 0} onClick={() => setClockRunning(!clockRunning)} className="mt-3 flex items-center gap-2 border border-slate-600 px-2 py-1.5 text-xs text-slate-200 disabled:opacity-40">{clockRunning ? <Pause size={13} /> : <Play size={13} />}{clockRunning ? "Pause replay clock" : "Play replay clock"}</button></div><p className="mt-4 text-sm leading-6 text-slate-300">{copy[language].shelter}</p>{language !== "en" && <p className="mt-2 text-[10px] text-amber-300">Draft translation, requires human review before use.</p>}
      <div className="mt-5 border border-slate-700 p-3"><div className="flex items-center gap-2 text-sm"><MapPinned size={16} className="text-emerald-300" /><b>Nearest shelter</b></div>{nearest ? <><p className="mt-2 text-sm">{nearest.name} / {nearest.distance.toFixed(1)} km</p><p className="mt-1 font-mono text-[10px] text-amber-300">USER-SUPPLIED OPEN / {nearest.verifiedAt} / {nearest.source}</p><a href={`https://www.google.com/maps/dir/?api=1&destination=${nearest.point.lat},${nearest.point.lon}`} target="_blank" rel="noreferrer" className="mt-3 block border border-cyan-700 p-2 text-center text-xs text-cyan-100">Open GPS route navigation</a></> : <p className="mt-2 font-mono text-xs text-slate-500">{importStatus}</p>}</div>
    </div>
    <section className="space-y-4 border border-slate-700 bg-[#0f172a] p-4"><div className="flex items-center gap-2"><ShieldAlert size={17} className="text-cyan-300" /><h2 className="text-sm font-semibold">Public warning simulation</h2></div><p className="text-xs leading-5 text-slate-400">This is a private replay preview, not a broadcast channel. Authorized warnings, shelter operations, and routing require live agency data and approval. Follow official advisories in real emergencies.</p><div className="border-t border-slate-700 pt-4"><label className="block text-xs text-slate-300">Import shelter GeoJSON<input type="file" accept=".json,.geojson,application/geo+json" onChange={(event) => void importShelters(event.target.files?.[0])} className="mt-2 block w-full text-xs" /></label><p className="mt-2 font-mono text-[10px] text-slate-500">Point features require properties: name, status=OPEN, verified_at, source. User-supplied status is not independently verified.</p></div><div className="border-t border-slate-700 pt-4"><button type="button" aria-expanded={showXml} onClick={() => setShowXml(!showXml)} className="border border-slate-600 px-3 py-2 text-xs text-cyan-200">{showXml ? "Hide" : "Show"} CAP 1.2 test draft</button>{showXml && <div className="mt-3">{draft ? <><div className="mb-2 flex gap-2"><button type="button" onClick={() => void navigator.clipboard.writeText(draft).then(() => setExportStatus("Copied test draft")).catch(() => setExportStatus("Clipboard unavailable"))} className="flex items-center gap-1 border border-slate-600 px-2 py-1 text-xs"><ClipboardCopy size={13} /> Copy XML</button><button type="button" onClick={downloadCap} className="flex items-center gap-1 border border-slate-600 px-2 py-1 text-xs"><Download size={13} /> Download XML</button></div><pre className="max-h-[440px] overflow-auto border border-slate-700 bg-[#090d16] p-3 font-mono text-[10px] text-slate-300">{draft}</pre></> : <p className="font-mono text-xs text-slate-500">NOT_COMPUTABLE / STRICT INTERSECTION ETA REQUIRED</p>}</div>}{exportStatus && <p role="status" className="mt-2 text-xs text-cyan-300">{exportStatus}</p>}</div><p className="text-[11px] text-slate-500">CAP draft uses Test / Private and no agency sender. No polygon is invented from a point query.</p></section>
  </div>;
}
