import type { EvidenceStatus, LocationQueryResult } from "./location";

export type AssetTriageEntry = {
  asset_id: string;
  name: string;
  centroid: { lat: number; lon: number };
  geometry_type: "POINT" | "POLYGON" | "ROUTE";
  eta_status: "ARRIVED" | "COMPUTED" | "UNKNOWN" | "NOT_COMPUTABLE";
  eta_minutes: number | null;
  result: LocationQueryResult;
};

export type AssetTriageReport = {
  issue_time: string;
  status: "COMPUTED" | "PARTIAL" | "NOT_COMPUTABLE";
  evidence_status: EvidenceStatus;
  method: string;
  assets: AssetTriageEntry[];
};

type Wgs84Geometry =
  | { type: "Polygon"; coordinates: number[][][] }
  | { type: "MultiPolygon"; coordinates: number[][][][] };

export type IsochroneReport = {
  status: "COMPUTED" | "NOT_COMPUTABLE";
  issue_time: string | null;
  evidence_status: EvidenceStatus;
  method: string;
  bands: {
    lead_minutes: 10 | 20 | 30;
    valid_time: string;
    area_km2: number;
    geometry: Wgs84Geometry;
    method: string;
    evidence_status: EvidenceStatus;
    source_ids: string[];
    forecast_ids: string[];
  }[];
  message: string;
};

export type IntensificationReport = {
  status: "COMPUTED" | "NOT_COMPUTABLE";
  evidence_status: EvidenceStatus;
  method: string;
  frame_index: number;
  valid_time: string | null;
  threshold_dbz_per_hour: number;
  observation_role: string;
  cells: {
    cell_id: string;
    previous_frame_id: string;
    current_frame_id: string;
    delta_dbz: number;
    interval_minutes: number;
    rate_dbz_per_hour: number;
    tag: "RAPID_INTENSIFICATION" | null;
  }[];
  message: string;
};

export type IMDBridgeStatus = {
  state: "AWAITING_AUTHORIZATION";
  connected: false;
  pipeline_steps: string[];
  required_gates: string[];
};
