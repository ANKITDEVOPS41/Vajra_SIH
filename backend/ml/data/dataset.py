"""
PyTorch Dataset for SEVIR Subset.
Handles loading HDF5 files of VIL and IR107 modalities, parsing temporal sequences,
and generating (X, Y) pairs for ML model training.
"""

import logging
from pathlib import Path
from typing import Tuple, Optional

import h5py
import numpy as np
import torch
from torch.utils.data import Dataset

# Configure module-level logger
logger = logging.getLogger(__name__)


class SEVIRDataset(Dataset):
    """
    Custom PyTorch Dataset for loading SEVIR storm event sequences.
    
    The dataset reads subsets of VIL and (optionally) IR107 datasets, normalizes them, 
    and slices the temporal dimension into:
    - X: past 13 frames (representing 65 minutes of context at 5min/frame)
    - Y: future 12 frames (representing a 60-minute forecast horizon)
    """
    
    def __init__(self, vil_path: str, ir107_path: Optional[str] = None):
        """
        Initializes the dataset, loading the smaller subset directly into memory.
        
        Args:
            vil_path (str): Path to the VIL HDF5 subset file.
            ir107_path (str, optional): Path to the IR107 HDF5 subset file.
        """
        self.vil_path = Path(vil_path)
        self.ir107_path = Path(ir107_path) if ir107_path else None
        
        logger.info(f"Initializing SEVIRDataset with VIL: {self.vil_path}")
        
        # Load VIL dataset completely into memory (safe for 50-event subset)
        self.vil_data = self._load_h5_data(self.vil_path, 'vil')
        
        # Optionally load IR107 dataset
        self.ir107_data = None
        if self.ir107_path and self.ir107_path.exists():
            logger.info(f"Loading optional IR107 dataset: {self.ir107_path}")
            self.ir107_data = self._load_h5_data(self.ir107_path, 'ir107')
            
            # Ensure sequence lengths match between modalities
            assert self.vil_data.shape[0] == self.ir107_data.shape[0], \
                "Mismatch in number of events between VIL and IR107"

        # Align dimensions appropriately.
        # SEVIR data shape is typically: (N_events, width, height, time_steps) (e.g., N, 384, 384, 49)
        # We need the time dimension up front for PyTorch sequence modeling, 
        # but standard spatial model dimensions are (Channels, Time, H, W) or (Time, Channels, H, W).
        # We'll transform to: (N_events, time_steps, width, height)
        if len(self.vil_data.shape) == 4 and self.vil_data.shape[-1] >= 25:
            # Transposing from (N, W, H, T) -> (N, T, W, H)
            self.vil_data = np.transpose(self.vil_data, (0, 3, 1, 2))
            if self.ir107_data is not None:
                self.ir107_data = np.transpose(self.ir107_data, (0, 3, 1, 2))
                
        logger.info(f"Dataset successfully loaded. Total events: {len(self)}")

    def _load_h5_data(self, filepath: Path, fallback_key: str) -> np.ndarray:
        """
        Helper method to extract HDF5 dataset array.
        """
        if not filepath.exists():
            raise FileNotFoundError(f"HDF5 dataset not found: {filepath}")
            
        with h5py.File(filepath, 'r') as h5_file:
            # Look for the exact dataset key, fallback to whatever is first available
            key = fallback_key if fallback_key in h5_file.keys() else list(h5_file.keys())[0]
            data = h5_file[key][:]
        return data

    def __len__(self) -> int:
        """Returns the total number of events in the dataset."""
        return len(self.vil_data)

    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """
        Applies Min-Max normalization per event sequence.
        Scales pixel values linearly between 0.0 and 1.0.
        """
        d_min = np.min(data)
        d_max = np.max(data)
        if d_max == d_min:
            return data
        return (data - d_min) / (d_max - d_min)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Generates one sample of data.
        
        Args:
            idx (int): Event index.
            
        Returns:
            Tuple[torch.Tensor, torch.Tensor]: (X, Y)
                X: Context frames tensor, shape (13, Channels, H, W)
                Y: Forecast frames tensor, shape (12, Channels, H, W)
        """
        # Fetch individual event sequences
        vil_event = self.vil_data[idx]
        
        if self.ir107_data is not None:
            ir107_event = self.ir107_data[idx]
            # Stack VIL and IR107 as distinct channels
            # Shapes: (time_steps, width, height) -> (time_steps, 2, width, height)
            event_data = np.stack((vil_event, ir107_event), axis=1)
        else:
            # Return as 1-channel sequence
            # Shapes: (time_steps, width, height) -> (time_steps, 1, width, height)
            event_data = np.expand_dims(vil_event, axis=1)

        # Apply Min-Max Normalization (0 to 1) 
        event_data = self._normalize(event_data)
        
        # Temporal slicing for sequence prediction
        # SEVIR events natively have 49 frames.
        # X: Past 13 frames (Indices 0 to 12) -> 65 mins
        # Y: Future 12 frames (Indices 13 to 24) -> 60 mins
        x_seq = event_data[:13]
        y_seq = event_data[13:25]
        
        # Convert arrays to PyTorch FloatTensors
        x_tensor = torch.from_numpy(x_seq).float()
        y_tensor = torch.from_numpy(y_seq).float()
        
        return x_tensor, y_tensor
