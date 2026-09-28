# ConvLSTM SEVIR Prototype Model Card

## Status

`UNVALIDATED_PROTOTYPE`

The checkpoint is integrated so the original work remains reproducible and inspectable. Phase 7 exposes its normalized SEVIR VIL output in a pixel-space replay preview, but it must not be presented as validated meteorological guidance or used for India ETA.

## Artifact

- Architecture: `LightweightConvLSTM`
- Trainable parameters: 90,945
- Stored state values: 91,076, including BatchNorm buffers
- Checkpoint: `convlstm-sevir-v0.pth`
- SHA-256: `2d2ee7d983869677db114aa8159e7f35d339e5b855307b0f6f75b1992f01e6e0`
- Expected context: 13 VIL frames
- Expected output: 12 VIL frames

## Supplied Prototype Limitations

- No experiment log, training run metadata, or train/validation split manifest accompanied the checkpoint.
- The supplied dataset code used full-event min-max normalization, allowing future target frames to influence input scaling.
- The supplied evaluation searched for a favorable threshold on the same batch used for reporting.
- The WebSocket prototype added randomized confidence values unrelated to calibrated model uncertainty.
- No held-out Indian radar, lightning, gauge, or hazard-label evaluation was supplied.

## Integration Rule

Use the checkpoint only for engineering smoke tests until it is retrained with fixed preprocessing and evaluated against persistence and advection on a frozen held-out set. Any UI surface must label resulting output `EXPERIMENTAL` and provide model, data, and code provenance.

---

# ConvectNet Spatiotemporal Prototype Model Card

## Status

`UNVALIDATED_PROTOTYPE`

This companion checkpoint is registered and load-tested, but it is not enabled for
forecast, hazard, location-intersection, or ETA output.

## Artifact

- Architecture: 3D-CNN + CBAM + two-layer ConvLSTM with a spatial decoder and four experimental task heads
- Trainable parameters: 2,740,238
- Stored state values: 2,741,591, including BatchNorm buffers
- Checkpoint: `convectnet-st-v0.pth`
- SHA-256: `22020351a25739c84613867cb13c2f2e3860602035e7617fe710c803f130ad4f`
- Expected input: four channels over a temporal context window

## Evidence Boundary

- The state dictionary has no embedded training metadata or calibration record.
- The companion evaluation JSON is not imported as verified evidence because it is not tied to a retained split manifest and reproducible run record.
- The supplied scripts mix real SEVIR fields with synthetic or proxy-derived multimodal targets in several paths.
- Hazard outputs and Monte Carlo dropout spread are not calibrated operational probabilities.
- The companion CAP generator is excluded because it emits `Actual` public alerts from proxy-driven values.
