from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import logging
import httpx
import asyncio
from datetime import datetime, timedelta
import random

# ========== IMPORT ML AJOUTÉ ==========
from ml.ml_utils import predire_6h, VILLES

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialisation de l'application FastAPI
app = FastAPI(title="Weather Dashboard", version="1.0.0")

# Configuration des APIs
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "demo_key")
OPENWEATHER_BASE_URL = "https://api.openweathermap.org/data/2.5"
OPENAGENDA_API_KEY = os.environ.get("OPENAGENDA_API_KEY", "demo_key")

# Villes supportées avec leurs coordonnées
CITIES = {
    "paris": {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "openagenda": "paris"},
    "lyon": {"name": "Lyon", "lat": 45.7640, "lon": 4.8357, "openagenda": "lyon"},
    "marseille": {"name": "Marseille", "lat": 43.2965, "lon": 5.3698, "openagenda": "marseille"},
    "bordeaux": {"name": "Bordeaux", "lat": 44.8378, "lon": -0.5792, "openagenda": "bordeaux"},
    "lille": {"name": "Lille", "lat": 50.6292, "lon": 3.0573, "openagenda": "lille"},
    "toulouse": {"name": "Toulouse", "lat": 43.6047, "lon": 1.4442, "openagenda": "toulouse"},
    "nice": {"name": "Nice", "lat": 43.7102, "lon": 7.2620, "openagenda": "nice"}
}


# ==========================================
# SERVICES
# ==========================================

class WeatherService:
    def __init__(self):
        self.api_key = OPENWEATHER_API_KEY
        self.base_url = OPENWEATHER_BASE_URL

    async def get_current_weather(self, city_key: str):
        """Récupérer la météo actuelle"""
        if city_key not in CITIES:
            raise HTTPException(status_code=404, detail="Ville non trouvée")

        city = CITIES[city_key]

        if self.api_key == "demo_key":
            return self._get_mock_weather(city_key)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/weather",
                    params={
                        "lat": city["lat"],
                        "lon": city["lon"],
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "fr"
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return {
                        "temperature": round(data["main"]["temp"]),
                        "feels_like": round(data["main"]["feels_like"]),
                        "humidity": data["main"]["humidity"],
                        "pressure": data["main"]["pressure"],
                        "visibility": round(data.get("visibility", 10000) / 1000),
                        "wind_speed": round(data["wind"]["speed"] * 3.6),
                        "description": data["weather"][0]["description"].title(),
                        "icon": data["weather"][0]["icon"]
                    }
                else:
                    logger.warning(f"OpenWeather API error: {response.status_code}")
                    return self._get_mock_weather(city_key)

        except Exception as e:
            logger.error(f"Weather API error: {e}")
            return self._get_mock_weather(city_key)

    async def get_forecast(self, city_key: str):
        """Récupérer les prévisions 24h"""
        if city_key not in CITIES:
            raise HTTPException(status_code=404, detail="Ville non trouvée")

        city = CITIES[city_key]

        if self.api_key == "demo_key":
            return self._get_mock_forecast(city_key)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/forecast",
                    params={
                        "lat": city["lat"],
                        "lon": city["lon"],
                        "appid": self.api_key,
                        "units": "metric",
                        "lang": "fr"
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    forecast_24h = []

                    for item in data["list"][:8]:
                        forecast_24h.append({
                            "time": item["dt_txt"],
                            "temp": round(item["main"]["temp"]),
                            "humidity": item["main"]["humidity"],
                            "icon": item["weather"][0]["icon"]
                        })

                    return forecast_24h
                else:
                    logger.warning(f"Forecast API error: {response.status_code}")
                    return self._get_mock_forecast(city_key)

        except Exception as e:
            logger.error(f"Forecast API error: {e}")
            return self._get_mock_forecast(city_key)

    def _get_mock_weather(self, city_key: str):
        """Données météo simulées"""
        base_temps = {
            "paris": 18, "lyon": 16, "marseille": 22, "bordeaux": 19,
            "lille": 14, "toulouse": 20, "nice": 24
        }

        base_temp = base_temps.get(city_key, 18)
        variation = random.randint(-5, 5)
        temp = base_temp + variation

        return {
            "temperature": temp,
            "feels_like": temp + random.randint(-2, 3),
            "humidity": random.randint(45, 85),
            "pressure": random.randint(1005, 1025),
            "visibility": random.randint(8, 20),
            "wind_speed": random.randint(5, 25),
            "description": random.choice(["Ensoleillé", "Partiellement nuageux", "Nuageux", "Ciel dégagé"]),
            "icon": random.choice(["01d", "02d", "03d", "04d"])
        }

    def _get_mock_forecast(self, city_key: str):
        """Prévisions simulées"""
        forecast = []
        base_time = datetime.now()

        for i in range(8):
            time = base_time + timedelta(hours=i * 3)
            temp = random.randint(12, 28)
            forecast.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "temp": temp,
                "humidity": random.randint(40, 80),
                "icon": random.choice(["01d", "02d", "03d", "04d", "01n", "02n"])
            })

        return forecast


