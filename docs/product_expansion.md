# Product expansion: replay-gated workspaces

The six top-level workspaces share the same replay session, baseline forecast,
location query, model registry, modality status, and IMD adapter state. The
Spatial Nowcast tab retains the 3x3 matrix, triage board, and strict WGS84 ETA.

## Verification

`GET /api/v1/replay/wmo-scorecard?source=SYNTHETIC|SEVIR` reports POD, FAR,
CSI and HSS at T+15/30/45/60/90/120. It derives counts from the existing
issue-time-safe verification path. The Bhubaneswar simulation has paired
observations only at T+30 and T+60; all other requested leads are
`NOT_COMPUTABLE`. The SEVIR benchmark is Farneback optical flow in pixel space,
not ConvLSTM validation or India nowcast skill. T+90 and T+120 are beyond the
implemented forecast horizon. All scores are retrospective and UNVALIDATED for
operational forecast skill.

`GET /api/v1/replay/observed-radar/{offset_minutes}` exposes the deterministic
simulation's 128x128 1 km reflectivity field and WGS84 grid bounds, only when
an observed fixture frame exists. The split map shows matching forecast and
replay leads, but never interpolates missing ground truth. The map layer dock
uses the same raster. It is not an IMD Doppler product.

## Public-alert simulator

Sachet/Public Alert is unaffiliated with NDMA, IMD, or Sachet. It uses an
intersecting `LocationImpact` with `eta.status=COMPUTED` to display a replay-time
countdown. The CAP v1.2 envelope uses `status=Test`, `scope=Private`, and
`sender=vajra.local`; no public alert delivery exists. `areaDesc` names the
queried location without inventing a warning polygon. Hindi/Odia strings are
draft translations requiring human review. Shelter routing remains unavailable
until a user imports GeoJSON Point features with `name`, `status=OPEN`,
`verified_at`, and `source`; even then, the displayed status is explicitly
user-supplied and not independently confirmed. Route links use the nearest
imported point by geodesic distance, not a verified safe route.

References: [OASIS CAP 1.2](https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.pdf),
[NDMA Sachet](https://sachet.ndma.gov.in/).

## VEBS runway simulator

The requested runway 01/19 is not the published VEBS designation. AAI's
April 2026 AIP lists runway **14/32**, thresholds `201539.18N 0854818.22E`
and `201427.12N 0854914.00E`, and true bearing 143.85 degrees for RWY 14.
The map uses those threshold coordinates and WGS84 geodesic 3 km approach
gates. Runway-relative headwind/crosswind projections and the vector
difference are computed only from operator-entered east/north wind vectors.
The 15 m/s exceedance is an illustrative calculation, **not** a measured LLWS
alert or ATC go-around instruction. No radial velocity, runway pressure,
temperature, or CAPE feed is present; these fields remain `NO FEED`.

Reference: [AAI VEBS AD 2.12](https://aim-india.aai.aero/eaip/eaip-v2-04-2026/eAIP/IN-AD%202.1VEBS-en-GB.html).

## Sensors and model

The current ConvLSTM receives 13 SEVIR VIL frames and predicts 12 VIL frames
through T+60. It is unvalidated and lacks India georeferencing. No physical
feature-attribution values are produced, so XAI is `NOT_COMPUTABLE` rather
than a speculative percentage. INSAT thermal IR, lightning density, AWS
stations, and drainage layers remain gated until aligned, licensed,
georeferenced feeds exist. The IMD/MOSDAC bridge remains disconnected and
awaiting authorization.
