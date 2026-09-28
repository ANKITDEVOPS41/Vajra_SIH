"""
SEVIR Dataset Client
Downloads a subset of the SEVIR dataset from the open AWS registry (s3://sevir/).
Targets VIL (Vertically Integrated Liquid) and IR107 (Infrared) modalities.

Usage:
    python sevir_client.py
"""

import os
import logging
from pathlib import Path

import boto3
from botocore import UNSIGNED
from botocore.config import Config
import h5py

# Configure production-grade logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# SEVIR S3 Bucket Configuration
SEVIR_BUCKET = 'sevir'
MODALITIES = {
    'vil': 'data/vil/',
    'ir107': 'data/ir107/'
}
MAX_EVENTS = 50  # We only want a small 50-event subset


def get_s3_client() -> boto3.client:
    """
    Returns an unsigned boto3 S3 client for accessing public buckets.
    SEVIR is hosted on an open AWS registry, so no credentials are required.
    """
    return boto3.client('s3', region_name='us-west-2', config=Config(signature_version=UNSIGNED))


def download_modality_subset(modality_name: str, prefix: str, download_dir: Path) -> None:
    """
    Downloads the first available HDF5 file for a given modality from S3,
    extracts an exact 50-event subset using h5py, and saves it locally.
    
    Args:
        modality_name (str): Name of the modality (e.g., 'vil', 'ir107').
        prefix (str): S3 path prefix for the modality.
        download_dir (Path): Local directory to save datasets.
    """
    s3 = get_s3_client()
    
    logger.info(f"[{modality_name}] Listing objects in s3://{SEVIR_BUCKET}/{prefix}")
    response = s3.list_objects_v2(Bucket=SEVIR_BUCKET, Prefix=prefix)
    
    if 'Contents' not in response:
        logger.error(f"[{modality_name}] No objects found under prefix {prefix}")
        return
        
    # Isolate HDF5 file keys
    h5_keys = [obj['Key'] for obj in response['Contents'] if obj['Key'].endswith('.h5')]
    
    if not h5_keys:
        logger.error(f"[{modality_name}] No HDF5 files found.")
        return
        
    # For subsetting, we just pick the first available file in the bucket prefix
    target_key = h5_keys[0]
    local_temp_path = download_dir / f"temp_{os.path.basename(target_key)}"
    subset_path = download_dir / f"{modality_name}_subset.h5"
    
    if subset_path.exists():
        logger.info(f"[{modality_name}] Subset already exists at {subset_path}. Skipping.")
        return

    logger.info(f"[{modality_name}] Target selected: {target_key}")
    logger.info(f"[{modality_name}] Downloading to temporary file: {local_temp_path} (This might take a while depending on network...)")
    
    # Download the full file first.
    # Note: For production large scale fetching, downloading via ranged GET requests or using h5py virtual layers
    # via the `ros3` backend would prevent downloading the entire file. For subset extraction, standard download+slice is used here.
    s3.download_file(SEVIR_BUCKET, target_key, str(local_temp_path))
    
    logger.info(f"[{modality_name}] Parsing HDF5 file and extracting {MAX_EVENTS} events...")
    try:
        with h5py.File(local_temp_path, 'r') as src_h5, h5py.File(subset_path, 'w') as dst_h5:
            for ds_name in src_h5.keys():
                dataset = src_h5[ds_name]
                logger.info(f"[{modality_name}] Found dataset '{ds_name}' with shape: {dataset.shape}")
                
                # Extract up to MAX_EVENTS. SEVIR shape is typical: (N, W, H, T) or (N, T, W, H)
                num_events = min(MAX_EVENTS, dataset.shape[0])
                subset_data = dataset[:num_events]
                
                logger.info(f"[{modality_name}] Saving subset dataset with shape: {subset_data.shape}")
                # H5py chunking and compression minimizes file size for local subsets
                dst_h5.create_dataset(
                    ds_name,
                    data=subset_data,
                    compression="gzip",
                    compression_opts=4
                )
    except Exception as e:
        logger.error(f"[{modality_name}] Error processing HDF5: {e}")
        if subset_path.exists():
            subset_path.unlink()
    finally:
        # Cleanup the extremely large temporary file to save disk space
        logger.info(f"[{modality_name}] Cleaning up temporary file {local_temp_path}")
        if local_temp_path.exists():
            local_temp_path.unlink()
            
    logger.info(f"[{modality_name}] Complete. Subset saved to: {subset_path}")


def main():
    """
    Main entry point for downloading SEVIR datasets.
    """
    # Ensure data download directory exists
    download_dir = Path(__file__).resolve().parent / "raw"
    download_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Starting SEVIR data ingestion. Destination: {download_dir}")
    
    for mod_name, mod_prefix in MODALITIES.items():
        download_modality_subset(mod_name, mod_prefix, download_dir)


if __name__ == "__main__":
    main()
