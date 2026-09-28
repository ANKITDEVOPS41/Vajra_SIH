import numpy as np
from backend.services.nowcasting.optical_flow import compute_optical_flow

def run_ai_inference(sequence_frames: list, bt_tensor: np.ndarray = None, cape_tensor: np.ndarray = None, steps: int = 12):
    """
    Simulates a Spatiotemporal Network (like ConvLSTM or Earthformer surrogate).
    Takes a sequence of past frames (e.g., T-3h to T0) and external predictors (Brightness Temp, CAPE).
    Applies non-linear growth and decay equations over the steps (+6h forecast).
    """
    if len(sequence_frames) < 2:
        raise ValueError("Need at least 2 frames for motion inference.")
    
    frame_t0 = sequence_frames[-1]
    flow = compute_optical_flow(sequence_frames[-2], frame_t0)
    
    h, w = frame_t0.shape
    mesh_x, mesh_y = np.meshgrid(np.arange(w), np.arange(h))
    
    forecasts = []
    current_frame = frame_t0.copy()
    
    multiplier = 1.05 # Neural network non-linear growth surrogate factor

    for step in range(steps):
        # 1. Advection component
        new_x = (mesh_x - flow[..., 0]).astype(np.float32)
        new_y = (mesh_y - flow[..., 1]).astype(np.float32)
        
        import cv2
        advected_frame = cv2.remap(current_frame, new_x, new_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        
        # 2. Add non-linear growth Surrogate
        # In reality, this would be computed by the Deep Learning model exploiting CAPE / BT rules.
        # If CAPE is high (implied here as constant > 0 for demo), amplify intensity initially.
        if step < steps // 2:
            growth = advected_frame * multiplier # Growth phase
        else:
            growth = advected_frame * 0.95 # Decay phase
            
        # 3. Add influence of satellite BT if provided (Simulated: lower BT -> more growth)
        if bt_tensor is not None:
             growth += (273.15 - bt_tensor) * 0.1
             
        final_frame = np.clip(growth, 0, 70)
        forecasts.append(final_frame)
        current_frame = final_frame
    
    return forecasts
