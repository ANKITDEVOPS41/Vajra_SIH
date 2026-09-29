import type { EvidenceStatus } from "./location";

export type GeoPoint = { lat: number; lon: number };
export type ForecastPolygon = {
  cell_id: string;
  lead_minutes?: number;
  polygon: GeoPoint[];
  max_reflectivity_dbz: number;
};
export type RadarFrame = {
  event_id: string;
  frame_id: string;
  offset_minutes: number;
  valid_time: string;
  evidence_status: EvidenceStatus;
  method: string;
  field: string;
  unit: "dBZ";
  width: number;
  height: number;
  southwest: GeoPoint;
  northeast: GeoPoint;
  values: number[][];
};
export type Scorecard = {
  event_id: string;
  source: "SYNTHETIC" | "SEVIR";
  verification_scope: "RETROSPECTIVE_REPLAY";
  forecast_validation_status: "UNVALIDATED";
  evidence_status: EvidenceStatus;
  method: string;
  field: string;
  threshold: number;
  threshold_unit: string;
  georeferenced: boolean;
  observation_source: string;
  leads: {
    lead_minutes: number;
    status: "COMPUTED" | "NOT_COMPUTABLE";
    hits: number | null;
    misses: number | null;
    false_alarms: number | null;
    correct_negatives: number | null;
    pod: number | null;
    far: number | null;
    csi: number | null;
    hss: number | null;
    reason: string | null;
  }[];
  limitations: string[];
};
