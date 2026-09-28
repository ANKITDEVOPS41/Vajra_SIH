from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio

from backend.services.ingestion.synthetic_generator import SyntheticGenerator
from backend.services.nowcasting.optical_flow import compute_optical_flow, extrapolate_reflectivity
from backend.services.nowcasting.ai_inference import run_ai_inference
from backend.services.validation.metrics import compute_all_metrics

# Import the newly constructed DL operational router
from backend.routers.forecast import router as forecast_router

app = FastAPI(title="VAJRA Backend API", version="1.0.0")

# Wire CORS Middleware logic securely for frontend traversal
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production specify actual deployment domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Wire DL infrastructure to global module execution graph
app.include_router(forecast_router)

# Setup synthetic data to act as "Database"
generator = SyntheticGenerator()
# Let's say T=12 is Now (T0), meaning T-3h to T+6h total 18 frames?
# For our scenario: 12 frames of past, 12 frames of future. Let's do 24.
generator = SyntheticGenerator()
historical_events = generator.generate_events(num_frames=24)
# True sequence: historical_events
# Past sequence (T_minus_6 to T0): historical_events[:12]
# Ground Truth future: historical_events[12:]

@app.get("/api/v1/forecast/stream")
async def get_forecast_stream(event: str = "uttarakhand_2023", t: int = 4):
    """
    Returns AI predicted forecast at time step {t}.
    t is the number of steps into the future. Each step is 30 mins.
    """
    if event != "uttarakhand_2023":
        raise HTTPException(status_code=404, detail="Event not found")
        
    if t < 0 or t > 12:
        raise HTTPException(status_code=400, detail="Invalid time step, must be 0 to 12")

    past_frames = historical_events[:12]
    # In a real app this is cached or retrieved from DB.
    # Run the AI surrogate model for `t` steps
    forecasts = run_ai_inference(past_frames, bt_tensor=None, cape_tensor=None, steps=t+1)
    
    # Return 2D array representing MaxZ (radar)
    return {"step": t, "grid": forecasts[t].tolist()}

@app.get("/api/v1/metrics/evaluate")
async def evaluate_metrics(lead_time: int = 120):
    """
    Evaluates the model against truth out to lead_time (in minutes).
    If step is 30 mins, 120 means t=4.
    """
    steps = lead_time // 30
    if steps > 12 or steps < 1:
         raise HTTPException(status_code=400, detail="Invalid lead time")
         
    past_frames = historical_events[:12]
    ground_truth = historical_events[12:]
    
    # 1. Baseline Optical Flow
    flow = compute_optical_flow(past_frames[-2], past_frames[-1])
    baseline_extrap = extrapolate_reflectivity(past_frames[-1], flow, steps=steps)
    baseline_pred = baseline_extrap[-1]
    
    # 2. AI Inference
    ai_extrap = run_ai_inference(past_frames, bt_tensor=None, cape_tensor=None, steps=steps)
    ai_pred = ai_extrap[-1]
    
    # Truth frame for this step
    obs = ground_truth[steps - 1]
    
    # Metrics
    ai_metrics = compute_all_metrics(ai_pred, obs, [35, 50])
    baseline_metrics = compute_all_metrics(baseline_pred, obs, [35, 50])
    
    return {
        "lead_time": lead_time,
        "ai_metrics": ai_metrics,
        "baseline_metrics": baseline_metrics
    }