class EventsService:
    def __init__(self):
        self.api_key = OPENAGENDA_API_KEY
        self.base_url = "https://api.openagenda.com/v2"

    async def get_city_events(self, city_key: str, limit: int = 10):
        """Récupérer les événements d'une ville via OpenAgenda"""
        if city_key not in CITIES:
            return self._get_fallback_events(city_key)

        if self.api_key == "demo_key":
            return self._get_fallback_events(city_key)

        try:
            city_name = CITIES[city_key]["name"]

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/events",
                    params={
                        "key": self.api_key,
                        "where": city_name,
                        "size": limit,
                        "sort": "updatedAt.desc",
                        "when": "upcoming"
                    },
                    timeout=15.0
                )

                if response.status_code == 200:
                    data = response.json()
                    events = []

                    for event in data.get("events", [])[:limit]:
                        # Traitement des données OpenAgenda
                        event_data = {
                            "name": event.get("title", {}).get("fr", "Événement"),
                            "date": event.get("firstDate", datetime.now().isoformat()),
                            "location": event.get("location", {}).get("name", "Lieu non spécifié"),
                            "category": self._map_category(event.get("categories", [])),
                            "description": event.get("description", {}).get("fr", "")[:200] + "...",
                            "url": event.get("canonicalUrl", ""),
                            "image": event.get("image", "")
                        }
                        events.append(event_data)

                    return {
                        "events": events,
                        "count": len(events),
                        "source": "openagenda"
                    }
                else:
                    logger.warning(f"OpenAgenda API error: {response.status_code}")
                    return self._get_fallback_events(city_key)

        except Exception as e:
            logger.error(f"Events API error: {e}")
            return self._get_fallback_events(city_key)

    def _map_category(self, categories):
        """Mapper les catégories OpenAgenda vers nos catégories"""
        category_mapping = {
            "concert": "concert",
            "spectacle": "culture",
            "exposition": "exposition",
            "sport": "sport",
            "marché": "marché",
            "festival": "culture",
            "conférence": "culture"
        }

        if not categories:
            return "culture"

        for cat in categories:
            cat_lower = cat.lower()
            for key, value in category_mapping.items():
                if key in cat_lower:
                    return value

        return "culture"

    def _get_fallback_events(self, city_key: str):
        """Événements de fallback si API indisponible"""
        events_data = {
            "paris": [
                {"name": "Festival Jazz de Paris", "date": "2026-03-22T19:00:00", "location": "Place de la République",
                 "category": "concert"},
                {"name": "Marché Bio Montmartre", "date": "2026-03-23T09:00:00", "location": "Place du Tertre",
                 "category": "marché"},
                {"name": "Exposition Louvre", "date": "2026-03-24T14:00:00", "location": "Musée du Louvre",
                 "category": "exposition"}
            ],
            "lyon": [
                {"name": "Fête des Lumières", "date": "2026-03-21T20:00:00", "location": "Vieux Lyon",
                 "category": "culture"},
                {"name": "Marché de la Croix-Rousse", "date": "2026-03-24T08:00:00",
                 "location": "Boulevard de la Croix-Rousse", "category": "marché"}
            ],
            "marseille": [
                {"name": "Festival de Marseille", "date": "2026-03-25T18:00:00", "location": "Vieux-Port",
                 "category": "culture"},
                {"name": "Marché aux Poissons", "date": "2026-03-22T06:00:00", "location": "Quai des Belges",
                 "category": "marché"}
            ]
        }

        city_events = events_data.get(city_key, [
            {"name": f"Événement local {city_key.title()}", "date": "2026-03-23T15:00:00", "location": "Centre-ville",
             "category": "culture"}
        ])

        return {
            "events": city_events,
            "count": len(city_events),
            "source": "fallback"
        }


