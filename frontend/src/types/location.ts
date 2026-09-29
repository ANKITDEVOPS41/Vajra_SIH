export type EvidenceStatus =
  | "OBSERVED"
  | "INFERRED"
  | "BASELINE_FORECAST"
  | "LEARNED_FORECAST"
  | "SIMULATED"
  | "DEGRADED"
  | "DATASET_VERIFIED"
  | "IMPLEMENTED"
  | "UNKNOWN";

export type ETAResult = {
  status: "UNKNOWN" | "NOT_COMPUTABLE" | "ARRIVED" | "COMPUTED";
  eta_minutes: number | null;
  method: string;
  confidence: number | null;
  not_computable_reason: string | null;
};

export type LocationImpact = {
  query_id: string;
  impact_id: string;
  issue_time: string | null;
  valid_time: string;
  lead_minutes: number;
  cell_id: string;
  hazard: string;
  value: number | null;
  unit: string;
  uncertainty: { lower: number; upper: number; method: string; level: number } | null;
  method: string;
  evidence_status: EvidenceStatus;
  source_ids: string[];
  forecast_id: string | null;
  model_version: string | null;
  spatial_relation: "INTERSECTS" | "WITHIN" | "APPROACHING" | "RECEDING" | "NO_RELATION";
  distance_km: number | null;
  eta: ETAResult;
};

export type LocationQueryResult = {
  query_id: string;
  issue_time: string;
  status: "COMPUTED" | "NOT_COMPUTABLE";
  evidence_status: EvidenceStatus;
  model_version: string | null;
  model_status: string | null;
  impacts: LocationImpact[];
  message: string;
};

export type NeighborhoodCellStatus = "LOADING" | "COMPUTED" | "NOT_COMPUTABLE" | "ERROR";

export type LocationNeighborhoodCell = {
  id: string;
  label: "NW" | "N" | "NE" | "W" | "C" | "E" | "SW" | "S" | "SE";
  center: { lat: number; lon: number };
  status: NeighborhoodCellStatus;
  result: LocationQueryResult | null;
  error?: string;
};
