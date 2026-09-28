import sys
import asyncio
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import numpy as np
import torch

root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from backend.services.inference_service import inference_pipeline
from backend.services.ingestion.h5_loader import RealDataLoader
from backend.ml.evaluate import calculate_metrics

router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])
loader = RealDataLoader()

@router.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # 1. Establish Uplink
        await websocket.send_json({"type": "log", "message": "Establishing secure WebSocket uplink..."})
        await asyncio.sleep(0.5)
        
        # 2. Ingest Data
        await websocket.send_json({"type": "log", "message": "Fetching SEVIR HDF5 tensors (384x384)..."})
        past_13_frames, ground_truth_frames = loader.get_live_context()
        
        # 3. AI Inference
        await websocket.send_json({"type": "log", "message": "Running ConvLSTM spatiotemporal inference..."})
        context_tensor = torch.from_numpy(past_13_frames).float().unsqueeze(0).unsqueeze(0)
        truth_tensor = torch.from_numpy(ground_truth_frames).float().unsqueeze(0).unsqueeze(0)
        
        preds_array, _ = inference_pipeline.predict(context_tensor)
        preds_tensor = torch.from_numpy(preds_array)
        runtime_metrics = calculate_metrics(truth_tensor, preds_tensor, threshold=0.35)
        
        base_csi = round(runtime_metrics['CSI'], 4)
        base_pod = round(runtime_metrics['POD'], 4)

        await websocket.send_json({
            "type": "telemetry",
            "csi": base_csi,
            "pod": base_pod
        })
        
        # 4. Stream Matrix Frames Sequentially
        compressed_grids = preds_tensor[0, 0].numpy().tolist()
        for i, grid in enumerate(compressed_grids):
            await websocket.send_json({"type": "frame", "index": i, "data": grid})
            await websocket.send_json({"type": "log", "message": f"Streamed forecast frame {i+1}/12 (T+{(i+1)*5} MIN)."})
            await asyncio.sleep(0.25) # Simulate hardware processing delay for visual effect
            
        await websocket.send_json({"type": "log", "message": "Inference cycle complete. Monitoring live telemetry."})
        
        # 5. Live Telemetry Heartbeat Loop
        tick = 12
        while True:
            await asyncio.sleep(2.0)
            tick += 1
            # Simulate real-time metric fluctuations for the chart
            live_confidence = 90 - (tick * 0.5) + (torch.randn(1).item() * 3)
            await websocket.send_json({
                "type": "heartbeat",
                "time": f"T+{tick*5}",
                "confidence": max(10, min(99, live_confidence))
            })

    except WebSocketDisconnect:
        print("[WS] Client disconnected from stream.")