# Instances des services
weather_service = WeatherService()
events_service = EventsService()


# ==========================================
# FONCTIONS UTILITAIRES
# ==========================================

def _simulate_air_quality():
    """Simulation de la qualité de l'air"""
    aqi = random.randint(25, 150)

    if aqi <= 50:
        label, color = "Bon", "green"
        advice = "Parfait pour les activités outdoor"
    elif aqi <= 100:
        label, color = "Modéré", "yellow"
        advice = "Activités outdoor acceptables"
    elif aqi <= 150:
        label, color = "Mauvais", "orange"
        advice = "Limitez les activités outdoor"
    else:
        label, color = "Très mauvais", "red"
        advice = "Évitez les activités outdoor"

    return {
        "aqi": aqi,
        "label": label,
        "color": color,
        "advice": advice,
        "pm25": random.randint(5, 50),
        "no2": random.randint(10, 80),
        "o3": random.randint(20, 120)
    }


def _calculate_urban_score(weather, air_quality):
    """Calcul du score urbain"""
    temp = weather["temperature"]
    if 18 <= temp <= 24:
        weather_score = 100
    elif 15 <= temp <= 27:
        weather_score = 80
    elif 10 <= temp <= 30:
        weather_score = 60
    else:
        weather_score = 40

    aqi = air_quality["aqi"]
    if aqi <= 50:
        air_score = 100
    elif aqi <= 100:
        air_score = 80
    elif aqi <= 150:
        air_score = 60
    else:
        air_score = 40

    events_score = random.randint(60, 90)
    global_score = int(weather_score * 0.4 + air_score * 0.4 + events_score * 0.2)

    if global_score >= 80:
        label = "Excellent"
    elif global_score >= 65:
        label = "Bon"
    elif global_score >= 50:
        label = "Moyen"
    else:
        label = "Mauvais"

    return {
        "score": global_score,
        "label": label,
        "breakdown": {
            "weather": {"score": weather_score, "weight": 0.4},
            "air_quality": {"score": air_score, "weight": 0.4},
            "events": {"score": events_score, "weight": 0.2}
        }
    }


def _simulate_ai_prediction():
    """Prédictions IA simulées"""
    current_aqi = random.randint(30, 120)
    predicted_aqi = current_aqi + random.randint(-15, 15)

    forecast = []
    for i in range(1, 7):
        aqi = predicted_aqi + random.randint(-10, 10)
        forecast.append({
            "hour": f"+{i}h",
            "aqi": max(10, min(300, aqi))
        })

    return {
        "predicted_aqi_6h": predicted_aqi,
        "confidence": random.randint(75, 95),
        "forecast": forecast
    }


# ==========================================
# ENDPOINTS API
# ==========================================

