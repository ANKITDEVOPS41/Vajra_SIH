# Phase 11.5: Spatial analytics and IMD bridge boundary

The active India event is an explicitly `SIMULATED` Bhubaneswar replay. Its
baseline forecast uses issue-time-safe radar-like observations and constant
velocity, equivalent-area WGS84 polygons. No result below is operational
weather guidance or a validated model score.

## Multi-asset triage

`POST /api/v1/location/triage` accepts a WGS84 GeoJSON `FeatureCollection`
with 1–100 assets plus `issue_time`, `horizon_minutes`, and `forecast_mode`.
Supported feature geometries are Point, LineString (route), and a single-ring
Polygon. Each feature is converted into a separate `LocationQuery` and passed
through the existing location intelligence service. The response retains the
complete `LocationQueryResult`, including every `LocationImpact` and nested
`ETAResult`, for each asset. The board ranks `ARRIVED` first, followed by
numeric `COMPUTED` ETA, then `UNKNOWN` and `NOT_COMPUTABLE`. A clear asset
has no invented ETA. Invalid coordinates, self-intersections, unsupported
geometries, and duplicate asset IDs are rejected with HTTP 422.

The frontend reads a local `.geojson` or `.json` file, up to 1 MB, and sends
its contents to this endpoint. It does not contain a built-in asset fixture.
On forecast-mode change it reruns the same collection. ConvLSTM mode returns
`NOT_COMPUTABLE` because the available SEVIR VIL predictions have no India
georeferencing.

## Swept forecast bands

`GET /api/v1/replay/isochrones?forecast_mode=BASELINE` returns incremental
T+10, T+20, and T+30 bands. The service transforms existing forecast polygons
into a local metric projection, takes the convex hull of each consecutive
polygon pair to include the swept area between five-minute samples, unions
the swept footprints through each lead, and subtracts the previous envelope.
It transforms the resulting GeoJSON bands back to WGS84. The area is measured
in the metric projection. Every band carries its method, valid time,
`SIMULATED` evidence status, source IDs, and contributing forecast IDs.

These are time-ordered footprints, not probability contours or new forecast
growth. `forecast_mode=LEARNED` returns `NOT_COMPUTABLE` with no geometry.

## Rapid intensification

`GET /api/v1/replay/intensification?frame_index=N` compares the selected
replay observation with only its immediate predecessor for matching cell IDs:

`rate_dbz_per_hour = (current_max_dbz - previous_max_dbz) * 60 / elapsed_minutes`

The engineering alert threshold is strictly greater than `8 dBZ/hr`. The
response provides the signed delta and rate, both frame IDs, observation
role, method, and `SIMULATED` evidence. Later replay observations are read
only when the replay UI advances to them; this derivative does not enter the
issue-time forecast. The first frame, a missing prior cell, and learned VIL
mode return `NOT_COMPUTABLE` rather than an invented dBZ derivative.

## IMD / MOSDAC bridge

`backend/app/adapters/imd_adapter.py` defines the authorized product,
validated-raster, and adapter protocol. `GET /api/v1/replay/imd-bridge`
reports `AWAITING_AUTHORIZATION` and `connected=false`. The displayed
NetCDF/HDF5 pipeline stages are planned interfaces: retrieve an authorized
product, decode product-specific metadata, verify calibration and missing
values, validate georeferencing and timestamps, run QC and co-registration,
then produce issue-time-safe replay fields with provenance. Credentials alone
do not satisfy those gates; no live IMD or MOSDAC fetch is implemented.
