import os
import sys
from pathlib import Path
import h5py
import numpy as np

# Ensure absolute import pathing
root_dir = str(Path(__file__).resolve().parent.parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

class RealDataLoader:
    """
    Production-grade SEVIR HDF5 data loader.
    Manages memory aggressively to prevent leaks during rapid API hits.
    Provides a highly realistic moving Gaussian storm fallback if arrays are offline.
    """
    def __init__(self):
        # Target the raw VIL dataset
        self.file_path = os.path.join(
            Path(__file__).resolve().parent.parent.parent, 
            "ml", "data", "raw", "vil_subset.h5"
        )

    def _generate_synthetic_storm(self):
        """
        Calculates a perfectly synthesized 2D Multi-Gaussian storm cell.
        Replicates natural advection moving Northeast across the 384x384 matrix.
        """
        print("[DataLoader] Generating Synthetic Supercell Fallback Sequences...")
        frames = []
        width, height = 384, 384
        
        # Operational origin (bottom-left quadrant relative map)
        cx, cy = 120.0, 260.0 
        
        # Spatial Coordinate bounds
        x = np.arange(0, width, 1, float)
        y = np.arange(0, height, 1, float)
        X, Y = np.meshgrid(x, y)
        
        # Dispersal matrix tuning
        sigma_x, sigma_y = 45.0, 55.0
        
        for i in range(25):
            # Complex spatial translation (Storm advects Northeast over time)
            cx += 5.5
            cy -= 4.0
            
            # Primary massive supercell body
            exponent = -((X - cx)**2 / (2 * sigma_x**2) + (Y - cy)**2 / (2 * sigma_y**2))
            storm_body = 0.85 * np.exp(exponent)
            
            # Microburst / Intense deep-convective internal core
            core_exponent = -((X - cx + 15)**2 / (2 * 18**2) + (Y - cy - 10)**2 / (2 * 18**2))
            storm_core = 0.50 * np.exp(core_exponent)
            
            # Additional forward-flanking precipitation boundary
            flank_exponent = -((X - cx - 35)**2 / (2 * 25**2) + (Y - cy + 25)**2 / (2 * 35**2))
            storm_flank = 0.35 * np.exp(flank_exponent)
            
            # Composite map constrained to native bounds
            frame = np.clip(storm_body + storm_core + storm_flank, 0.0, 1.0)
            frames.append(frame.astype(np.float32))
            
        data = np.array(frames)
        return data[:13], data[13:]

    def get_live_context(self):
        """
        Extracts 25 consecutive frames (13 for historical context, 12 for ground-truth scoring).
        Returns normalized (0.0 to 1.0) NumPy arrays.
        """
        try:
            if not os.path.exists(self.file_path):
                print(f"[System] Database fault: {self.file_path} missing. Engaging Fallback Simulation.")
                return self._generate_synthetic_storm()

            # Context manager ensures file is closed immediately after reading
            with h5py.File(self.file_path, 'r') as hf:
                dataset = hf['vil']
                raw_data = dataset[:25]
                
                # Standardize shape to (25, 384, 384)
                if raw_data.ndim == 4:
                    raw_data = np.squeeze(raw_data, axis=-1)
                    
                # Normalize typical VIL max values (0 - 255) to float (0.0 - 1.0)
                normalized_data = raw_data.astype(np.float32) / 255.0
                
                past_13 = normalized_data[:13]
                future_12 = normalized_data[13:25]
                
                return past_13, future_12

        except Exception as e:
            print(f"[DataLoader] SEVIR extraction fault: {e}. Mounting Synthetic Tensors.")
            return self._generate_synthetic_storm()
