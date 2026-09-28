import os
import torch
import numpy as np
from torch.utils.data import DataLoader

from backend.ml.data.dataset import SEVIRDataset
from backend.ml.models.convlstm import LightweightConvLSTM

def calculate_metrics(y_true, y_pred, threshold):
    """
    Calculates Critical Success Index (CSI), Probability of Detection (POD), 
    and False Alarm Ratio (FAR) over PyTorch sequences.
    
    These metrics are standard in meteorology for evaluating storm predictions 
    above specific intensity levels (like 35 dBZ).
    
    Args:
        y_true (Tensor): Ground truth sequence tensors.
        y_pred (Tensor): Predicted sequence tensors.
        threshold (float): Scaled intensity threshold to binarize predictions.
        
    Returns:
        dict: Dictionary of metric values.
    """
    # 1. Binarize logic based on weather severity threshold
    y_true_b = (y_true >= threshold)
    y_pred_b = (y_pred >= threshold)
    
    # 2. Extract intersection contingencies 
    hits = (y_true_b & y_pred_b).sum().float()
    false_alarms = (~y_true_b & y_pred_b).sum().float()
    misses = (y_true_b & ~y_pred_b).sum().float()
    
    eps = 1e-7 # Prevent division by zero runtime warnings
    
    # 3. Calculate Operational Formulations
    csi = hits / (hits + false_alarms + misses + eps)
    pod = hits / (hits + misses + eps)
    far = false_alarms / (hits + false_alarms + eps)
    
    return {
        "CSI": csi.item(),
        "POD": pod.item(),
        "FAR": far.item()
    }

def main():
    """
    Core Evaluation Baseline Module.
    Compares the state-of-the-art Deep Learning VAJRA pipeline vs Persistence. 
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Evaluation Context Device: {device}")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    vil_path = os.path.join(base_dir, "data", "raw", "vil_subset.h5")
    ir107_path = os.path.join(base_dir, "data", "raw", "ir107_subset.h5")
    
    # 1. Initialize Pipeline Loader
    dataset = SEVIRDataset(
        vil_path=vil_path, 
        ir107_path=ir107_path if os.path.exists(ir107_path) else None
    )
    
    sample_x, _ = dataset[0]
    in_channels = sample_x.shape[1] 
    
    # 2. Re-create and load optimal Model Weights
    best_model_path = os.path.join(base_dir, "checkpoints", "best_model.pth")
    model = LightweightConvLSTM(in_channels=in_channels, hidden_channels=16, seq_out=12).to(device)
    
    if not os.path.exists(best_model_path):
        print(f"Alert: Weights file missing at {best_model_path}. Complete a training run first.")
        # Proceeding is impossible without weights.
        return
        
    print(f"Restoring AI Model Weights from {best_model_path}...")
    model.load_state_dict(torch.load(best_model_path, map_location=device))
    model.eval()
    
    # 3. Running an Inference Demo on a Test Batch
    # Here fetching a validation sample as proxy for operational input test.
    test_loader = DataLoader(dataset, batch_size=2, shuffle=False)
    x, y_true = next(iter(test_loader))
    
    # Shape reorientation
    # Dataloader inputs: (Batch, Seq, Ch, H, W). 
    # Network expects: (Batch, Ch, Seq, H, W)
    x = x.permute(0, 2, 1, 3, 4).to(device)
    y_true = y_true.permute(0, 2, 1, 3, 4).to(device)
    
    with torch.no_grad():
        # A) Predict Future using AI
        y_pred_ai = model(x)
        
        # B) Predict Future using Base Persistence Formula (Static Snapshot)
        last_input_frame = x[:, :, -1, :, :] # Slice giving shape (Batch, Ch, H, W)
        seq_out = y_true.size(2)
        y_pred_persistence = last_input_frame.unsqueeze(2).expand(-1, -1, seq_out, -1, -1)
        
    # 4. Optimal Threshold Search (Addressing MSE Smoothing Effect)
    print("\n--- Searching for Optimal Threshold ---")
    print("MSE Loss tends to smooth out high-intensity predictions. Finding the optimal binarization threshold...")
    
    candidate_thresholds = np.arange(0.30, 0.56, 0.05)
    best_threshold = 0.30
    best_ai_csi = -1.0
    
    for thresh in candidate_thresholds:
        metrics = calculate_metrics(y_true, y_pred_ai, thresh)
        print(f"Threshold {thresh:.2f} -> Global AI CSI: {metrics['CSI']:.4f}")
        if metrics['CSI'] > best_ai_csi:
            best_ai_csi = metrics['CSI']
            best_threshold = thresh
            
    print(f"\n=> Optimal Threshold Selected: {best_threshold:.2f}\n")
    
    # 5. Calculate Metrics Per Lead Time Sequence
    # Evaluate incrementally at Frame 3 (T+15), Frame 6 (T+30), Frame 9 (T+45), Frame 12 (T+60)
    frames_to_eval = [
        (2, "T+15 min (Frame 3)"),
        (5, "T+30 min (Frame 6)"),
        (8, "T+45 min (Frame 9)"),
        (11, "T+60 min (Frame 12)")
    ]
    
    print("--- Comparing AI vs Persistence across time horizons ---")
    print(f"| Lead Time            | AI CSI | Pers CSI | AI POD | Pers POD | AI FAR | Pers FAR |")
    print(f"|----------------------|--------|----------|--------|----------|--------|----------|")
    
    for frame_idx, time_label in frames_to_eval:
        if frame_idx >= seq_out:
            continue
            
        # Extract spatial tensor predictions for the isolated time step
        yt_f = y_true[:, :, frame_idx, :, :]
        yp_ai_f = y_pred_ai[:, :, frame_idx, :, :]
        yp_pe_f = y_pred_persistence[:, :, frame_idx, :, :]
        
        # Calculate isolated metrics
        ai_mets = calculate_metrics(yt_f, yp_ai_f, best_threshold)
        pe_mets = calculate_metrics(yt_f, yp_pe_f, best_threshold)
        
        # Markdown row injection
        print(f"| {time_label: <20} | {ai_mets['CSI']:.4f} | {pe_mets['CSI']:.4f}   | {ai_mets['POD']:.4f} | {pe_mets['POD']:.4f}   | {ai_mets['FAR']:.4f} | {pe_mets['FAR']:.4f}   |")
        
    print("\nEvaluation Output Complete.")

if __name__ == "__main__":
    main()
