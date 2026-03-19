
import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import random

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tentative d'import de la base de données
try:
    from database import DatabaseManager
    db_available = True
    logger.info("✅ Database module loaded successfully")
except ImportError as e:
    logger.warning(f"⚠️ Database module not available: {e}")
    db_available = False

app = FastAPI(
    title="PulseBoard - Event Analytics Platform",
    description="Plateforme d'analyse d'événements avec prédictions ML",
    version="2.0.0"
)

# Données simulées pour le mode fallback
MOCK_EVENTS = [
    {
        "id": 1,
        "name": "🎵 Festival Jazz d'Été",
        "date": "2024-07-15",
        "venue": "Parc Central",
        "capacity": 5000,
        "tickets_sold": 3750,
        "revenue": 187500,
        "status": "active"
    },
    {
        "id": 2,
        "name": "🎨 Exposition Art Moderne",
        "date": "2024-08-20",
        "venue": "Galerie Métropolitaine",
        "capacity": 2000,
        "tickets_sold": 1650,
        "revenue": 82500,
        "status": "active"
    },
    {
        "id": 3,
        "name": "🏃 Marathon de la Ville",
        "date": "2024-09-10",
        "venue": "Centre-ville",
        "capacity": 10000,
        "tickets_sold": 8500,
        "revenue": 425000,
        "status": "active"
    },
    {
        "id": 4,
        "name": "🎭 Théâtre Classique",
        "date": "2024-10-05",
        "venue": "Opéra National",
        "capacity": 1500,
        "tickets_sold": 1200,
        "revenue": 120000,
        "status": "active"
    },
    {
        "id": 5,
        "name": "🎪 Cirque Fantastique",
        "date": "2024-11-12",
        "venue": "Grand Chapiteau",
        "capacity": 3000,
        "tickets_sold": 2100,
        "revenue": 157500,
        "status": "active"
    }
]

# Initialisation de la base de données
db_manager = None
if db_available:
    try:
        db_manager = DatabaseManager()
        logger.info("✅ Database manager initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        db_manager = None

@app.get("/health")
async def health_check():
    """Health check endpoint avec statut de la base de données"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database_connected": False,
        "database_type": "none"
    }
    
    if db_manager:
        try:
            # Test de connexion à la base
            test_result = db_manager.test_connection()
            health_status["database_connected"] = test_result
            health_status["database_type"] = "neon_postgresql"
            logger.info("✅ Database connection test successful")
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}")
            health_status["database_connected"] = False
            health_status["error"] = str(e)
    
    return health_status

@app.get("/events")
async def get_events():
    """Récupérer tous les événements"""
    if db_manager:
        try:
            events = db_manager.get_all_events()
            logger.info(f"✅ Retrieved {len(events)} events from database")
            return {"events": events, "source": "neon_database"}
        except Exception as e:
            logger.error(f"❌ Failed to get events from database: {e}")
    
    # Fallback vers les données simulées
    logger.info("⚠️ Using mock data as fallback")
    return {"events": MOCK_EVENTS, "source": "mock_data"}

@app.get("/events/{event_id}")
async def get_event(event_id: int):
    """Récupérer un événement spécifique"""
    if db_manager:
        try:
            event = db_manager.get_event(event_id)
            if event:
                return event
        except Exception as e:
            logger.error(f"❌ Failed to get event {event_id}: {e}")
    
    # Fallback vers les données simulées
    event = next((e for e in MOCK_EVENTS if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.post("/events")
async def create_event(event_data: Dict[str, Any]):
    """Créer un nouvel événement"""
    if db_manager:
        try:
            event_id = db_manager.create_event(event_data)
            logger.info(f"✅ Created event with ID: {event_id}")
            return {"message": "Event created successfully", "id": event_id}
        except Exception as e:
            logger.error(f"❌ Failed to create event: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")
    
    # En mode simulation, on simule juste la création
    new_id = max([e["id"] for e in MOCK_EVENTS]) + 1
    return {"message": "Event created (simulation mode)", "id": new_id}

@app.get("/predict/{event_id}")
async def predict_sales(event_id: int):
    """Prédictions ML simulées pour un événement"""
    # Simulation de prédictions ML
    predictions = {
        "event_id": event_id,
        "predicted_sales": random.randint(1000, 5000),
        "confidence": round(random.uniform(0.75, 0.95), 2),
        "trend": random.choice(["increasing", "stable", "decreasing"]),
        "peak_day": random.choice(["Friday", "Saturday", "Sunday"]),
        "recommended_price": round(random.uniform(25, 150), 2),
        "model_version": "v2.1.0",
        "generated_at": datetime.now().isoformat()
    }
    
    return predictions

@app.get("/test")
async def test_endpoint():
    """Endpoint de test pour vérifier le fonctionnement"""
    test_results = {
        "message": "🎉 PulseBoard API is working!",
        "timestamp": datetime.now().isoformat(),
        "database_available": db_manager is not None,
        "endpoints": {
            "health": "/health",
            "events": "/events",
            "predictions": "/predict/{event_id}",
            "docs": "/docs"
        }
    }
    
    if db_manager:
        try:
            db_test = db_manager.test_connection()
            test_results["database_status"] = "✅ Connected to Neon PostgreSQL" if db_test else "❌ Connection failed"
        except Exception as e:
            test_results["database_status"] = f"❌ Error: {str(e)}"
    else:
        test_results["database_status"] = "⚠️ Running in simulation mode"
    
    return test_results

# Servir les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Page d'accueil avec interface web"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
