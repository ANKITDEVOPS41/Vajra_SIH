import os
import sys
from pathlib import Path
import torch

# Ensure the package root (VAJRA) is on sys.path to resolve ModuleNotFoundError
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend.ml.models.convlstm import LightweightConvLSTM

class InferenceService:
    """
    AI Inference Pipeline Service.
    Wraps the trained VAJRA LightweightConvLSTM core, manages memory scopes efficiently, 
    and pipes high-speed array manipulations avoiding operational lag.
    """
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Dynamically discover optimal weights
        self.best_model_path = os.path.join(
            Path(__file__).resolve().parent.parent, 
            "ml", "checkpoints", "best_model.pth"
        )
        self.model = None

    def _initialize_model(self, channels: int):
        """Loads and compiles model architecture natively on target tensor properties."""
        print(f"[InferenceService] Bootstrapping LightWeight ConvLSTM onto {self.device}")
        self.model = LightweightConvLSTM(in_channels=channels, hidden_channels=16, seq_out=12).to(self.device)
        
        if os.path.exists(self.best_model_path):
            print(f"[InferenceService] Target locked: Restoring memory weights from {self.best_model_path}")
            self.model.load_state_dict(torch.load(self.best_model_path, map_location=self.device))
        else:
            print(f"[InferenceService] WARNING: Operational weights offline at {self.best_model_path}. Initiating with untrained state variables.")
            
        # Hard lock into evaluation architecture. Very important.
        self.model.eval()

    def predict(self, context_tensor: torch.Tensor):
        """
        Processes standard Context Sequence Grid.
        
        Args:
            context_tensor (Tensor): PyTorch spatial-temporal sequence tensor. 
                                     Shape required: (1, Channels, 13, 384, 384)
                                     
        Returns:
            numpy.ndarray: Predicted 12 Future frames matrix. Shape: (1, Channels, 12, 384, 384)
            float: Simulated historical base confidence bounds.
        """
        # Ascertain pipeline dimensional channels map to initialized state
        channels = context_tensor.size(1)
        if self.model is None:
            self._initialize_model(channels)
            
        # Secure mapping buffer onto required device
        context_tensor = context_tensor.to(self.device)
        
        # Operational pass block without tracking gradient vectors. High velocity mode.
        with torch.no_grad():
            predictions = self.model(context_tensor)
            
        # Decouple GPU memory and return array primitive
        raw_frames = predictions.cpu().numpy()
        
        # Abstract bound expectation
        baseline_confidence = 0.85 
        
        return raw_frames, baseline_confidence

# Singleton instantiation 
inference_pipeline = InferenceService()
