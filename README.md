# VAJRA V2 Replay and Location Intelligence

The active app lives in `backend/app` and `frontend/src/App.tsx`. The earlier
prototype endpoints are retained in `backend/legacy_main.py` but are not mounted
on the live API. The ConvLSTM and ConvectNet checkpoints in `models/prototype`
are registered as `UNVALIDATED_PROTOTYPE`. The ConvLSTM now drives a separate
SEVIR pixel-space replay preview, but neither checkpoint drives India location impacts.

## Run

From the repository root:

```powershell
pip install -r backend/requirements.txt
pip install -r backend/ml/requirements_ml.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

From `frontend` in another terminal:

```powershell
npm ci
npm run dev
```

Open http://127.0.0.1:5173. For verification, run `pytest backend/tests -q`,
`npm run build`, and `npm run lint` from their respective directories.

## Evidence Boundary

`/api/v1/replay/grid/analysis/{frame_index}` screens and tracks the compact
SEVIR VIL event in pixel coordinates. Its source values are not calibrated dBZ
and the supplied subset has no georeferencing. It cannot support an India ETA.

The mapped Bhubaneswar replay is a deterministic `SIMULATED` integration
fixture. Issue-time-safe observations are rasterized, screened with adapted
ConvectNow radar QC, tracked with persistent IDs, and advected at constant
velocity in 5-minute steps through T+60. The forecast footprints are
equivalent-area circles; growth, decay and uncertainty calibration are not
modeled. `/api/v1/location/query` uses the committed Shapely/pyproj engine for
point, route and polygon intersection. A numeric ETA is returned only when a
track crosses the submitted geometry and the engine reports `COMPUTED`.

This demonstrates the forecast-to-location workflow, not operational weather
skill or verified hazard guidance. CSI and POD remain unavailable until a
held-out evaluation exists.

## Phase 7 Learned Replay

`GET /api/v1/replay/grid/learned` verifies the registered
`convlstm-sevir-v0` checkpoint hash (the same weights as
`backend/ml/checkpoints/best_model.pth`), reads only the 13 SEVIR VIL frames
through issue index 12, and returns 12 normalized prediction fields at
T+5 through T+60. Predicted components are numerically screened and tracked
in 96x96 pixel space. The 0.5 detection threshold is not a physical hazard
threshold. Neither model output nor the source event has WGS84 coordinates or
an absolute issue timestamp, and the checkpoint is unvalidated with known
normalization limitations.

The frontend can inspect this ConvLSTM replay separately. A `LocationQuery`
with `forecast_mode: "LEARNED"` returns `NOT_COMPUTABLE` for Jaydev Vihar;
it does not substitute SEVIR pixels for India coordinates or invent an AI ETA.
The default `BASELINE` query retains the explicitly simulated engineering ETA.

## Phase 8-9 Modality and Hazard Gates

`GET /api/v1/replay/modalities` inventories the bundled H5 channels. This
compact event contains `vil` and `id` only: there is no SEVIR IR107 thermal
raster. INSAT-3D is not configured or authorized. The ConvLSTM remains a
single-channel VIL model (`VIL_ONLY_FALLBACK`). If an `ir107` dataset is later
present, its shape alone does not establish time/space co-registration, so it
is reported as context only and excluded from inference until alignment and
thermal scaling are verified. The Bhubaneswar fixture's synthetic satellite
source has metadata but no raster; its availability is `NOT_AVAILABLE`.

`GET /api/v1/replay/hazards?forecast_mode=BASELINE|LEARNED` evaluates tracked
cell peaks at each issue-relative lead. A 45 dBZ threshold screens the
**simulated** reflectivity core, and the existing 0.5 threshold screens the
**unvalidated** learned normalized VIL pixel core. Each screen returns the
input value, threshold, method, source evidence, `INFERRED` derivation,
`NOT_CALIBRATED` uncertainty status, and no probability. Neither screen is
a physical cloudburst or hail diagnosis. Those risks return `NOT_EVALUABLE`
because high-frequency gauge/calibrated QPE and validated hail evidence are
absent. Learned screens stay in SEVIR pixel space and cannot drive India
location alerts or ETA. The dashboard displays these method/evidence states
alongside the explicit missing-modality feed.
