# VAJRA Phase 2 Data Manifest

This manifest records the access state and permitted MVP use of each source identified in the V2 PRD. Dashboard visibility is not treated as downloadable machine-learning data.

| Dataset | Status | Phase 2 role | Claim boundary |
| --- | --- | --- | --- |
| SEVIR | GREEN | Multimodal training and replay adapter target | United States benchmark; no India performance claim |
| NOAA NEXRAD Level II | GREEN | Radar preprocessing and tracking adapter target | United States coverage |
| NOAA Storm Events | GREEN | Weak severe-event labels | Report uncertainty must remain visible |
| IMD 0.25 degree daily rainfall | GREEN | India rainfall context and retrospective validation | Not sub-hourly cloudburst truth |
| IMD real-time GPM merged rainfall | GREEN | Near-real-time rainfall context | Too coarse and slow for cell-scale nowcasting truth |
| INSAT-3D and INSAT-3DR via MOSDAC | YELLOW | India satellite adapter target | Credentials and DatasetId must be verified |
| ERA5 | YELLOW | Environmental context | Not storm-cell truth |
| IMDAA | YELLOW | India-focused environmental context | Historical reanalysis, not direct cell observation |
| IMD DWR | RED | Future India radar validation | Permission required; adapter disabled |
| IITM or IMD lightning | RED | Future India lightning labels | Do not scrape apps or dashboards |
| IMD AWS or gauges | RED | Future high-frequency rainfall validation | Permission required |

## Phase 2 Bundle

`data/events/bhubaneswar-synthetic-001.json` is a deterministic, offline, explicitly `SIMULATED` integration fixture. It proves replay loading, issue-time separation, source-health rendering, and API serialization. It contains no learned forecast, hazard probability, ETA, or validation metric.

`data/replay/sevir-r17062923508259.h5` is a one-event extraction from the user-supplied SEVIR VIL subset. It contains 49 observed VIL frames and is labelled `DATASET_VERIFIED`. The supplied subset has no georeferencing metadata, so this replay is rendered as an abstract field and is never placed on the India map.

The original `temp_SEVIR_VIL_RANDOMEVENTS_2017_0501_0831.h5` archive is approximately 9.9 GB and remains outside the scaffold. The compact event extraction keeps the offline demo reproducible without duplicating the full temporary download.

Phase 7 uses frames 0-12 as issue-time context for the registered ConvLSTM and
exposes frames 13-24 as experimental, normalized VIL predictions. The learned
fields and tracked components remain in pixel coordinates. The checkpoint's
historical full-event min-max preprocessing cannot be reproduced without
future-frame leakage, so fixed uint8 scaling is used and the domain shift is
recorded as a model limitation. These outputs are not India forecast inputs.

## India Claim Gate

India radar, lightning, gauge, and model-performance claims remain blocked until authorized datasets are received, synchronized, labelled, and evaluated on held-out events.