@app.get("/api/dashboard/{city}")
async def get_dashboard_data(city: str):
    """Endpoint principal pour toutes les données du dashboard"""
    try:
        # Récupération parallèle des données
        current_weather = await weather_service.get_current_weather(city)
        forecast_24h = await weather_service.get_forecast(city)
        events_data = await events_service.get_city_events(city)

        # Simulation des autres données
        air_quality = _simulate_air_quality()
        urban_score = _calculate_urban_score(current_weather, air_quality)
        prediction = _simulate_ai_prediction()

        # ========== INTÉGRATION ML DANS LE DASHBOARD ==========
        ml_predictions = None
        if city.upper() in VILLES:
            try:
                ml_predictions = predire_6h(city.upper())
                logger.info(f"ML predictions loaded for {city}")
            except Exception as e:
                logger.warning(f"ML prediction failed for {city}: {e}")

        return {
            "city": CITIES.get(city, {}).get("name", city.title()),
            "weather": {
                "current": current_weather,
                "forecast_24h": forecast_24h
            },
            "air": air_quality,
            "score": urban_score,
            "events": events_data,
            "prediction": prediction,
            "ml_predictions": ml_predictions,  # ← NOUVEAU
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Dashboard error for {city}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données: {str(e)}")


@app.get("/api/cities")
async def get_cities():
    """Liste des villes disponibles"""
    return {
        "cities": [{"key": key, "name": city["name"]} for key, city in CITIES.items()],
        "count": len(CITIES)
    }


@app.get("/api/weather/{city}")
async def get_weather(city: str):
    """Météo actuelle pour une ville"""
    current = await weather_service.get_current_weather(city)
    forecast = await weather_service.get_forecast(city)

    return {
        "city": CITIES.get(city, {}).get("name", city.title()),
        "current": current,
        "forecast_24h": forecast
    }


@app.get("/api/events/{city}")
async def get_events(city: str):
    """Événements d'une ville"""
    events = await events_service.get_city_events(city)
    return {
        "city": CITIES.get(city, {}).get("name", city.title()),
        **events
    }


@app.get("/api/events")
async def get_all_events():
    """Tous les événements de toutes les villes"""
    all_events = {}
    for city_key in CITIES.keys():
        events = await events_service.get_city_events(city_key, limit=5)
        all_events[city_key] = events

    return {
        "cities": all_events,
        "total_cities": len(CITIES)
    }


# ========== NOUVEL ENDPOINT ML ==========
@app.get("/api/predict/temperature/{city}")
async def predict_temperature(city: str):
    """Prédictions de température ML pour les 6 prochaines heures"""
    try:
        # Vérifier si la ville est supportée par le modèle ML
        if city.upper() not in VILLES:
            available_cities = ", ".join(VILLES)
            raise HTTPException(
                status_code=404,
                detail=f"Ville '{city}' non supportée par le modèle ML. Villes disponibles: {available_cities}"
            )

        # Appeler la fonction de prédiction ML
        predictions = predire_6h(city.upper())

        return {
            "city": city.title(),
            "predictions": predictions,
            "model": "XGBoost",
            "timestamp": datetime.now().isoformat(),
            "source": "ml_model"
        }

    except Exception as e:
        logger.error(f"ML prediction error for {city}: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de prédiction ML: {str(e)}")


# ==========================================
# ROUTES STATIQUES ET HTML
# ==========================================

# Servir les fichiers statiques
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/js/main.js")
async def get_main_js():
    """Servir le fichier JavaScript principal"""
    try:
        with open("static/js/main.js", "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content, media_type="application/javascript")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="main.js non trouvé")


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Page d'accueil du dashboard"""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Weather Dashboard</title></head>
            <body>
                <h1>Weather Dashboard</h1>
                <p>Fichier index.html non trouvé. Veuillez l'ajouter à la racine du projet.</p>
                <p><a href="/api/dashboard/paris">Test API Paris</a></p>
            </body>
        </html>
        """)


@app.get("/health")
async def health_check():
    """Endpoint de santé"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "weather": "active",
            "events": "active",
            "ml": "active" if VILLES else "inactive"  # ← NOUVEAU
        }
    }


# ==========================================
# DÉMARRAGE DE L'APPLICATION
# ==========================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
