# Replay verification scope

`GET /api/v1/replay/verification?source=SYNTHETIC` compares the issue-time
constant-velocity equivalent-area cell footprints with future **simulated**
reflectivity frames. Only matching T+30 and T+60 observations exist in the
current India fixture. The observed event is reflectivity >= 30 dBZ on the
fixture's 1 km raster; the predicted event is the forecast cell footprint.

`source=SEVIR` estimates Farneback optical flow from VIL frames 11 and 12,
advects frame 12 to T+5 through T+60, and compares each pixel with the actual
later VIL frame at the raw uint8 threshold 128. It is a separate, single-event
US **pixel-space baseline**, not a ConvLSTM score or an India location forecast.
Future frames are read only for scoring. Neither verification path alters the
issue-time forecast or unlocks an un-georeferenced location ETA.

CSI = hits / (hits + misses + false alarms). POD = hits / (hits + misses).
Aggregate scores pool contingency counts across matched leads before taking
either ratio; they are not the mean of per-lead scores. A score is returned
only when the denominator is defined. `COMPUTED` means a retrospective score
exists, while `forecast_validation_status=UNVALIDATED` remains in force:
neither benchmark establishes operational or meteorological skill.
