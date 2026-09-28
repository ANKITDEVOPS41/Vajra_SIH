# ConvectNow Updated: Selective Merge Audit

Reviewed source: `VARJA_SIH/convectnow_Updated/convect` (local peer checkout).
This is an engineering intake record, not a validation report or authorization
to use government data. VAJRA's location query, ETA, and India claim gates stay
unchanged.

## Useful additions adopted

- `backend/data/ingester_mosdac.py` reads an `IMG_<band>_TEMP` lookup table.
  VAJRA adapted only this decoding step into `backend/app/science/insat_lut.py`.
  The adapter requires explicit Kelvin units, an actual LUT, and valid count
  indices. It does not fabricate default calibration, timestamps, geometry,
  or a live INSAT observation. A real product still needs verified time and
  geolocation metadata before it can join the replay.
- `backend/meteorological_verification.py` includes Gilbert/equitable threat
  score. VAJRA added its formula to the existing science verification module,
  with a deterministic contingency-table test. It is not populated with a
  model score until a held-out evaluation exists.
- The peer's tests suggested focused invalid-calibration and zero-event
  fixtures; these were recreated locally without importing its broad tests or
  dependencies.

The peer `tests/test_data_pipeline.py` also tests LAEA/geostationary/polar
round-trips, optical-flow missing-frame imputation, and radar GIF decoding;
`tests/test_grid.py` tests a fixed Sohra grid, including out-of-domain
clamping. These are candidate future tests, not drop-ins for VAJRA's WGS84
intersection engine. In particular, silent out-of-domain clamping could turn
an invalid location into a false intersection, and two-sided missing-frame
imputation is not valid for an issue-time forecast.

## Candidate data products and events

The peer catalogue names INSAT-3DR Imager and thermal channels, plus MOSDAC
radar products, as future India-source candidates. [MOSDAC's INSAT-3DR product
page](https://www.mosdac.gov.in/insat-3dr-data-products) describes the imager
product family. Its [INSAT-3D format document](https://www.mosdac.gov.in/docs/INSAT3D_Products.pdf)
documents `IMG_TIR1` counts, `IMG_TIR1_TEMP` calibration, and separate
geolocation datasets. Product existence is not proof of VAJRA download access,
alignment, or event coverage.

`docs/EVENT_PROOF.md` in the peer checkout proposes the **5 May 2024 Meghalaya
hail/squall** and **16-17 June 2022 Cherrapunji rainfall** windows for future
overlap study. Its specific sensor counts, access claims, and radar continuity
were not reproduced here. Both are candidate events only, not VAJRA replay or
verification datasets.

## Evaluation evidence gate

The peer `evaluation_report.json` claims T+15-minute CSI values of 0.6901
(ConvectNet), 0.6537 (optical flow), and 0.5642 (persistence). Its training
script uses a storm-level 78/12/10 split, seed 42, 12 input frames, a
three-frame lead, 128-pixel crops, threshold 0.35 on normalized VIL, batch
size 16, learning rate 0.001, and a 10-epoch entry point. These are **script
parameters and unverified report claims**, not accepted VAJRA skill metrics.
The peer checkout has no checkpoint, frozen split IDs, source-file hashes,
per-event predictions, or retained evaluation plots tying the report to a
reproducible run. In particular, the script's display label calls its 0.35
normalized threshold "35 dBZ" without a justified physical conversion.
No model descriptor or checkpoint was registered in VAJRA.

## Excluded from the active pipeline

- The peer MOSDAC adapter uses `verify=False`, fixed values (including 206.2 K
  and -0.52 K/min), and generated fallback fields even when only catalogue
  metadata is fetched. These must not masquerade as observations.
- The peer SEVIR dataset synthesizes IR/lightning-like channels and
  cloudburst/hail targets from VIL proxies. Its four-channel tensor is not an
  issue-time-safe, co-registered sensor cube with verified hazard labels.
- Radar AP gating based on a warm cloud-top threshold could erase real echoes
  without independent validation. Optical-flow interpolation using the next
  frame would leak future information at issue time. No new dealiasing routine
  was found.
- Peer colorbars and cell panels label dBZ bands as "hail" or "cloudburst"
  and show fixed attribution percentages or ETA values. VAJRA's evidence-gated
  dashboard and location engine were not replaced.
- `SIH_PITCH_GUIDE.md`, `DATA_CATALOGUE.md`, and `EVENT_PROOF.md` contain
  operational and "100% verified" claims unsupported by artifacts in this
  checkout. They were reviewed but not copied wholesale.

All model weights, H5 datasets, NumPy arrays, generated frontend bundles, and
credential files remain outside Git tracking. The local untracked prototype
weights used by VAJRA can remain on disk for development but require an
external artifact store or setup step for a fresh clone.
