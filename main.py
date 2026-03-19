from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import DatabaseManager
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import ML functions
from ml.ml_utils import predire_6h, VILLES

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="PulseBoard API + ML Predictions", 
    version="2.0.0",
    description="Dashboard météo avec prédictions ML"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir les fichiers statiques (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Base de données
db = DatabaseManager()

@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    try:
        await db.connect()
        logger.info("✅ Database connection established")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    try:
        await db.disconnect()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")

# ============================================================
# ROUTES FRONTEND
# ============================================================

@app.get("/")
async def serve_frontend():
    """Sert le frontend principal"""
    return FileResponse("static/index.html")

@app.get("/health")
async def health_check():
    """Vérification de l'état de l'API"""
    try:
        return {
            "status": "healthy",
            "database_connected": True,
            "ml_models_loaded": len(VILLES) > 0,
            "ml_cities": list(VILLES.keys()),
            "timestamp": datetime.now().isoformat() + "Z"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat() + "Z"
        }

# ============================================================
# ROUTES API MÉTÉO (EXISTANTES)
# ============================================================

@app.get("/api/cities")
async def get_cities():
    """Récupère toutes les villes"""
    try:
        cities = await db.get_all_cities() if hasattr(db, 'get_all_cities') else []
        return {"cities": cities}
    except Exception as e:
        logger.error(f"Error fetching cities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/events")
async def get_events():
    """Récupère tous les événements"""
    try:
        events = await db.get_all_events() if hasattr(db, 'get_all_events') else []
        return {"events": events}
    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    """Récupère toutes les métriques météo"""
    try:
        metrics = await db.get_all_weather_data() if hasattr(db, 'get_all_weather_data') else []
        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ROUTES ML PRÉDICTIONS (NOUVELLES)
# ============================================================

@app.get("/api/ml/cities")
async def get_ml_cities():
    """Récupère les villes supportées par le ML"""
    return {
        "cities": list(VILLES.keys()),
        "total": len(VILLES),
        "coordinates": VILLES
    }

@app.get("/api/predict/temperature/{city}")
async def predict_temperature(city: str):
    """Prédit la température pour les 6 prochaines heures"""
    try:
        # Vérifier que la ville est supportée
        if city not in VILLES:
            raise HTTPException(
                status_code=404,
                detail=f"Ville '{city}' non supportée. Villes disponibles : {list(VILLES.keys())}"
            )

        # Faire la prédiction
        resultat = predire_6h(city)
        return {
            "success": True,
            "data": resultat,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error predicting temperature for {city}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/predict/batch")
async def predict_batch():
    """Prédit la température pour toutes les villes supportées"""
    try:
        predictions = {}
        for city in VILLES.keys():
            try:
                predictions[city] = predire_6h(city)
            except Exception as e:
                predictions[city] = {"error": str(e)}
        
        return {
            "success": True,
            "predictions": predictions,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error in batch prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================
# ROUTES DEBUG
# ============================================================

@app.get("/api/debug/status")
async def debug_status():
    """Status complet du système"""
    return {
        "api_status": "running",
        "ml_cities": list(VILLES.keys()),
        "ml_models_count": len(VILLES),
        "database_configured": bool(os.getenv("DATABASE_URL")),
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "local"),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
