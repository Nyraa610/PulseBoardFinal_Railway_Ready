import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import httpx

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Weather Dashboard API",
    description="Dashboard météo avec OpenWeatherMap",
    version="1.0.0"
)

# 🔑 Clé API (à mettre dans Railway Variables)
API_KEY = os.getenv("OPENWEATHER_API_KEY")

if not API_KEY:
    logger.warning("⚠️ OPENWEATHER_API_KEY not set!")

BASE_URL = "https://api.openweathermap.org/data/2.5"

# 🌤️ Endpoint météo par ville
@app.get("/weather")
async def get_weather(city: str):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    url = f"{BASE_URL}/weather"

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "fr"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Ville non trouvée")

    data = response.json()

    return {
        "city": data["name"],
        "temperature": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "weather": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"]
    }

# 📅 Prévisions (5 jours)
@app.get("/forecast")
async def get_forecast(city: str):
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key not configured")

    url = f"{BASE_URL}/forecast"

    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric",
        "lang": "fr"
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Erreur prévisions")

    data = response.json()

    forecast_list = []

    for item in data["list"][:8]:  # prochaines 24h (8 x 3h)
        forecast_list.append({
            "datetime": item["dt_txt"],
            "temp": item["main"]["temp"],
            "weather": item["weather"][0]["description"]
        })

    return {
        "city": data["city"]["name"],
        "forecast": forecast_list
    }

# ❤️ Health check
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "api_key_configured": API_KEY is not None
    }

# 📄 Frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

# 🚀 Lancement
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
