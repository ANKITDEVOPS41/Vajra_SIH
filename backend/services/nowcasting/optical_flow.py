import cv2
import numpy as np

def compute_optical_flow(frame1: np.ndarray, frame2: np.ndarray):
    """
    Computes dense optical flow using the Farneback method.
    Frames must be 2D radar reflectivity array in same scale.
    """
    # Normalize arrays to 0-255 for cv2 calculations (Farneback works best on 8-bit images)
    # Assume max dBZ is 70
    scale = 255.0 / 70.0
    f1_scaled = np.clip(frame1 * scale, 0, 255).astype(np.uint8)
    f2_scaled = np.clip(frame2 * scale, 0, 255).astype(np.uint8)

    flow = cv2.calcOpticalFlowFarneback(
        f1_scaled, f2_scaled, None, 
        pyr_scale=0.5, levels=3, winsize=15, 
        iterations=3, poly_n=5, poly_sigma=1.2, flags=0
    )
    return flow

def extrapolate_reflectivity(frame: np.ndarray, flow: np.ndarray, steps: int = 4):
    """
    Extrapolate the radar frame forward linearly based on the motion vector flow.
    If 1 step = 30 mins, step=4 means +2hr.
    """
    h, w = frame.shape
    mesh_x, mesh_y = np.meshgrid(np.arange(w), np.arange(h))
    
    # Predict step-by-step
    current_frame = frame.copy()
    extrapolated_frames = []
    
    for _ in range(steps):
        flow_x = flow[..., 0]
        flow_y = flow[..., 1]
        
        # Calculate new coordinates
        new_x = (mesh_x - flow_x).astype(np.float32)
        new_y = (mesh_y - flow_y).astype(np.float32)
        
        # Remap using OpenCV
        next_frame = cv2.remap(current_frame, new_x, new_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        extrapolated_frames.append(next_frame)
        
        current_frame = next_frame # Simple iterative advection
        
    return extrapolated_frames
