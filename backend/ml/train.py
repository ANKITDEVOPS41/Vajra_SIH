import os
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from tqdm import tqdm

from backend.ml.data.dataset import SEVIRDataset
from backend.ml.models.convlstm import LightweightConvLSTM

class WeightedLoss(nn.Module):
    """
    Custom Loss Function addressing the MSE spatial smoothing effect.
    1. Combines MAE (L1) for sharper images and MSE (L2) for large error penalization.
    2. Applies a heavy multiplier to convective cores (intensities > threshold).
    """
    def __init__(self, high_intensity_weight=20.0, threshold=0.1):
        super().__init__()
        self.mae = nn.L1Loss(reduction='none')
        self.mse = nn.MSELoss(reduction='none')
        self.weight = high_intensity_weight
        self.threshold = threshold

    def forward(self, pred, target):
        # Base composite error map
        mae_loss = self.mae(pred, target)
        mse_loss = self.mse(pred, target)
        combined_error = mae_loss + mse_loss
        
        # Apply intense multiplier focus
        # weight_mask defaults to 1.0 (empty sky), spikes for intense targets
        weight_mask = torch.ones_like(target)
        weight_mask[target > self.threshold] = self.weight
        
        # Element-wise weighting and mean reduction
        weighted_error = combined_error * weight_mask
        return weighted_error.mean()


def main():
    """
    Core Training Engine loop for VAJRA Forecasting Module.
    Designed for local execution using CUDA where available.
    """
    # 1. Setup hardware acceleration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Training Architecture initialized on device: {device}")
    
    # Engine Configuration (tuned for laptop/local GPUs securely)
    batch_size = 2
    epochs = 25  # Increased passes to learn complex spatial advection
    learning_rate = 1e-4
    val_split = 0.2
    
    # 2. Configure File pathways referencing pipeline datasets
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vil_path = os.path.join(base_dir, "data", "raw", "vil_subset.h5")
    ir107_path = os.path.join(base_dir, "data", "raw", "ir107_subset.h5")
    
    # Instantiate Data Pipeline (VIL + optional IR107 fallback)
    print("Loading SEVIR Dataset into memory...")
    dataset = SEVIRDataset(
        vil_path=vil_path, 
        ir107_path=ir107_path if os.path.exists(ir107_path) else None
    )
    
    # Extract dynamic input channels provided by the dataset parsing
    sample_x, sample_y = dataset[0]
    in_channels = sample_x.shape[1] 
    
    # Data Split allocations
    val_size = int(len(dataset) * val_split)
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    # Create Pytorch Loaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # 3. Model Architecture Construction
    model = LightweightConvLSTM(in_channels=in_channels, hidden_channels=16, seq_out=12).to(device)
    
    # Training Primitives
    # Swapped basic MSELoss for Custom WeightedLoss to fix smoothing and low FAR
    criterion = WeightedLoss(high_intensity_weight=20.0, threshold=0.1)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    best_val_loss = float('inf')
    checkpoint_dir = os.path.join(base_dir, "checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    print("Commencing Deep Learning Training Loop...")
    # 4. Deep Learning Sequence Loop
    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        
        # --- TRAINING PHASE ---
        with tqdm(train_loader, desc=f"Epoch {epoch}/{epochs} [Train]") as pbar:
            for x, y in pbar:
                # DataLoader batches: (Batch, Sequence, Channels, Height, Width)
                # Model architecture assumes input: (Batch, Channels, Sequence, Height, Width)
                x = x.permute(0, 2, 1, 3, 4).to(device)
                y = y.permute(0, 2, 1, 3, 4).to(device)
                
                optimizer.zero_grad()
                preds = model(x)
                
                loss = criterion(preds, y)
                loss.backward()
                optimizer.step()
                
                train_loss += loss.item() * x.size(0)
                pbar.set_postfix({"Loss": loss.item()})
                
        train_loss /= len(train_loader.dataset)
        
        # --- VALIDATION PHASE ---
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            with tqdm(val_loader, desc=f"Epoch {epoch}/{epochs} [Val]") as pbar:
                for x, y in pbar:
                    x = x.permute(0, 2, 1, 3, 4).to(device)
                    y = y.permute(0, 2, 1, 3, 4).to(device)
                    
                    preds = model(x)
                    loss = criterion(preds, y)
                    
                    val_loss += loss.item() * x.size(0)
                    pbar.set_postfix({"Loss": loss.item()})
                    
        val_loss /= len(val_loader.dataset)
        
        print(f"Epoch [{epoch}/{epochs}] - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")
        
        # Save Best Model Weights
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_model_path = os.path.join(checkpoint_dir, "best_model.pth")
            torch.save(model.state_dict(), best_model_path)
            print(f"--> Checkpoint triggered! Saved best weights to {best_model_path}")

if __name__ == "__main__":
    main()
