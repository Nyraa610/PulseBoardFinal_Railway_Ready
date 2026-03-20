import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
import httpx
import asyncio

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="PulseBoard - Weather Analytics Platform",
    description="Plateforme d'analyse météorologique avec données OpenWeatherMap",
    version="3.0.0"
)

# Configuration OpenWeatherMap
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"

# Villes françaises supportées
CITIES = {
    "paris": {"name": "Paris", "lat": 48.8566, "lon": 2.3522},
    "lyon": {"name": "Lyon", "lat": 45.7640, "lon": 4.8357},
    "marseille": {"name": "Marseille", "lat": 43.2965, "lon": 5.3698},
    "bordeaux": {"name": "Bordeaux", "lat": 44.8378, "lon": -0.5792},
    "lille": {"name": "Lille", "lat": 50.6292, "lon": 3.0573},
    "toulouse": {"name": "Toulouse", "lat": 43.6047, "lon": 1.4442},
    "nice": {"name": "Nice", "lat": 43.7102, "lon": 7.2620}
}

class WeatherService:
    def __init__(self):
        self.api_key = OPENWEATHER_API_KEY
        self.base_url = OPENWEATHER_BASE_URL
        
    async def get_current_weather(self, city: str) -> Dict[str, Any]:
        """Récupérer la météo actuelle pour une ville"""
        if not self.api_key:
            return self._get_mock_weather(city)
            
        city_info = CITIES.get(city.lower())
        if not city_info:
            raise HTTPException(status_code=404, detail="Ville non trouvée")
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "lat": city_info["lat"],
                        "lon": city_info["lon"],
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "fr"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "city": city_info["name"],
                    "temperature": round(data["main"]["temp"]),
                    "feels_like": round(data["main"]["feels_like"]),
                    "humidity": data["main"]["humidity"],
                    "pressure": data["main"]["pressure"],
                    "wind_speed": round(data["wind"]["speed"] * 3.6),  # m/s vers km/h
                    "visibility": round(data.get("visibility", 10000) / 1000),  # mètres vers km
                    "description": data["weather"][0]["description"].capitalize(),
                    "icon": data["weather"][0]["icon"],
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Erreur API OpenWeatherMap pour {city}: {e}")
            return self._get_mock_weather(city)
    
    async def get_forecast(self, city: str) -> Dict[str, Any]:
        """Récupérer les prévisions pour une ville"""
        if not self.api_key:
            return self._get_mock_forecast(city)
            
        city_info = CITIES.get(city.lower())
        if not city_info:
            raise HTTPException(status_code=404, detail="Ville non trouvée")
            
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "lat": city_info["lat"],
                        "lon": city_info["lon"],
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "fr"
                    },
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
                
                forecast = []
                for item in data["list"][:8]:  # 24h de prévisions (8 x 3h)
                    forecast.append({
                        "time": item["dt_txt"],
                        "temp": round(item["main"]["temp"]),
                        "feels_like": round(item["main"]["feels_like"]),
                        "humidity": item["main"]["humidity"],
                        "description": item["weather"][0]["description"].capitalize(),
                        "icon": item["weather"][0]["icon"]
                    })
                
                return {
                    "city": city_info["name"],
                    "forecast_24h": forecast,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Erreur prévisions OpenWeatherMap pour {city}: {e}")
            return self._get_mock_forecast(city)
    
    def _get_mock_weather(self, city: str) -> Dict[str, Any]:
        """Données météo simulées en cas d'erreur API"""
        mock_data = {
            "paris": {"temp": 22, "feels_like": 25, "humidity": 65, "wind": 12, "pressure": 1013, "visibility": 15, "desc": "Ensoleillé", "icon": "01d"},
            "lyon": {"temp": 24, "feels_like": 27, "humidity": 58, "wind": 8, "pressure": 1015, "visibility": 20, "desc": "Partiellement nuageux", "icon": "02d"},
            "marseille": {"temp": 26, "feels_like": 29, "humidity": 62, "wind": 15, "pressure": 1012, "visibility": 18, "desc": "Ensoleillé", "icon": "01d"},
            "bordeaux": {"temp": 21, "feels_like": 24, "humidity": 70, "wind": 10, "pressure": 1014, "visibility": 12, "desc": "Nuageux", "icon": "03d"},
            "lille": {"temp": 18, "feels_like": 21, "humidity": 75, "wind": 14, "pressure": 1016, "visibility": 10, "desc": "Bruine", "icon": "09d"}
        }
        
        data = mock_data.get(city.lower(), mock_data["paris"])
        city_info = CITIES.get(city.lower(), CITIES["paris"])
        
        return {
            "city": city_info["name"],
            "temperature": data["temp"],
            "feels_like": data["feels_like"],
            "humidity": data["humidity"],
            "pressure": data["pressure"],
            "wind_speed": data["wind"],
            "visibility": data["visibility"],
            "description": data["desc"],
            "icon": data["icon"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_mock_forecast(self, city: str) -> Dict[str, Any]:
        """Prévisions simulées en cas d'erreur API"""
        base_time = datetime.now()
        forecast = []
        
        for i in range(8):
            hour_offset = i * 3
            forecast_time = base_time.replace(minute=0, second=0, microsecond=0)
            forecast_time = forecast_time.replace(hour=(forecast_time.hour + hour_offset) % 24)
            
            temp_variation = [22, 24, 21, 19, 17, 16, 18, 20][i]
            
            forecast.append({
                "time": forecast_time.strftime("%Y-%m-%d %H:%M:%S"),
                "temp": temp_variation,
                "feels_like": temp_variation + 3,
                "humidity": 65 + (i * 2),
                "description": "Ensoleillé",
                "icon": "01d" if 6 <= (forecast_time.hour) <= 18 else "01n"
            })
        
        city_info = CITIES.get(city.lower(), CITIES["paris"])
        return {
            "city": city_info["name"],
            "forecast_24h": forecast,
            "timestamp": datetime.now().isoformat()
        }

# Service de qualité de l'air simulé
class AirQualityService:
    def get_air_quality(self, city: str) -> Dict[str, Any]:
        """Simuler la qualité de l'air (en attendant une vraie API)"""
        import random
        
        # Simulation basée sur la ville
        city_aqi = {
            "paris": random.randint(40, 80),
            "lyon": random.randint(35, 70),
            "marseille": random.randint(45, 85),
            "bordeaux": random.randint(30, 65),
            "lille": random.randint(50, 90)
        }
        
        aqi = city_aqi.get(city.lower(), random.randint(40, 80))
        
        if aqi <= 50:
            label, color, advice = "Bon", "green", "Parfait pour les activités outdoor"
        elif aqi <= 100:
            label, color, advice = "Modéré", "yellow", "Activités outdoor recommandées avec modération"
        elif aqi <= 150:
            label, color, advice = "Mauvais", "orange", "Limitez les activités outdoor intensives"
        else:
            label, color, advice = "Très mauvais", "red", "Évitez les activités outdoor"
        
        return {
            "aqi": aqi,
            "pm25": random.randint(10, 35),
            "no2": random.randint(20, 50),
            "o3": random.randint(60, 120),
            "label": label,
            "color": color,
            "advice": advice,
            "timestamp": datetime.now().isoformat()
        }

# Service d'événements simulé
class EventsService:
    def get_events(self, city: str) -> Dict[str, Any]:
        """Simuler des événements pour la ville"""
        events_data = {
            "paris": [
                {"name": "Festival Jazz de Paris", "date": "2026-03-20T19:00:00", "location": "Place de la République", "category": "culture"},
                {"name": "Marché Bio Montmartre", "date": "2026-03-21T09:00:00", "location": "Place du Tertre", "category": "marché"},
                {"name": "Concert Philharmonique", "date": "2026-03-22T20:30:00", "location": "Salle Pleyel", "category": "concert"}
            ],
            "lyon": [
                {"name": "Fête des Lumières", "date": "2026-03-20T18:00:00", "location": "Vieux Lyon", "category": "culture"},
                {"name": "Marathon du Rhône", "date": "2026-03-21T08:00:00", "location": "Berges du Rhône", "category": "sport"}
            ],
            "marseille": [
                {"name": "Festival de Marseille", "date": "2026-03-20T17:00:00", "location": "Vieux Port", "category": "culture"},
                {"name": "Marché aux Poissons", "date": "2026-03-21T06:00:00", "location": "Quai des Belges", "category": "marché"}
            ]
        }
        
        city_events = events_data.get(city.lower(), events_data["paris"])
        
        return {
            "events": city_events,
            "count": len(city_events),
            "timestamp": datetime.now().isoformat()
        }

# Service de prédictions IA simulé
class PredictionService:
    def get_prediction(self, current_aqi: int) -> Dict[str, Any]:
        """Simuler des prédictions IA"""
        import random
        
        # Simuler une prédiction basée sur l'AQI actuel
        predicted_aqi = max(10, current_aqi + random.randint(-15, 10))
        confidence = random.randint(75, 95)
        
        forecast = []
        for i in range(1, 7):
            variation = random.randint(-5, 5)
            forecast.append({
                "hour": f"+{i}h",
                "aqi": max(10, predicted_aqi + variation)
            })
        
        return {
            "predicted_aqi_6h": predicted_aqi,
            "confidence": confidence,
            "forecast": forecast,
            "timestamp": datetime.now().isoformat()
        }

# Initialisation des services
weather_service = WeatherService()
air_service = AirQualityService()
events_service = EventsService()
prediction_service = PredictionService()

@app.get("/health")
async def health_check():
    """Health check avec statut OpenWeatherMap"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openweather_api": bool(OPENWEATHER_API_KEY),
        "supported_cities": len(CITIES)
    }
    
    if OPENWEATHER_API_KEY:
        try:
            # Test rapide de l'API
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{OPENWEATHER_BASE_URL}/weather",
                    params={
                        "lat": 48.8566,
                        "lon": 2.3522,
                        "appid": OPENWEATHER_API_KEY
                    },
                    timeout=5.0
                )
                health_status["openweather_status"] = "connected" if response.status_code == 200 else "error"
        except Exception as e:
            health_status["openweather_status"] = f"error: {str(e)}"
    else:
        health_status["openweather_status"] = "no_api_key"
    
    return health_status

@app.get("/cities")
async def get_cities():
    """Liste des villes supportées"""
    return {
        "cities": [info["name"] for info in CITIES.values()],
        "count": len(CITIES),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/weather/current/{city}")
async def get_current_weather(city: str):
    """Météo actuelle pour une ville"""
    try:
        weather_data = await weather_service.get_current_weather(city)
        return weather_data
    except Exception as e:
        logger.error(f"Erreur météo pour {city}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weather/forecast/{city}")
async def get_weather_forecast(city: str):
    """Prévisions météo pour une ville"""
    try:
        forecast_data = await weather_service.get_forecast(city)
        return forecast_data
    except Exception as e:
        logger.error(f"Erreur prévisions pour {city}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/weather/all")
async def get_all_weather():
    """Météo actuelle pour toutes les villes"""
    try:
        tasks = []
        for city_key in CITIES.keys():
            tasks.append(weather_service.get_current_weather(city_key))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        weather_data = {}
        for i, city_key in enumerate(CITIES.keys()):
            if not isinstance(results[i], Exception):
                weather_data[city_key] = results[i]
            else:
                logger.error(f"Erreur pour {city_key}: {results[i]}")
        
        return {
            "cities": weather_data,
            "count": len(weather_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur météo globale: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/dashboard/{city}")
async def get_dashboard_data(city: str):
    """Endpoint principal pour le dashboard"""
    try:
        # Récupération parallèle de toutes les données
        weather_task = weather_service.get_current_weather(city)
        forecast_task = weather_service.get_forecast(city)
        
        current_weather, forecast = await asyncio.gather(weather_task, forecast_task)
        
        # Services synchrones
        air_quality = air_service.get_air_quality(city)
        events = events_service.get_events(city)
        prediction = prediction_service.get_prediction(air_quality["aqi"])
        
        # Calcul du score urbain
        weather_score = min(100, max(0, 100 - abs(current_weather["temperature"] - 22) * 5))
        air_score = min(100, max(0, 100 - air_quality["aqi"]))
        events_score = min(100, events["count"] * 25)
        
        urban_score = int(
            weather_score * 0.4 + 
            air_score * 0.4 + 
            events_score * 0.2
        )
        
        if urban_score >= 80:
            score_label = "Excellent"
        elif urban_score >= 60:
            score_label = "Bon"
        elif urban_score >= 40:
            score_label = "Moyen"
        else:
            score_label = "Mauvais"
        
        return {
            "weather": {
                "current": current_weather,
                "forecast_24h": forecast["forecast_24h"]
            },
            "air": air_quality,
            "events": events,
            "prediction": prediction,
            "score": {
                "score": urban_score,
                "label": score_label,
                "breakdown": {
                    "weather": {"score": int(weather_score), "weight": 0.4},
                    "air_quality": {"score": int(air_score), "weight": 0.4},
                    "events": {"score": int(events_score), "weight": 0.2}
                }
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur dashboard pour {city}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_endpoint():
    """Test de l'API avec OpenWeatherMap"""
    test_results = {
        "message": "🌤️ PulseBoard Weather API is working!",
        "timestamp": datetime.now().isoformat(),
        "openweather_configured": bool(OPENWEATHER_API_KEY),
        "supported_cities": len(CITIES),
        "endpoints": {
            "health": "/health",
            "cities": "/cities",
            "current_weather": "/weather/current/{city}",
            "forecast": "/weather/forecast/{city}",
            "dashboard": "/api/dashboard/{city}",
            "docs": "/docs"
        }
    }
    
    if OPENWEATHER_API_KEY:
        try:
            # Test avec Paris
            test_weather = await weather_service.get_current_weather("paris")
            test_results["openweather_test"] = "✅ API OpenWeatherMap fonctionnelle"
            test_results["sample_data"] = {
                "city": test_weather["city"],
                "temperature": f"{test_weather['temperature']}°C",
                "description": test_weather["description"]
            }
        except Exception as e:
            test_results["openweather_test"] = f"❌ Erreur API: {str(e)}"
    else:
        test_results["openweather_test"] = "⚠️ Clé API manquante - Mode simulation"
    
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
    logger.info(f"🚀 Démarrage PulseBoard Weather sur le port {port}")
    logger.info(f"🔑 OpenWeatherMap API: {'✅ Configurée' if OPENWEATHER_API_KEY else '❌ Manquante'}")
    logger.info(f"🏙️ Villes supportées: {len(CITIES)}")
    uvicorn.run(app, host="0.0.0.0", port=port)
