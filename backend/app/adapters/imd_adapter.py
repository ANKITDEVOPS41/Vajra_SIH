"""Dormant IMD DWR / MOSDAC ingestion boundary; no network client is configured."""

from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel


class IMDProduct(BaseModel):
    product_id: str
    modality: Literal["IMD_DWR", "INSAT_3D_IR"]
    format: Literal["NetCDF", "HDF5"]
    source_uri: str


class ValidatedRaster(BaseModel):
    product_id: str
    source_id: str
    issue_time: str
    valid_time: str
    crs: str
    units: str
    width: int
    height: int
    data_path: Path


class IMDAdapter(Protocol):
    """An authorized implementation must verify each stage before replay use."""

    def retrieve(self, product: IMDProduct) -> Path: ...
    def decode_and_validate(self, product: IMDProduct, local_path: Path) -> ValidatedRaster: ...
    def quality_control(self, raster: ValidatedRaster) -> ValidatedRaster: ...
    def align_to_issue_time(self, radar: ValidatedRaster, thermal: ValidatedRaster | None) -> ValidatedRaster: ...


class IMDBridgeStatus(BaseModel):
    state: Literal["AWAITING_AUTHORIZATION"]
    connected: Literal[False]
    pipeline_steps: list[str]
    required_gates: list[str]


def imd_bridge_status() -> IMDBridgeStatus:
    return IMDBridgeStatus(
        state="AWAITING_AUTHORIZATION", connected=False,
        pipeline_steps=[
            "Authorize source and retrieve product manifest",
            "Decode IMD DWR NetCDF or MOSDAC INSAT-3D HDF5 with product-specific metadata",
            "Validate units, calibration, missing values, timestamps, and WGS84 georeferencing",
            "Apply radar QC and spatial/temporal co-registration",
            "Convert to issue-time-safe replay fields with source provenance",
        ],
        required_gates=[
            "Authorized product access and documented licensing",
            "Verified radar/satellite product IDs and decoding specifications",
            "Valid coordinates, time alignment, QC, and calibration",
            "Held-out Indian event evaluation before operational claims",
        ],
    )
