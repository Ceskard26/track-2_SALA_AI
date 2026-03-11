"""
RainCaster Galápagos — Backend API
FastAPI + Uvicorn · EC2 t3.small

TODO markers show exactly where to plug in the real model.
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import Optional
import random

# ── TODO: uncomment when model is ready ──────────────────
# from model import RainCasterModel
# model = RainCasterModel.load("checkpoints/best_model.pt")
# ─────────────────────────────────────────────────────────

app = FastAPI(
    title="RainCaster Galápagos API",
    description="Early Warning System — San Cristóbal Island",
    version="1.0.0"
)

# ── CORS — allow frontend from CloudFront + S3 ───────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # TODO: restrict to CloudFront URL in production
    allow_methods=["GET"],
    allow_headers=["*"],
)

# ── STATION METADATA ─────────────────────────────────────
STATIONS = {
    "jun":  {"name": "El Junco",   "elev": 548, "lat": -0.896537, "lon": -89.481624},
    "cer":  {"name": "Cerro Alto", "elev": 517, "lat": -0.887048, "lon": -89.530985},
    "mira": {"name": "El Mirador", "elev": 387, "lat": -0.886247, "lon": -89.539586},
    "merc": {"name": "Merceditas", "elev": 100, "lat": -0.889712, "lon": -89.442020},
}

# ── MOCK DATA ─────────────────────────────────────────────
# TODO: Remove all MOCK data once model is trained.
# Replace get_prediction() with real model inference.
MOCK_PREDICTIONS = {
    "jun":  {1: {"cls": 0, "prob": 0.82, "precip": 0.00, "rh": 78.0, "temp": 22.1, "wind": 1.2},
             3: {"cls": 1, "prob": 0.65, "precip": 0.20, "rh": 84.0, "temp": 21.8, "wind": 1.5},
             6: {"cls": 1, "prob": 0.58, "precip": 0.40, "rh": 87.0, "temp": 21.4, "wind": 1.8}},
    "cer":  {1: {"cls": 1, "prob": 0.71, "precip": 0.15, "rh": 82.0, "temp": 20.5, "wind": 2.1},
             3: {"cls": 2, "prob": 0.60, "precip": 0.62, "rh": 89.0, "temp": 20.0, "wind": 2.4},
             6: {"cls": 2, "prob": 0.55, "precip": 0.92, "rh": 91.0, "temp": 19.8, "wind": 2.6}},
    "mira": {1: {"cls": 0, "prob": 0.88, "precip": 0.00, "rh": 71.0, "temp": 24.3, "wind": 0.9},
             3: {"cls": 0, "prob": 0.79, "precip": 0.00, "rh": 73.0, "temp": 24.0, "wind": 1.0},
             6: {"cls": 1, "prob": 0.62, "precip": 0.18, "rh": 76.0, "temp": 23.5, "wind": 1.2}},
    "merc": {1: {"cls": 0, "prob": 0.85, "precip": 0.00, "rh": 69.0, "temp": 25.1, "wind": 1.4},
             3: {"cls": 0, "prob": 0.77, "precip": 0.00, "rh": 71.0, "temp": 24.8, "wind": 1.5},
             6: {"cls": 0, "prob": 0.70, "precip": 0.05, "rh": 74.0, "temp": 24.3, "wind": 1.7}},
}

# ── CLASS THRESHOLDS (from raincaster_guidelines.pdf) ────
THRESHOLDS = {
    1: {"light": 0.000, "heavy": 0.254},
    3: {"light": 0.000, "heavy": 0.508},
    6: {"light": 0.000, "heavy": 0.762},
}

def precip_to_class(precip_mm: float, horizon: int) -> int:
    """Convert accumulated precipitation to class label (0/1/2)."""
    t = THRESHOLDS[horizon]
    if precip_mm == 0:
        return 0
    elif precip_mm <= t["heavy"]:
        return 1
    else:
        return 2

def get_prediction(station_id: str, horizon: int) -> dict:
    """
    Get prediction for a station and horizon.

    ── TODO: Replace this entire function with real model inference ──
    When the model is ready:

    1. Load the latest sensor readings for the station:
       features = load_latest_features(station_id)   # shape: (96, n_features)

    2. Run model inference:
       pred_class, pred_prob = model.predict(features, horizon)

    3. Return real values:
       return {
           "pred_class":    int(pred_class),
           "pred_prob":     float(pred_prob),
           "obs_precip_mm": float(get_observed_precip(station_id, horizon)),
           "rh_avg":        float(get_current_rh(station_id)),
           "temp_c":        float(get_current_temp(station_id)),
           "wind_ms":       float(get_current_wind(station_id)),
       }
    ──────────────────────────────────────────────────────────────────
    """
    d = MOCK_PREDICTIONS[station_id][horizon]
    return {
        "pred_class":    d["cls"],
        "pred_prob":     d["prob"],
        "obs_precip_mm": d["precip"],
        "rh_avg":        d["rh"],
        "temp_c":        d["temp"],
        "wind_ms":       d["wind"],
        "data_source":   "mock",   # TODO: change to "model" when ready
    }


# ══════════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════════

@app.get("/health")
def health():
    """Health check — used by EC2 load balancer."""
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "model_loaded": False,  # TODO: set True when model is loaded
    }


@app.get("/api/stations")
def get_stations():
    """Return metadata for all 4 stations."""
    return [
        {
            "id":          sid,
            "name":        s["name"],
            "elev_m":      s["elev"],
            "lat":         s["lat"],
            "lon":         s["lon"],
            "last_update": datetime.utcnow().isoformat(),
            "status":      "active",
        }
        for sid, s in STATIONS.items()
    ]


@app.get("/api/predict")
def predict(
    station: str = Query(..., description="Station ID: jun | cer | mira | merc"),
    horizon: int = Query(..., description="Forecast horizon in hours: 1 | 3 | 6"),
):
    """
    Get precipitation forecast for a station and horizon.

    Returns pred_class (0=No Rain, 1=Light, 2=Heavy),
    pred_prob (model confidence), and current sensor readings.
    """
    if station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found. Valid: {list(STATIONS.keys())}")
    if horizon not in (1, 3, 6):
        raise HTTPException(status_code=400, detail="Horizon must be 1, 3, or 6")

    pred = get_prediction(station, horizon)

    return {
        "timestamp":     datetime.utcnow().isoformat(),
        "station_id":    station,
        "station_name":  STATIONS[station]["name"],
        "horizon_h":     horizon,
        "pred_class":    pred["pred_class"],
        "pred_prob":     pred["pred_prob"],
        "class_label":   ["No Rain", "Light Rain", "Heavy Rain"][pred["pred_class"]],
        "obs_precip_mm": pred["obs_precip_mm"],
        "conditions": {
            "rh_avg":   pred["rh_avg"],
            "temp_c":   pred["temp_c"],
            "wind_ms":  pred["wind_ms"],
        },
        "thresholds": THRESHOLDS[horizon],
        "data_source":   pred["data_source"],
    }


@app.get("/api/predict/all")
def predict_all(
    horizon: int = Query(1, description="Forecast horizon: 1 | 3 | 6"),
):
    """Get predictions for all 4 stations at once."""
    if horizon not in (1, 3, 6):
        raise HTTPException(status_code=400, detail="Horizon must be 1, 3, or 6")

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "horizon_h": horizon,
        "stations": {
            sid: get_prediction(sid, horizon)
            for sid in STATIONS
        }
    }


@app.get("/api/history")
def history(
    station: str = Query(..., description="Station ID"),
    hours:   int = Query(24,  description="Hours of history (max 168)"),
):
    """
    Return historical precipitation for the chart.

    TODO: Replace mock data with real CSV/database query:
    df = load_station_csv(station)
    recent = df.last(f'{hours}h')['rain_mm'].resample('1h').sum()
    return recent.reset_index().to_dict('records')
    """
    if station not in STATIONS:
        raise HTTPException(status_code=404, detail=f"Station '{station}' not found.")
    hours = min(hours, 168)

    # Mock: generate plausible hourly precipitation
    # TODO: replace with real historical data from CSVs
    mock_precip = [0,0,0,0.1,0,0,0.15,0,0,0.3,0.8,2.1,
                   0.4,0,0,0,0.05,0,0,0.12,0,0,0.6,1.2]
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    records = []
    for i in range(hours):
        t = now - timedelta(hours=hours-1-i)
        precip = mock_precip[i % len(mock_precip)]
        records.append({
            "timestamp":  t.isoformat(),
            "precip_mm":  precip,
            "obs_class":  precip_to_class(precip, 1),
        })

    return {
        "station_id": station,
        "hours":      hours,
        "data":       records,
    }


@app.get("/api/metrics")
def metrics():
    """
    Return model evaluation metrics for the dashboard.

    TODO: Replace with real metrics computed after walk-forward validation.
    After training, save metrics to metrics.json and load here:

    import json
    with open("metrics.json") as f:
        return json.load(f)
    """
    return {
        "model":       "pending",
        "macro_f1":    None,   # TODO: fill after training
        "weighted_f1": None,   # TODO: fill after training
        "micro_f1":    None,   # TODO: fill after training
        "trained_at":  None,
        "horizons":    [1, 3, 6],
        "stations":    list(STATIONS.keys()),
        "status":      "mock — model not yet trained",
    }
