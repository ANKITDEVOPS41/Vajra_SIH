import { useEffect, useMemo, useRef, useState } from "react";
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { CircleMarker, MapContainer, Polygon, Polyline, TileLayer, Tooltip as LeafletTooltip, useMapEvents } from "react-leaflet";
import {
  Activity,
  BarChart3,
  CloudLightning,
  Cpu,
  Crosshair,
  DatabaseZap,
  Gauge,
  Layers3,
  MapPin,
  MapPinned,
  PanelRightOpen,
  Pause,
  Play,
  Radar,
  Route,
  Satellite,
  Shield,
  SkipBack,
  SkipForward,
  TerminalSquare,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { renderVilGrid } from "./lib/gridOverlay";
import { LocationImpactDrawer } from "./components/LocationImpactDrawer";
import { LocationNeighborhoodMatrix } from "./components/LocationNeighborhoodMatrix";
import { ThreatTriageBoard } from "./components/ThreatTriageBoard";
import { DualSplitVerification } from "./components/DualSplitVerification";
import { WmoScorecardModal } from "./components/WmoScorecardModal";
import { AirfieldRunwayTwin } from "./components/AirfieldRunwayTwin";
import { SachetMobileSimulator } from "./components/SachetMobileSimulator";
import { LayerController } from "./components/LayerController";
import { RadarFieldLayer, useRadarFrame } from "./components/RadarFieldLayer";
import { AIPipelineWorkspace } from "./components/AIPipelineWorkspace";
import { DataSourcesWorkspace } from "./components/DataSourcesWorkspace";
import type { AssetTriageReport, IMDBridgeStatus, IntensificationReport, IsochroneReport } from "./types/analytics";
import type { EvidenceStatus, LocationNeighborhoodCell, LocationQueryResult } from "./types/location";

type ReplaySource = {
  source_id: string;
  name: string;
  modality: "radar" | "satellite" | "lightning" | "environmental" | "gauge";
  evidence_status: EvidenceStatus;
  availability: "AVAILABLE" | "DEGRADED" | "NOT_AVAILABLE";
  quality_status: string;
  freshness_minutes: number | null;
  provenance: string;
};

type ReplayEvent = {
  source_id: string;
  level: "INFO" | "WATCH" | "WARNING" | "CRITICAL";
  message: string;
};

type ReplayCell = {
  cell_id: string;
  centroid: { lat: number; lon: number };
  max_reflectivity_dbz: number;
  rain_rate_mm_h: number;
  lightning_flashes: number;
  lifecycle_state: string;
};

type ReplayFrame = {
  frame_id: string;
  offset_minutes: number;
  valid_time: string;
  record_type: "OBSERVATION";
  available_at_issue_time: boolean;
  cells: ReplayCell[];
  events: ReplayEvent[];
};

type ReplaySession = {
  event_id: string;
  label: string;
  region: string;
  mode: "REPLAY";
  evidence_status: EvidenceStatus;
  coordinate_reference_system: string;
  issue_time: string;
  horizon_minutes: number;
  timeline_step_minutes: number;
  verification_status: "NOT_EVALUATED" | "EVALUATED";
  metrics: { csi: number | null; pod: number | null; far: number | null };
  sources: ReplaySource[];
  frames: ReplayFrame[];
  provenance: {
    dataset_id: string;
    dataset_version: string;
    code_version: string;
  };
  limitations: string[];
};

type TelemetrySnapshot = {
  event_id: string;
  mode: "REPLAY";
  evidence_status: EvidenceStatus;
  issue_time: string;
  horizon_minutes: number;
  frame_count: number;
  available_sources: number;
  total_sources: number;
  verification_status: "NOT_EVALUATED" | "EVALUATED";
  csi: number | null;
  pod: number | null;
};

type VerificationReport = {
  source: "SYNTHETIC" | "SEVIR";
  status: "COMPUTED" | "UNVALIDATED";
  forecast_validation_status: "UNVALIDATED";
  evidence_status: EvidenceStatus;
  method: string;
  field: string;
  threshold: number;
  threshold_unit: string;
  georeferenced: boolean;
  observation_source: string;
  leads: { lead_minutes: number; csi: number | null; pod: number | null }[];
  csi: number | null;
  pod: number | null;
  limitations: string[];
};

type GridReplayMetadata = {
  event_id: string;
  sample_id: string;
  evidence_status: EvidenceStatus;
  field: string;
  units: string;
  frame_count: number;
  time_step_minutes: number;
  issue_index: number;
  georeferenced: boolean;
};

type GridReplayFrame = {
  frame_index: number;
  offset_minutes: number;
  width: number;
  height: number;
  values: number[][];
};

type LearnedGridForecast = {
  model_version: string;
  model_status: "UNVALIDATED_PROTOTYPE";
  evidence_status: "LEARNED_FORECAST";
  georeferenced: false;
  frames: { lead_minutes: number; width: number; height: number; values: number[][]; cells: { cell_id: string; centroid_x: number; centroid_y: number; radius_pixels: number }[] }[];
};

type MultimodalStatus = {
  fusion_mode: "VIL_ONLY_FALLBACK";
  model_input_channels: string[];
  modalities: {
    source_id: string;
    availability: "AVAILABLE" | "NOT_AVAILABLE";
    role: "MODEL_INPUT" | "CONTEXT_ONLY" | "UNAVAILABLE";
    aligned_context_frames: number;
    reason: string;
  }[];
};

type HazardIndicator = {
  cell_id: string;
  lead_minutes: number;
  indicator: "HIGH_REFLECTIVITY_CORE" | "NORMALIZED_VIL_CORE" | "CLOUDBURST_RISK" | "HAIL_RISK";
  state: "THRESHOLD_MET" | "BELOW_THRESHOLD" | "NOT_EVALUABLE";
  value: number | null;
  threshold: number | null;
  unit: string | null;
  method: string;
  evidence_status: EvidenceStatus;
  derivation_status: "INFERRED";
  uncertainty_status: "NOT_CALIBRATED";
  probability: null;
  reason: string;
};

type HazardScreening = {
  forecast_mode: "BASELINE" | "LEARNED";
  modality_mode: "VIL_ONLY_FALLBACK" | "SIMULATED_RADAR_ONLY";
  indicators: HazardIndicator[];
};

type ModelArtifact = {
  model_id: string;
  architecture: string;
  parameter_count: number;
  status: "UNVALIDATED_PROTOTYPE" | "VALIDATED";
  evidence_status: "PROPOSED" | "IMPLEMENTED" | "VALIDATED";
};

type BaselineCell = {
  cell_id: string;
  lead_minutes?: number;
  centroid: { lat: number; lon: number };
  polygon: { lat: number; lon: number }[];
  equivalent_radius_km: number;
  max_reflectivity_dbz: number;
  area_km2?: number;
  qc_removed_pixels?: number;
};

type BaselineForecast = {
  event_id: string;
  evidence_status: EvidenceStatus;
  method: "CONSTANT_VELOCITY_EQUIVALENT_AREA";
  current_cells: BaselineCell[];
  forecast_cells: BaselineCell[];
  limitations: string[];
};

const workspaces = [
  { id: "spatial", label: "Spatial Nowcast", icon: MapPinned },
  { id: "verification", label: "Dual-Screen Verification", icon: Layers3 },
  { id: "airfield", label: "Airfield Runway Twin", icon: Route },
  { id: "alert", label: "Sachet / Public Alert", icon: Shield },
  { id: "ai", label: "AI Pipeline & XAI", icon: Cpu },
  { id: "sources", label: "Data Sources & IMD", icon: DatabaseZap },
] as const;
type Workspace = (typeof workspaces)[number]["id"];

const initialPoint = { lat: 20.2961, lon: 85.8245 };

function App() {
  const [workspace, setWorkspace] = useState<Workspace>("spatial");
  const [scorecardOpen, setScorecardOpen] = useState(false);
  const [radarEnabled, setRadarEnabled] = useState(false);
  const [radarOpacity, setRadarOpacity] = useState(0.75);
  const [telemetry, setTelemetry] = useState<TelemetrySnapshot | null>(null);
  const [replay, setReplay] = useState<ReplaySession | null>(null);
  const [activeIndex, setActiveIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [selectedPoint, setSelectedPoint] = useState(initialPoint);
  const [queryResult, setQueryResult] = useState<LocationQueryResult | null>(null);
  const [querying, setQuerying] = useState(false);
  const [neighborhoodCells, setNeighborhoodCells] = useState<LocationNeighborhoodCell[]>([]);
  const [impactDrawer, setImpactDrawer] = useState<{ name: string; coordinates: { lat: number; lon: number }; result: LocationQueryResult } | null>(null);
  const queryGeneration = useRef(0);
  const [queryError, setQueryError] = useState<string | null>(null);
  const [forecastMode, setForecastMode] = useState<"BASELINE" | "LEARNED">("BASELINE");
  const [triageReport, setTriageReport] = useState<AssetTriageReport | null>(null);
  const [isochrones, setIsochrones] = useState<IsochroneReport | null>(null);
  const [showIsochrones, setShowIsochrones] = useState(true);
  const [intensification, setIntensification] = useState<IntensificationReport | null>(null);
  const [imdBridge, setImdBridge] = useState<IMDBridgeStatus | null>(null);
  const [learnedForecast, setLearnedForecast] = useState<LearnedGridForecast | null>(null);
  const [learnedError, setLearnedError] = useState<string | null>(null);
  const [learnedIndex, setLearnedIndex] = useState(0);
  const [gridMetadata, setGridMetadata] = useState<GridReplayMetadata | null>(null);
  const [gridFrame, setGridFrame] = useState<GridReplayFrame | null>(null);
  const [modelArtifacts, setModelArtifacts] = useState<ModelArtifact[]>([]);
  const [baseline, setBaseline] = useState<BaselineForecast | null>(null);
  const [verification, setVerification] = useState<VerificationReport | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [hoveredLearnedCell, setHoveredLearnedCell] = useState<LearnedGridForecast["frames"][number]["cells"][number] | null>(null);
  const [modalities, setModalities] = useState<MultimodalStatus | null>(null);
  const [baselineHazards, setBaselineHazards] = useState<HazardScreening | null>(null);
  const [learnedHazards, setLearnedHazards] = useState<HazardScreening | null>(null);
  const [gridIndex, setGridIndex] = useState(12);
  const [error, setError] = useState<string | null>(null);
  const { frame: radarFrame, status: radarStatus } = useRadarFrame(radarEnabled && replay ? replay.frames[activeIndex]?.offset_minutes ?? null : null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [telemetryResponse, sessionsResponse, gridResponse, modelsResponse, baselineResponse, modalitiesResponse, hazardsResponse] = await Promise.all([
          fetch("/api/v1/replay/telemetry"),
          fetch("/api/v1/replay/sessions"),
          fetch("/api/v1/replay/grid"),
          fetch("/api/v1/models"),
          fetch("/api/v1/replay/baseline"),
          fetch("/api/v1/replay/modalities"),
          fetch("/api/v1/replay/hazards?forecast_mode=BASELINE"),
        ]);
        if (!telemetryResponse.ok || !sessionsResponse.ok || !gridResponse.ok || !modelsResponse.ok || !baselineResponse.ok || !modalitiesResponse.ok || !hazardsResponse.ok) {
          throw new Error("Replay API returned an error.");
        }

        const nextTelemetry = (await telemetryResponse.json()) as TelemetrySnapshot;
        const sessions = (await sessionsResponse.json()) as ReplaySession[];
        const nextGridMetadata = (await gridResponse.json()) as GridReplayMetadata;
        const nextModelArtifacts = (await modelsResponse.json()) as ModelArtifact[];
        const nextBaseline = (await baselineResponse.json()) as BaselineForecast;
        const nextModalities = (await modalitiesResponse.json()) as MultimodalStatus;
        const nextHazards = (await hazardsResponse.json()) as HazardScreening;
        const nextReplay = sessions[0];
        if (!nextReplay) throw new Error("No replay event bundle is available.");

        setTelemetry(nextTelemetry);
        setReplay(nextReplay);
        setGridMetadata(nextGridMetadata);
        setModelArtifacts(nextModelArtifacts);
        setBaseline(nextBaseline);
        setModalities(nextModalities);
        setBaselineHazards(nextHazards);
        setGridIndex(nextGridMetadata.issue_index);
        setActiveIndex(Math.max(0, nextReplay.frames.findIndex((frame) => frame.offset_minutes === 0)));
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Replay API is unavailable.");
      }
    };

    void loadData();
  }, []);

  useEffect(() => {
    let cancelled = false;
    setVerification(null);
    setVerificationError(null);
    const source = forecastMode === "LEARNED" ? "SEVIR" : "SYNTHETIC";
    const loadVerification = async () => {
      try {
        const response = await fetch(`/api/v1/replay/verification?source=${source}`);
        if (!response.ok) throw new Error(`Verification unavailable (${response.status}).`);
        if (!cancelled) setVerification((await response.json()) as VerificationReport);
      } catch (caught) {
        if (!cancelled) setVerificationError(caught instanceof Error ? caught.message : "Verification unavailable.");
      }
    };
    void loadVerification();
    return () => { cancelled = true; };
  }, [forecastMode]);

  useEffect(() => {
    let cancelled = false;
    setIsochrones(null);
    const load = async () => {
      const response = await fetch(`/api/v1/replay/isochrones?forecast_mode=${forecastMode}`);
      if (response.ok && !cancelled) setIsochrones((await response.json()) as IsochroneReport);
    };
    void load().catch(() => { if (!cancelled) setIsochrones(null); });
    return () => { cancelled = true; };
  }, [forecastMode]);

  useEffect(() => {
    let cancelled = false;
    setIntensification(null);
    const load = async () => {
      const response = await fetch(`/api/v1/replay/intensification?frame_index=${activeIndex}&forecast_mode=${forecastMode}`);
      if (response.ok && !cancelled) setIntensification((await response.json()) as IntensificationReport);
    };
    void load().catch(() => { if (!cancelled) setIntensification(null); });
    return () => { cancelled = true; };
  }, [activeIndex, forecastMode]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      const response = await fetch("/api/v1/replay/imd-bridge");
      if (response.ok && !cancelled) setImdBridge((await response.json()) as IMDBridgeStatus);
    };
    void load().catch(() => { if (!cancelled) setImdBridge(null); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!gridMetadata) return;
    const loadFrame = async () => {
      const response = await fetch(`/api/v1/replay/grid/frames/${gridIndex}`);
      if (response.ok) setGridFrame((await response.json()) as GridReplayFrame);
    };
    void loadFrame();
  }, [gridIndex, gridMetadata]);

  useEffect(() => {
    if (forecastMode !== "LEARNED" || (learnedForecast && learnedHazards) || learnedError) return;
    let cancelled = false;
    const loadLearned = async () => {
      try {
        const [response, hazardsResponse] = await Promise.all([
          fetch("/api/v1/replay/grid/learned"),
          fetch("/api/v1/replay/hazards?forecast_mode=LEARNED"),
        ]);
        if (!response.ok || !hazardsResponse.ok) throw new Error(`ConvLSTM replay unavailable (${response.status}/${hazardsResponse.status}).`);
        const forecast = (await response.json()) as LearnedGridForecast;
        const hazards = (await hazardsResponse.json()) as HazardScreening;
        if (!cancelled) {
          setLearnedForecast(forecast);
          setLearnedHazards(hazards);
        }
      } catch (caught) {
        if (!cancelled) setLearnedError(caught instanceof Error ? caught.message : "ConvLSTM replay unavailable.");
      }
    };
    void loadLearned();
    return () => { cancelled = true; };
  }, [forecastMode, learnedForecast, learnedHazards, learnedError]);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      if (forecastMode === "LEARNED") {
        setLearnedIndex((current) => {
          if (current >= (learnedForecast?.frames.length ?? 1) - 1) {
            setPlaying(false);
            return current;
          }
          return current + 1;
        });
      } else if (replay) {
        setActiveIndex((current) => {
          if (current >= replay.frames.length - 1) {
            setPlaying(false);
            return current;
          }
          return current + 1;
        });
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [playing, replay, forecastMode, learnedForecast]);

  const activeFrame = replay?.frames[activeIndex] ?? null;
  const activeCell = activeFrame?.cells[0] ?? null;
  const hazardLead = forecastMode === "LEARNED" ? learnedForecast?.frames[learnedIndex]?.lead_minutes ?? 5 : 0;
  const hazardIndicators = (forecastMode === "LEARNED" ? learnedHazards : baselineHazards)?.indicators.filter(
    (indicator) => indicator.lead_minutes === hazardLead,
  ) ?? [];
  const visibleFrames = useMemo(
    () => replay?.frames.slice(0, activeIndex + 1) ?? [],
    [activeIndex, replay],
  );
  const track = useMemo(
    () =>
      visibleFrames.flatMap((frame) =>
        frame.cells.map((cell) => [cell.centroid.lat, cell.centroid.lon] as [number, number]),
      ),
    [visibleFrames],
  );
  const chartData = visibleFrames.map((frame) => ({
    t: formatOffset(frame.offset_minutes),
    reflectivity: frame.cells[0]?.max_reflectivity_dbz ?? 0,
    rain: frame.cells[0]?.rain_rate_mm_h ?? 0,
  }));
  const terminalLines = visibleFrames.flatMap((frame) =>
    frame.events.map((event) => ({ ...event, ts: formatOffset(frame.offset_minutes) })),
  );
  const forecastTrack = useMemo(
    () => baseline?.forecast_cells.map((cell) => [cell.centroid.lat, cell.centroid.lon] as [number, number]) ?? [],
    [baseline],
  );
  const firstIntersectingImpact = queryResult?.impacts.find((impact) =>
    impact.spatial_relation === "INTERSECTS" || impact.spatial_relation === "WITHIN",
  ) ?? null;
  const computedEta = queryResult?.impacts
    .map((impact) => impact.eta.eta_minutes)
    .filter((eta): eta is number => eta !== null)
    .sort((a, b) => a - b)[0];
  const alreadyArrived = queryResult?.impacts.some((impact) => impact.eta.status === "ARRIVED") ?? false;
  const etaNotComputable = queryResult?.status === "NOT_COMPUTABLE" ||
    queryResult?.impacts.some((impact) => impact.eta.status === "NOT_COMPUTABLE");
  const queryIntersection = queryResult?.status === "COMPUTED"
    ? firstIntersectingImpact ? "INTERSECTS" : "CLEAR"
    : queryResult?.status === "NOT_COMPUTABLE" || forecastMode === "LEARNED" ? "N/C" : "PENDING";
  const etaLabel = computedEta !== undefined
    ? `T+${computedEta.toFixed(1)}m`
    : alreadyArrived ? "ARRIVED" : etaNotComputable || forecastMode === "LEARNED" ? "N/C" : queryResult?.status === "COMPUTED" ? "UNKNOWN" : "N/A";
  const verificationLabel = verification?.source === "SEVIR" ? "SEVIR FLOW BENCHMARK / NOT CONVLSTM" : "SIMULATED REPLAY BENCHMARK";
  const verificationDetail = verification
    ? `${verification.method} / ${verification.field} >= ${verification.threshold} ${verification.threshold_unit} / ${verification.observation_source} / T+${verification.leads.map((lead) => lead.lead_minutes).join(",") || "NONE"}`
    : verificationError ?? "Replay verification loading";
  const intensityCell = intensification?.cells[0] ?? null;
  const rapidIntensification = intensityCell?.tag === "RAPID_INTENSIFICATION";

  const runPointQuery = async () => {
    if (!replay) return;
    const generation = ++queryGeneration.current;
    setQueryResult(null);
    setQueryError(null);
    setNeighborhoodCells([]);
    setImpactDrawer(null);
    setQuerying(true);
    const locationName = locationNameFor(selectedPoint);
    try {
      const pointResult = await submitLocationQuery({
        geometry_type: "POINT",
        geometry: { longitude: selectedPoint.lon, latitude: selectedPoint.lat },
        coordinate_reference_system: "EPSG:4326",
        name: locationName,
        source_of_location: "MAP_CLICK",
        issue_time: replay.issue_time,
        horizon_minutes: replay.horizon_minutes,
        forecast_mode: forecastMode,
      });
      if (generation !== queryGeneration.current) return;
      setQueryResult(pointResult);

      const cells = createNeighborhood(selectedPoint);
      if (forecastMode === "LEARNED" || pointResult.status === "NOT_COMPUTABLE") {
        setNeighborhoodCells(cells.map((cell) => ({ ...cell, status: "NOT_COMPUTABLE", result: null })));
      } else {
        setNeighborhoodCells(cells.map((cell) => ({ ...cell, status: "LOADING", result: null })));
        const outcomes = await Promise.allSettled(cells.map((cell) => submitLocationQuery({
          geometry_type: "POLYGON",
          geometry: { vertices: squarePolygon(cell.center) },
          coordinate_reference_system: "EPSG:4326",
          name: `${cell.label} 1 km neighborhood cell`,
          source_of_location: "MAP_NEIGHBORHOOD_MATRIX",
          issue_time: replay.issue_time,
          horizon_minutes: replay.horizon_minutes,
          forecast_mode: "BASELINE",
        })));
        if (generation !== queryGeneration.current) return;
        setNeighborhoodCells(cells.map((cell, index) => {
          const outcome = outcomes[index];
          return outcome.status === "fulfilled"
            ? { ...cell, status: outcome.value.status, result: outcome.value }
            : { ...cell, status: "ERROR", result: null, error: outcome.reason instanceof Error ? outcome.reason.message : "Query failed" };
        }));
      }
    } catch (caught) {
      if (generation === queryGeneration.current) setQueryError(caught instanceof Error ? caught.message : "Location query failed.");
    } finally {
      if (generation === queryGeneration.current) setQuerying(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#090d16] text-slate-100 xl:h-screen xl:overflow-hidden">
        <section className="flex min-h-screen min-w-0 flex-1 flex-col xl:h-full">
          <header className="flex min-h-[86px] shrink-0 flex-wrap items-center gap-3 border-b border-cyan-900/30 bg-slate-950/50 px-5 py-3 backdrop-blur-xl">
            <div className="mr-auto min-w-[260px]">
              <div className="flex items-center gap-3">
                <Radar className="h-6 w-6 text-cyan-300" />
                <h1 className="text-xl font-black uppercase tracking-[0.3em] text-slate-100">VAJRA</h1>
                <StatusTag>{forecastMode === "LEARNED" ? "LEARNED / UNVALIDATED" : telemetry?.evidence_status ?? "LOADING"}</StatusTag>
              </div>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                {forecastMode === "LEARNED" ? "SEVIR VIL learned replay / U.S. benchmark / pixel space" : `Location-first convective intelligence / ${replay?.region ?? "event bundle loading"}`}
              </p>
            </div>
            <HudMetric icon={Gauge} label="CSI Score" value={verification?.status === "COMPUTED" ? formatMetric(verification.csi) : "--"} unit={verification?.source === "SEVIR" ? "SEVIR FLOW" : verification ? "SIM REPLAY" : "UNVALIDATED"} title={verificationDetail} tone="amber" />
            <HudMetric icon={Activity} label="POD Matrix" value={verification?.status === "COMPUTED" ? formatMetric(verification.pod) : "--"} unit="UNVALIDATED" title={verificationDetail} tone="amber" />
            <HudMetric icon={Crosshair} label="Target Horizon" value={forecastMode === "LEARNED" ? "60" : telemetry ? String(telemetry.horizon_minutes) : "---"} unit="MIN" />
            <HudMetric icon={Activity} label="Intensity Delta" value={intensityCell ? `${intensityCell.rate_dbz_per_hour >= 0 ? "+" : ""}${intensityCell.rate_dbz_per_hour.toFixed(1)}` : "N/C"} unit={rapidIntensification ? "dBZ/HR / RAPID" : "dBZ/HR"} title={intensification ? `${intensification.method} / ${intensification.evidence_status} / ${intensification.observation_role} / threshold >${intensification.threshold_dbz_per_hour} dBZ/hr` : "No adjacent observed cell frames"} tone={rapidIntensification ? "amber" : "cyan"} />
            {forecastMode === "LEARNED" ? (
              <HudMetric icon={Cpu} label="Model" value={learnedForecast ? "LOADED" : "---"} unit="UNVALIDATED" tone="amber" />
            ) : (
              <HudMetric
                icon={Satellite}
                label="Source Health"
                value={telemetry ? `${telemetry.available_sources}/${telemetry.total_sources}` : "--/--"}
                unit={telemetry?.mode ?? "REPLAY"}
                tone="emerald"
              />
            )}
            <button type="button" onClick={() => setScorecardOpen(true)} className="h-10 shrink-0 border border-cyan-700/70 bg-cyan-950/30 px-3 text-[11px] font-semibold text-cyan-100 hover:bg-cyan-900/40">WMO Scorecard</button>
          </header>

          <nav aria-label="Operational workspaces" className="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-700 bg-[#0f172a] px-4 py-2">
            {workspaces.map((item) => { const Icon = item.icon; return <button key={item.id} type="button" aria-current={workspace === item.id ? "page" : undefined} onClick={() => { setWorkspace(item.id); setPlaying(false); }} className={`flex shrink-0 items-center gap-2 border px-3 py-2 text-[11px] font-semibold transition-colors ${workspace === item.id ? "border-cyan-700 bg-cyan-900/30 text-cyan-100" : "border-transparent text-slate-400 hover:border-slate-700 hover:text-slate-100"}`}><Icon size={15} />{item.label}</button>; })}
          </nav>

          {error ? (
            <div className="m-4 border border-rose-800 bg-rose-950/20 p-4 font-mono text-sm text-rose-200">
              BACKEND DEGRADED: {error}
            </div>
          ) : null}

          {workspace === "spatial" ? <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 xl:grid-cols-[minmax(0,1fr)_360px] xl:grid-rows-[minmax(0,1fr)_270px]">
            <Panel className="relative min-h-[430px] overflow-hidden xl:col-span-1 xl:row-span-1 xl:min-h-0">
              <div className="absolute left-4 top-4 z-[500] flex items-center gap-3 border border-cyan-900/40 bg-slate-950/85 px-3 py-2 backdrop-blur-xl">
                <MapPinned className="h-4 w-4 text-cyan-300" />
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{forecastMode === "LEARNED" ? "SEVIR / Predicted VIL" : "GIS / Replay Observation"}</p>
                  <p className="font-mono text-xs text-cyan-100">
                    {forecastMode === "LEARNED" ? "AI FIELD: PIXEL SPACE ONLY" : activeCell ? `${activeCell.centroid.lat.toFixed(3)} / ${activeCell.centroid.lon.toFixed(3)}` : "NO FRAME"}
                  </p>
                </div>
                {forecastMode === "BASELINE" ? <button type="button" title="Toggle forecast isochrone bands" aria-label="Toggle forecast isochrone bands" aria-pressed={showIsochrones} onClick={() => setShowIsochrones((shown) => !shown)} className={`border p-1.5 ${showIsochrones ? "border-cyan-500/60 text-cyan-200" : "border-slate-700 text-slate-500"}`}><Layers3 className="h-4 w-4" /></button> : null}
              </div>
              {forecastMode === "BASELINE" && isochrones?.status === "COMPUTED" && showIsochrones ? (
                <div className="pointer-events-none absolute left-4 top-[74px] z-[500] border border-cyan-900/40 bg-slate-950/90 px-2 py-1 font-mono text-[9px] text-slate-200">
                  <span className="mr-2 text-red-300">T+10</span><span className="mr-2 text-amber-300">T+20</span><span className="text-cyan-300">T+30</span><span className="ml-2 text-slate-500">SWEPT / SIMULATED</span>
                </div>
              ) : null}
              <div className="pointer-events-none absolute right-4 top-[72px] z-[500] max-w-[45%] border border-amber-500/30 bg-slate-950/90 px-2 py-1 text-right font-mono text-[9px] text-amber-200 lg:top-4">
                {forecastMode === "LEARNED" ? "VIL_ONLY_FALLBACK / NO WGS84 ETA" : queryResult?.status === "NOT_COMPUTABLE" ? "NOT_COMPUTABLE / LOCATION GATED" : "SIMULATED / WGS84"}
              </div>

              {forecastMode === "LEARNED" ? (
                <div className="relative h-full w-full bg-[#020617]">
                  <GridFieldPreview frame={learnedForecast?.frames[learnedIndex] ?? null} className="h-full w-full" />
                  {learnedForecast?.frames[learnedIndex] ? (
                    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 96 96" preserveAspectRatio="none" aria-label="Tracked predicted cells">
                      {learnedForecast.frames[learnedIndex].cells.map((cell) => (
                        <circle key={cell.cell_id} cx={cell.centroid_x} cy={cell.centroid_y} r={cell.radius_pixels} fill="transparent" stroke="#fbbf24" strokeWidth="0.6" style={{ pointerEvents: "auto" }} onMouseEnter={() => setHoveredLearnedCell(cell)} onMouseLeave={() => setHoveredLearnedCell(null)} />
                      ))}
                    </svg>
                  ) : null}
                  {hoveredLearnedCell ? (
                    <div className="pointer-events-none absolute z-[450] w-[220px] border border-amber-500/50 bg-slate-950/95 p-2 font-mono text-[10px] text-slate-200" style={{ left: `${Math.min(68, hoveredLearnedCell.centroid_x / 96 * 100)}%`, top: `${Math.max(20, Math.min(70, hoveredLearnedCell.centroid_y / 96 * 100))}%` }}>
                      <p className="font-bold text-amber-300">{hoveredLearnedCell.cell_id}</p>
                      <p>VIL / {learnedForecast?.model_version}</p>
                      <p>PIXEL {hoveredLearnedCell.centroid_x.toFixed(1)}, {hoveredLearnedCell.centroid_y.toFixed(1)} / R {hoveredLearnedCell.radius_pixels.toFixed(1)} PX</p>
                      <p>LEARNED_FORECAST / VIL_ONLY_FALLBACK</p>
                      <p className="text-amber-300">NOT_COMPUTABLE / NO WGS84 ETA</p>
                    </div>
                  ) : null}
                </div>
              ) : (
              <MapContainer center={[20.3, 85.82]} zoom={9} scrollWheelZoom className="z-0">
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" subdomains={["a", "b", "c"]} />
                {radarEnabled && radarFrame?.offset_minutes === activeFrame?.offset_minutes ? <RadarFieldLayer frame={radarFrame} opacity={radarOpacity} /> : null}
                <MapClickSelector onSelect={(point) => { queryGeneration.current += 1; setSelectedPoint(point); setQuerying(false); setQueryResult(null); setQueryError(null); setNeighborhoodCells([]); setImpactDrawer(null); }} />
                {showIsochrones && isochrones?.status === "COMPUTED" ? <IsochroneMapBands report={isochrones} /> : null}
                {forecastMode === "BASELINE" && track.length > 1 ? <Polyline positions={track} pathOptions={{ color: "#67e8f9", weight: 2, opacity: 0.9 }}><TacticalMapTooltip title="OBSERVED TRACK" rows={[`EVENT ${replay?.event_id ?? "--"}`, "METHOD: SYNTHETIC_REPLAY_OBSERVATION", "EVIDENCE: SIMULATED", `FRAMES: ${visibleFrames.length}`]} /></Polyline> : null}
                {forecastMode === "BASELINE" && forecastTrack.length > 1 ? <Polyline positions={forecastTrack} pathOptions={{ color: "#fbbf24", weight: 2, opacity: 0.9, dashArray: "6 8" }}><TacticalMapTooltip title="BASELINE TRAJECTORY" rows={[`METHOD: ${baseline?.method ?? "--"}`, "EVIDENCE: SIMULATED", "HORIZON: T+5 TO T+60 MIN", "NO GROWTH / DECAY"]} /></Polyline> : null}
                {forecastMode === "BASELINE" ? baseline?.current_cells.map((cell) => (
                  <Polygon
                    key={cell.cell_id}
                    positions={cell.polygon.map((point) => [point.lat, point.lon])}
                    pathOptions={{ color: "#fbbf24", fillColor: "#fbbf24", fillOpacity: 0.08, weight: 1.5, dashArray: "4 4" }}
                  >
                    <TacticalMapTooltip title={`TRACKED CELL ${cell.cell_id}`} rows={["DETECT: QC + >=30 dBZ COMPONENTS", "TRACK: COST-MATRIX ASSIGNMENT", "EVIDENCE: SIMULATED", `PEAK: ${cell.max_reflectivity_dbz.toFixed(1)} dBZ`, `AREA: ${cell.area_km2?.toFixed(1) ?? "--"} KM2`, `QC GRID REMOVED: ${cell.qc_removed_pixels ?? "--"} PX`, `CENTER: ${cell.centroid.lat.toFixed(4)}, ${cell.centroid.lon.toFixed(4)}`]} />
                  </Polygon>
                )) : null}
                {forecastMode === "BASELINE" && activeCell ? (
                  <CircleMarker
                    center={[activeCell.centroid.lat, activeCell.centroid.lon]}
                    radius={15}
                    pathOptions={{ color: "#fb7185", fillColor: "#fb7185", fillOpacity: 0.18, weight: 2 }}
                  >
                    <TacticalMapTooltip title={`OBSERVATION ${activeCell.cell_id}`} rows={[`FRAME: ${activeFrame?.frame_id ?? "--"}`, `VALID: ${activeFrame?.valid_time ?? "--"}`, `PEAK: ${activeCell.max_reflectivity_dbz.toFixed(1)} dBZ`, "METHOD: SYNTHETIC_REPLAY_OBSERVATION", "EVIDENCE: SIMULATED"]} />
                  </CircleMarker>
                ) : null}
                {triageReport && triageReport.issue_time === replay?.issue_time ? triageReport.assets.map((asset) => (
                  <CircleMarker key={asset.asset_id} center={[asset.centroid.lat, asset.centroid.lon]} radius={5} pathOptions={{ color: asset.eta_status === "COMPUTED" || asset.eta_status === "ARRIVED" ? "#fb7185" : "#67e8f9", fillOpacity: 0.6, weight: 1.5 }}>
                    <TacticalMapTooltip title={asset.name.toUpperCase()} rows={[`ASSET: ${asset.asset_id}`, `ETA: ${asset.eta_minutes !== null ? `T+${asset.eta_minutes.toFixed(1)} MIN` : asset.eta_status}`, `EVIDENCE: ${asset.result.evidence_status}`, `METHOD: ${triageReport.method}`]} />
                  </CircleMarker>
                )) : null}
                <CircleMarker
                  center={[selectedPoint.lat, selectedPoint.lon]}
                  radius={7}
                  pathOptions={{ color: "#34d399", fillColor: "#34d399", fillOpacity: 0.35, weight: 2 }}
                >
                  <TacticalMapTooltip title="LOCATION QUERY POINT" rows={[`WGS84: ${selectedPoint.lat.toFixed(5)}, ${selectedPoint.lon.toFixed(5)}`, `INTERSECTION: ${queryIntersection}`, `ETA: ${etaLabel}`, "METHOD: STRICT_SPATIAL_INTERSECTION"]} />
                </CircleMarker>
              </MapContainer>
              )}

              {forecastMode === "BASELINE" ? <LayerController radarEnabled={radarEnabled} onRadarEnabled={setRadarEnabled} opacity={radarOpacity} onOpacity={setRadarOpacity} radarStatus={radarEnabled ? radarStatus : "SIMULATED REPLAY AVAILABLE"} /> : null}

              <div className="radar-grid pointer-events-none absolute inset-0 z-[400] opacity-70" />
              <div className="pointer-events-none absolute inset-x-1/2 top-0 z-[410] h-full border-l border-cyan-300/20" />
              <div className="pointer-events-none absolute inset-y-1/2 left-0 z-[410] w-full border-t border-cyan-300/20" />
              {forecastMode === "BASELINE" ? <div className="pointer-events-none absolute left-1/2 top-1/2 z-[420] h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan-300/30" /> : null}

              <div className="absolute inset-x-4 bottom-4 z-[500] border border-cyan-900/40 bg-slate-950/90 p-3 backdrop-blur-xl">
                <div className="flex items-center gap-3">
                  <IconButton label={forecastMode === "LEARNED" ? "First forecast frame" : "Return to issue time"} onClick={() => forecastMode === "LEARNED" ? setLearnedIndex(0) : replay && setActiveIndex(Math.max(0, replay.frames.findIndex((frame) => frame.offset_minutes === 0)))}>
                    <SkipBack className="h-4 w-4" />
                  </IconButton>
                  <IconButton label={playing ? "Pause replay" : "Play replay"} onClick={() => setPlaying((value) => !value)}>
                    {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                  </IconButton>
                  <IconButton label="Advance one frame" onClick={() => forecastMode === "LEARNED" ? setLearnedIndex((value) => Math.min((learnedForecast?.frames.length ?? 1) - 1, value + 1)) : replay && setActiveIndex((value) => Math.min(replay.frames.length - 1, value + 1))}>
                    <SkipForward className="h-4 w-4" />
                  </IconButton>
                  <input
                    aria-label={forecastMode === "LEARNED" ? "Learned forecast timeline" : "Replay timeline"}
                    type="range"
                    min={0}
                    max={forecastMode === "LEARNED" ? Math.max(0, (learnedForecast?.frames.length ?? 1) - 1) : Math.max(0, (replay?.frames.length ?? 1) - 1)}
                    value={forecastMode === "LEARNED" ? learnedIndex : activeIndex}
                    onChange={(event) => forecastMode === "LEARNED" ? setLearnedIndex(Number(event.target.value)) : setActiveIndex(Number(event.target.value))}
                    className="min-w-0 flex-1 accent-cyan-400"
                  />
                  <div className="min-w-[74px] text-right font-mono text-sm font-bold text-[#00F0FF]">
                    {forecastMode === "LEARNED" ? learnedForecast ? `T+${String(learnedForecast.frames[learnedIndex]?.lead_minutes ?? 5).padStart(3, "0")}` : "T---" : activeFrame ? formatOffset(activeFrame.offset_minutes) : "T---"}
                  </div>
                </div>
              </div>
            </Panel>

            <Panel className="flex min-h-0 flex-col gap-4 overflow-y-auto p-4 xl:row-span-2">
              <SectionHeader icon={Route} label="Location Query" status={forecastMode === "LEARNED" ? "VIL-only / unvalidated" : "Simulated baseline"} />
              <div className="grid grid-cols-2 border border-cyan-900/30 bg-slate-950/50 p-1" role="group" aria-label="Forecast model">
                <button type="button" aria-pressed={forecastMode === "BASELINE"} onClick={() => { queryGeneration.current += 1; setForecastMode("BASELINE"); setPlaying(false); setQuerying(false); setQueryResult(null); setQueryError(null); setNeighborhoodCells([]); setImpactDrawer(null); }} className={`px-2 py-2 text-[10px] font-bold uppercase text-center ${forecastMode === "BASELINE" ? "bg-cyan-950/70 text-[#00F0FF]" : "text-slate-500"}`}>Baseline</button>
                <button type="button" aria-pressed={forecastMode === "LEARNED"} onClick={() => { queryGeneration.current += 1; setForecastMode("LEARNED"); setPlaying(false); setQuerying(false); setQueryResult(null); setQueryError(null); setNeighborhoodCells([]); setImpactDrawer(null); }} className={`px-2 py-2 text-[10px] font-bold uppercase text-center ${forecastMode === "LEARNED" ? "bg-amber-950/50 text-amber-300" : "text-slate-500"}`}>ConvLSTM</button>
              </div>
              <div className="border border-cyan-900/30 bg-slate-950/40 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Selected point</p>
                    <p className="mt-2 font-mono text-xl font-black text-[#00F0FF]">
                      {selectedPoint.lat === initialPoint.lat && selectedPoint.lon === initialPoint.lon ? "JAYDEV VIHAR" : "MAP SELECTION"}
                    </p>
                  </div>
                  <MapPin className="h-5 w-5 text-[#39FF14]" />
                </div>
                <p className="mt-3 font-mono text-xs text-slate-300">
                  {selectedPoint.lat.toFixed(5)} / {selectedPoint.lon.toFixed(5)}
                </p>
                <button
                  type="button"
                  onClick={() => void runPointQuery()}
                  disabled={!replay || querying}
                  className="mt-4 flex w-full items-center justify-center gap-2 border border-cyan-400/60 bg-cyan-950/30 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-100 transition hover:bg-cyan-900/30 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  <Crosshair className="h-4 w-4" /> {querying ? "Calculating" : forecastMode === "LEARNED" ? "Check learned location" : "Query point + 3x3 neighborhood"}
                </button>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <IntelStat label="Intersection" value={queryIntersection} tone={forecastMode === "LEARNED" ? "amber" : "emerald"} />
                <IntelStat label="ETA" value={etaLabel} tone={forecastMode === "LEARNED" ? "amber" : "emerald"} />
              </div>

              {queryResult ? (
                <div className="flex items-center justify-between gap-3 border border-slate-800 bg-slate-950/40 px-3 py-2">
                  <div className="min-w-0">
                    <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-slate-500">Location briefing</p>
                    <p className="mt-1 truncate font-mono text-[10px] text-slate-200">{queryResult.evidence_status} / {queryResult.status} / {queryResult.impacts.length} impacts</p>
                  </div>
                  <button type="button" onClick={() => setImpactDrawer({ name: locationNameFor(selectedPoint), coordinates: selectedPoint, result: queryResult })} className="flex shrink-0 items-center gap-1.5 border border-cyan-800/60 px-2 py-1.5 font-mono text-[9px] font-bold uppercase text-cyan-200 hover:bg-cyan-950/40">
                    <PanelRightOpen className="h-3.5 w-3.5" /> Inspect report
                  </button>
                </div>
              ) : null}

              <LocationNeighborhoodMatrix
                cells={neighborhoodCells}
                onInspect={(cell) => cell.result && setImpactDrawer({ name: `${cell.label} neighborhood cell`, coordinates: cell.center, result: cell.result })}
              />

              <ThreatTriageBoard
                issueTime={replay?.issue_time ?? null}
                horizonMinutes={replay?.horizon_minutes ?? 60}
                forecastMode={forecastMode}
                onReport={setTriageReport}
                onInspect={(asset) => setImpactDrawer({ name: asset.name, coordinates: asset.centroid, result: asset.result })}
              />

              <div className={`border p-3 ${rapidIntensification ? "border-red-500/50 bg-red-950/20" : "border-slate-800 bg-slate-950/40"}`}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">Rapid intensification / RID</p>
                  <span className={`font-mono text-[9px] ${rapidIntensification ? "text-red-300" : "text-amber-300"}`}>{rapidIntensification ? "RAPID_INTENSIFICATION" : intensification?.status ?? "LOADING"}</span>
                </div>
                <p className="mt-2 font-mono text-sm text-slate-100">Calculated Intensity Delta: {intensityCell ? `${intensityCell.rate_dbz_per_hour >= 0 ? "+" : ""}${intensityCell.rate_dbz_per_hour.toFixed(1)} dBZ/hr` : "NOT_COMPUTABLE"}</p>
                <p className="mt-1 break-words font-mono text-[9px] text-slate-500">{intensification ? `${intensification.method} / ${intensification.evidence_status} / ${intensification.observation_role} / >${intensification.threshold_dbz_per_hour} dBZ/hr` : "ADJACENT OBSERVATION REQUIRED"}</p>
              </div>

              <div className="border border-slate-800 bg-slate-950/40 p-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Scientific gate</p>
                <p className="mt-2 text-xs leading-5 text-slate-300">
                  {queryError ?? queryResult?.message ?? (forecastMode === "LEARNED"
                    ? "ConvLSTM output is a U.S. SEVIR pixel field without India georeferencing. A Jaydev ETA remains gated."
                    : "Select a map point to intersect it with the simulated constant-velocity replay baseline.")}
                </p>
              </div>

              <div className="border border-cyan-900/30 bg-slate-950/40 p-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">Hazard screens / T+{hazardLead}</p>
                  <span className="font-mono text-[9px] text-amber-300">UNCALIBRATED</span>
                </div>
                <div className="mt-2 divide-y divide-slate-800">
                  {hazardIndicators.length ? hazardIndicators.map((indicator) => (
                    <div key={`${indicator.cell_id}-${indicator.lead_minutes}-${indicator.indicator}`} className="py-2 first:pt-0 last:pb-0">
                      <div className="flex items-start justify-between gap-2 font-mono text-[10px]">
                        <span className="min-w-0 break-words text-slate-200">{indicator.indicator.replaceAll("_", " ")}</span>
                        <span className={`shrink-0 ${indicator.state === "THRESHOLD_MET" ? "text-amber-300" : "text-slate-500"}`}>
                          {indicator.state === "THRESHOLD_MET" ? `${indicator.value?.toFixed(indicator.unit === "dBZ" ? 1 : 3)} ${indicator.unit}` : indicator.state.replaceAll("_", " ")}
                        </span>
                      </div>
                      <p className="mt-1 break-words font-mono text-[9px] text-slate-500">
                        {indicator.method} / {indicator.evidence_status} / {indicator.derivation_status}
                        {indicator.threshold !== null ? ` / threshold ${indicator.threshold} ${indicator.unit}` : ""}
                      </p>
                      <p className="mt-1 text-[10px] leading-4 text-slate-400">{indicator.reason}</p>
                    </div>
                  )) : <p className="py-2 font-mono text-[10px] text-slate-500">{forecastMode === "LEARNED" && !learnedForecast ? "WAITING FOR MODEL" : "NO TRACKED CELLS"}</p>}
                </div>
              </div>

              {queryResult?.status === "COMPUTED" ? (
                <div className="border border-amber-500/30 bg-amber-950/10 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">Baseline impact timeline</p>
                    <StatusTag>SIMULATED</StatusTag>
                  </div>
                  <div className="mt-3 space-y-1.5 font-mono text-[10px]">
                    {queryResult.impacts.map((impact) => (
                      <div key={`${impact.cell_id}-${impact.valid_time}`} className="grid grid-cols-[44px_1fr_auto] items-center gap-2 border-b border-slate-800/80 pb-1.5 last:border-b-0 last:pb-0">
                        <span className="text-cyan-200">{formatLeadTime(impact.valid_time, replay?.issue_time)}</span>
                        <span className={impact.spatial_relation === "INTERSECTS" || impact.spatial_relation === "WITHIN" ? "text-[#39FF14]" : "text-slate-400"}>{impact.spatial_relation}</span>
                        <span className="text-right text-slate-500">
                          {impact === firstIntersectingImpact && impact.eta.status === "COMPUTED"
                            ? `ETA ${impact.eta.eta_minutes?.toFixed(1)}m`
                            : impact.spatial_relation === "INTERSECTS" || impact.spatial_relation === "WITHIN"
                              ? `${impact.value?.toFixed(0) ?? "--"} dBZ`
                              : impact.distance_km !== null ? `${impact.distance_km.toFixed(1)} km` : "--"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="border border-cyan-900/30 bg-slate-950/50 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{forecastMode === "LEARNED" ? "ConvLSTM VIL Prediction" : "SEVIR VIL Replay"}</p>
                    <p className="mt-1 font-mono text-[10px] text-cyan-200">{gridMetadata?.sample_id ?? "LOADING"} / UNGEOREFERENCED</p>
                  </div>
                  <StatusTag>{forecastMode === "LEARNED" ? "UNVALIDATED" : gridMetadata?.evidence_status ?? "LOADING"}</StatusTag>
                </div>
                <GridFieldPreview frame={forecastMode === "LEARNED" ? learnedForecast?.frames[learnedIndex] ?? null : gridFrame} />
                {forecastMode === "LEARNED" && learnedError ? <p className="mt-2 text-xs text-[#FF003C]">{learnedError}</p> : null}
                <div className="mt-2 flex items-center gap-3">
                  <input
                    aria-label={forecastMode === "LEARNED" ? "ConvLSTM forecast frame" : "SEVIR replay frame"}
                    type="range"
                    min={0}
                    max={forecastMode === "LEARNED" ? Math.max(0, (learnedForecast?.frames.length ?? 1) - 1) : Math.max(0, (gridMetadata?.frame_count ?? 1) - 1)}
                    value={forecastMode === "LEARNED" ? learnedIndex : gridIndex}
                    onChange={(event) => forecastMode === "LEARNED" ? setLearnedIndex(Number(event.target.value)) : setGridIndex(Number(event.target.value))}
                    className="min-w-0 flex-1 accent-cyan-400"
                  />
                  <span className="min-w-[58px] text-right font-mono text-[10px] text-[#00F0FF]">
                    {forecastMode === "LEARNED" ? learnedForecast ? `T+${String(learnedForecast.frames[learnedIndex]?.lead_minutes ?? 5).padStart(3, "0")}` : "T---" : gridFrame ? formatOffset(gridFrame.offset_minutes) : "T---"}
                  </span>
                </div>
                {forecastMode === "LEARNED" && learnedForecast ? <p className="mt-2 font-mono text-[10px] text-amber-300">{learnedForecast.model_version} / {learnedForecast.frames[learnedIndex]?.cells.length ?? 0} pixel-space cells</p> : null}
              </div>

              <SectionHeader icon={CloudLightning} label="Sources / Model Registry" status={baseline?.evidence_status ?? "LOADING"} />
              <div className="min-h-0 flex-1 overflow-y-auto border border-slate-800 bg-slate-950/40">
                {imdBridge ? (
                  <details className="border-b border-amber-500/30 bg-amber-950/10 px-3 py-2 font-mono text-[10px]">
                    <summary className="cursor-pointer text-amber-200">IMD DWR / MOSDAC API [{imdBridge.state.replaceAll("_", " ")}]</summary>
                    <p className="mt-2 text-slate-400">DISCONNECTED / NO AUTHORIZED PRODUCT</p>
                    <ol className="mt-2 space-y-1 text-slate-400">{imdBridge.pipeline_steps.map((step, index) => <li key={step}>{index + 1}. {step}</li>)}</ol>
                    <p className="mt-2 text-amber-300">{imdBridge.required_gates.join(" / ")}</p>
                  </details>
                ) : null}
                {modalities ? <div className="border-b border-cyan-900/30 bg-cyan-950/10 px-3 py-2 font-mono text-[10px] text-cyan-200">{modalities.fusion_mode.replaceAll("_", " ")} / INPUT {modalities.model_input_channels.join(", ")}</div> : null}
                {modalities?.modalities.map((modality) => (
                  <div key={modality.source_id} className="border-b border-slate-800 px-3 py-2">
                    <div className="flex items-start justify-between gap-2 font-mono text-[10px]">
                      <span className="text-slate-200">{modality.source_id}</span>
                      <span className={modality.role === "MODEL_INPUT" ? "text-emerald-300" : "text-amber-300"}>{modality.role.replaceAll("_", " ")}</span>
                    </div>
                    <p className="mt-1 text-[10px] leading-4 text-slate-500">{modality.reason}</p>
                  </div>
                ))}
                {replay?.sources.map((source) => (
                  <div key={source.source_id} className="flex items-center gap-3 border-b border-slate-800 px-3 py-3 last:border-b-0">
                    <span className={`h-2 w-2 shrink-0 rounded-full ${source.availability === "AVAILABLE" ? "bg-emerald-400" : "bg-amber-400"}`} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[11px] font-bold uppercase text-slate-200">{source.name}</p>
                      <p className="mt-1 font-mono text-[10px] text-slate-500">{source.modality} / {source.quality_status}</p>
                    </div>
                    <span className={`font-mono text-[10px] ${source.availability === "AVAILABLE" ? "text-emerald-300" : "text-amber-300"}`}>{source.availability}</span>
                  </div>
                ))}
                {modelArtifacts.map((model) => (
                  <div key={model.model_id} className="flex items-center gap-3 border-b border-slate-800 px-3 py-3 last:border-b-0">
                    <span className="h-2 w-2 shrink-0 bg-amber-300" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-mono text-[11px] font-bold uppercase text-slate-200">{model.model_id}</p>
                      <p className="mt-1 truncate font-mono text-[10px] text-slate-500">
                        {model.architecture} / {model.parameter_count.toLocaleString()} PARAMETERS
                      </p>
                    </div>
                    <span className="font-mono text-[9px] text-amber-200">UNVALIDATED</span>
                  </div>
                ))}
              </div>
            </Panel>

            <Panel className="grid min-h-[260px] grid-cols-1 gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_420px] xl:min-h-0">
              <div className="min-w-0">
                <SectionHeader icon={BarChart3} label={forecastMode === "LEARNED" ? "Simulated India Replay" : "Observed Replay Fields"} status="Backend event bundle" />
                <p className="mt-2 truncate font-mono text-[10px] text-amber-300" title={verificationDetail}>{verificationLabel} / {verification?.status ?? (verificationError ? "UNVALIDATED" : "CALCULATING")} / {verification?.forecast_validation_status ?? "UNVALIDATED"} / {verification?.leads.length ?? 0} LEADS</p>
                <div className="mt-2 h-[170px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="reflectivityGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#00F0FF" stopOpacity={0.55} />
                          <stop offset="95%" stopColor="#00F0FF" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="rainGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#fb7185" stopOpacity={0.35} />
                          <stop offset="95%" stopColor="#fb7185" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid stroke="rgba(8,145,178,0.18)" strokeDasharray="3 6" />
                      <XAxis dataKey="t" stroke="#64748b" tick={{ fontSize: 10, fontFamily: "monospace" }} />
                      <YAxis stroke="#64748b" tick={{ fontSize: 10, fontFamily: "monospace" }} />
                      <Tooltip contentStyle={{ background: "rgba(2,6,23,0.94)", border: "1px solid rgba(8,145,178,0.35)", borderRadius: 0, color: "#e2e8f0", fontFamily: "monospace" }} />
                      <Area type="monotone" dataKey="reflectivity" name="Reflectivity dBZ" stroke="#00F0FF" fill="url(#reflectivityGradient)" strokeWidth={2} />
                      <Area type="monotone" dataKey="rain" name="Rain rate mm/h" stroke="#fb7185" fill="url(#rainGradient)" strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="min-w-0 border border-slate-800 bg-black/30">
                <div className="flex items-center gap-2 border-b border-slate-800 px-3 py-2">
                  <TerminalSquare className="h-4 w-4 text-[#39FF14]" />
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">Simulated Event Log</p>
                </div>
                <div className="h-[196px] overflow-y-auto p-3 font-mono text-[11px] leading-5">
                  {terminalLines.map((line, index) => (
                    <p key={`${line.ts}-${index}`} className={line.level === "WARNING" || line.level === "CRITICAL" ? "text-rose-300" : "text-emerald-300"}>
                      <span className="text-slate-500">{line.ts}</span> [{line.source_id.toUpperCase()}] {line.message}
                    </p>
                  ))}
                  <p className="animate-pulse text-[#39FF14]">&gt; deterministic replay ready_</p>
                </div>
              </div>
            </Panel>
          </div> : workspace === "verification" ? <DualSplitVerification forecastCells={baseline?.forecast_cells ?? []} currentCells={baseline?.current_cells ?? []} isochrones={isochrones} forecastMode={forecastMode} observedOffsets={replay?.frames.map((frame) => frame.offset_minutes) ?? []} />
            : workspace === "airfield" ? <AirfieldRunwayTwin />
            : workspace === "alert" ? <SachetMobileSimulator result={queryResult} location={selectedPoint} place={locationNameFor(selectedPoint)} replayOffset={activeFrame?.offset_minutes ?? 0} forecastMode={forecastMode} />
            : workspace === "ai" ? <AIPipelineWorkspace artifacts={modelArtifacts} forecast={learnedForecast} modalities={modalities} loadModel={() => { setForecastMode("LEARNED"); setLearnedError(null); }} error={learnedError} />
            : <DataSourcesWorkspace sources={replay?.sources ?? []} bridge={imdBridge} modalities={modalities} />}
        </section>
      {impactDrawer ? <LocationImpactDrawer {...impactDrawer} onClose={() => setImpactDrawer(null)} /> : null}
      {scorecardOpen ? <WmoScorecardModal source={forecastMode === "LEARNED" ? "SEVIR" : "SYNTHETIC"} onClose={() => setScorecardOpen(false)} /> : null}
    </main>
  );
}

type LocationQueryPayload = {
  geometry_type: "POINT" | "POLYGON";
  geometry: { longitude: number; latitude: number } | { vertices: { longitude: number; latitude: number }[] };
  coordinate_reference_system: "EPSG:4326";
  name: string;
  source_of_location: string;
  issue_time: string;
  horizon_minutes: number;
  forecast_mode: "BASELINE" | "LEARNED";
};

const neighborhoodLayout = [
  { label: "NW", row: 1, column: -1 }, { label: "N", row: 1, column: 0 }, { label: "NE", row: 1, column: 1 },
  { label: "W", row: 0, column: -1 }, { label: "C", row: 0, column: 0 }, { label: "E", row: 0, column: 1 },
  { label: "SW", row: -1, column: -1 }, { label: "S", row: -1, column: 0 }, { label: "SE", row: -1, column: 1 },
] as const;

function locationNameFor(point: { lat: number; lon: number }) {
  return point.lat === initialPoint.lat && point.lon === initialPoint.lon ? "Jaydev Vihar" : "Selected map point";
}

function createNeighborhood(point: { lat: number; lon: number }): LocationNeighborhoodCell[] {
  const latitudeRadians = point.lat * Math.PI / 180;
  const eccentricitySquared = 6.69437999014e-3;
  const primeVertical = 6_378_137 / Math.sqrt(1 - eccentricitySquared * Math.sin(latitudeRadians) ** 2);
  const meridional = 6_378_137 * (1 - eccentricitySquared) / (1 - eccentricitySquared * Math.sin(latitudeRadians) ** 2) ** 1.5;
  const metersPerDegreeLongitude = Math.PI / 180 * primeVertical * Math.cos(latitudeRadians);
  const metersPerDegreeLatitude = Math.PI / 180 * meridional;

  return neighborhoodLayout.map(({ label, row, column }) => ({
    id: label,
    label,
    center: {
      lat: point.lat + row * 1000 / metersPerDegreeLatitude,
      lon: point.lon + column * 1000 / metersPerDegreeLongitude,
    },
    status: "LOADING" as const,
    result: null,
  }));
}

function squarePolygon(center: { lat: number; lon: number }) {
  const latitudeRadians = center.lat * Math.PI / 180;
  const eccentricitySquared = 6.69437999014e-3;
  const primeVertical = 6_378_137 / Math.sqrt(1 - eccentricitySquared * Math.sin(latitudeRadians) ** 2);
  const meridional = 6_378_137 * (1 - eccentricitySquared) / (1 - eccentricitySquared * Math.sin(latitudeRadians) ** 2) ** 1.5;
  const halfLat = 500 / (Math.PI / 180 * meridional);
  const halfLon = 500 / (Math.PI / 180 * primeVertical * Math.cos(latitudeRadians));
  const south = center.lat - halfLat;
  const north = center.lat + halfLat;
  const west = center.lon - halfLon;
  const east = center.lon + halfLon;
  return [
    { longitude: west, latitude: south },
    { longitude: east, latitude: south },
    { longitude: east, latitude: north },
    { longitude: west, latitude: north },
  ];
}

async function submitLocationQuery(payload: LocationQueryPayload): Promise<LocationQueryResult> {
  const response = await fetch("/api/v1/location/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Location query failed (${response.status}): ${detail}`);
  }
  return (await response.json()) as LocationQueryResult;
}

function MapClickSelector({ onSelect }: { onSelect: Dispatch<SetStateAction<{ lat: number; lon: number }>> }) {
  useMapEvents({
    click(event) {
      onSelect({ lat: event.latlng.lat, lon: event.latlng.lng });
    },
  });
  return null;
}

function TacticalMapTooltip({ title, rows }: { title: string; rows: string[] }) {
  return (
    <LeafletTooltip sticky direction="top" opacity={1} className="vajra-map-tooltip">
      <div className="font-mono text-[10px] leading-4">
        <p className="border-b border-cyan-900/50 pb-1 font-bold tracking-wider text-[#00F0FF]">{title}</p>
        {rows.map((row) => <p key={row} className="mt-1 text-slate-300">{row}</p>)}
      </div>
    </LeafletTooltip>
  );
}

function IsochroneMapBands({ report }: { report: IsochroneReport }) {
  const colorByLead = { 10: "#FF003C", 20: "#fbbf24", 30: "#00F0FF" };
  return report.bands.flatMap((band) => {
    const polygons = band.geometry.type === "Polygon" ? [band.geometry.coordinates] : band.geometry.coordinates;
    return polygons.map((rings, index) => (
      <Polygon
        key={`${band.lead_minutes}-${index}`}
        positions={rings.map((ring) => ring.map(([longitude, latitude]) => [latitude, longitude] as [number, number]))}
        pathOptions={{ color: colorByLead[band.lead_minutes], fillColor: colorByLead[band.lead_minutes], fillOpacity: 0.13, weight: 1.5, dashArray: "4 5" }}
      >
        <TacticalMapTooltip title={`T+${band.lead_minutes} SWEPT FOOTPRINT`} rows={[`AREA: ${band.area_km2.toFixed(2)} KM2`, `METHOD: ${band.method}`, `EVIDENCE: ${band.evidence_status}`, `SOURCE: ${band.source_ids.join(", ")}`, `VALID: ${band.valid_time}`, "INCREMENTAL BAND / NOT IMPACT PROBABILITY"]} />
      </Polygon>
    ));
  });
}

function GridFieldPreview({ frame, className = "radar-grid mt-3 h-28 overflow-hidden border border-slate-800 bg-[#020617]" }: { frame: { values: number[][] } | null; className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!canvasRef.current) return;
    if (frame) renderVilGrid(canvasRef.current, frame.values);
    else canvasRef.current.getContext("2d")?.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
  }, [frame]);

  return (
    <div className={className}>
      <canvas ref={canvasRef} className="h-full w-full [image-rendering:pixelated]" />
    </div>
  );
}

function Panel({ className, children }: { className?: string; children: ReactNode }) {
  return <section className={`border border-cyan-900/30 bg-slate-900/40 backdrop-blur-xl ${className ?? ""}`}>{children}</section>;
}

function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="grid h-8 w-8 shrink-0 place-items-center border border-slate-700 bg-slate-900 text-slate-300 transition hover:border-cyan-400/60 hover:text-[#00F0FF]"
    >
      {children}
    </button>
  );
}

function HudMetric({ icon: Icon, label, value, unit, title, tone = "cyan" }: { icon: typeof Gauge; label: string; value: string; unit: string; title?: string; tone?: "cyan" | "emerald" | "amber" }) {
  const color = tone === "emerald" ? "text-[#39FF14]" : tone === "amber" ? "text-amber-300" : "text-[#00F0FF]";
  return (
    <div title={title} className="flex h-14 min-w-[148px] items-center gap-3 border border-cyan-900/30 bg-slate-900/40 px-3 backdrop-blur-xl">
      <Icon className={`h-4 w-4 ${color}`} />
      <div className="min-w-0">
        <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{label}</p>
        <p className={`truncate font-mono text-lg font-black ${color}`}>
          {value} <span className="text-[9px] text-slate-500">{unit}</span>
        </p>
      </div>
    </div>
  );
}

function IntelStat({ label, value, tone = "emerald" }: { label: string; value: string; tone?: "emerald" | "amber" }) {
  return (
    <div className="border border-cyan-900/30 bg-slate-950/40 p-3">
      <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{label}</p>
      <p className={`mt-1 font-mono text-lg font-black ${tone === "amber" ? "text-amber-300" : "text-[#39FF14]"}`}>{value}</p>
    </div>
  );
}

function SectionHeader({ icon: Icon, label, status }: { icon: typeof Radar; label: string; status: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-[#00F0FF]" />
        <h2 className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-400">{label}</h2>
      </div>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[10px] uppercase text-slate-400">{status}</span>
      </div>
    </div>
  );
}

function StatusTag({ children }: { children: ReactNode }) {
  return <span className="border border-amber-400/50 bg-amber-950/30 px-2 py-1 font-mono text-[9px] font-bold uppercase text-amber-200">{children}</span>;
}

function formatMetric(value: number | null | undefined) {
  return value == null ? "N/A" : value.toFixed(2);
}

function formatOffset(offset: number) {
  if (offset === 0) return "T+000";
  const sign = offset > 0 ? "+" : "-";
  return `T${sign}${String(Math.abs(offset)).padStart(3, "0")}`;
}

function formatLeadTime(validTime: string, issueTime?: string) {
  if (!issueTime) return "T+---";
  const minutes = Math.round((new Date(validTime).getTime() - new Date(issueTime).getTime()) / 60000);
  return `T+${String(Math.max(0, minutes)).padStart(2, "0")}`;
}

export default App;
