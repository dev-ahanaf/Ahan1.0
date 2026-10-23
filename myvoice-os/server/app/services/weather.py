"""Open-Meteo weather service integration."""
import sys
import httpx

def condition(code: int) -> str:
    """Map WMO weather code to descriptive condition string."""
    if code == 0:
        return "clear skies"
    if code in (1, 2, 3):
        return "partly cloudy"
    if code in (45, 48):
        return "foggy"
    if 51 <= code <= 67:
        return "rain or drizzle"
    if 71 <= code <= 77:
        return "snowy"
    if 80 <= code <= 82:
        return "rain showers"
    if code in (95, 96, 99):
        return "thunderstorms"
    return "variable conditions"

async def fetch_weather(*args, **kwargs) -> dict:
    """Fetch live weather metrics from Open-Meteo forecast API."""
    backend = sys.modules.get("app")
    if backend and hasattr(backend, "fetch_weather") and backend.fetch_weather is not fetch_weather:
        return await backend.fetch_weather(*args, **kwargs)
        
    if len(args) == 1:
        row = args[0]
        lat = row["latitude"] if isinstance(row, dict) else row.latitude
        lon = row["longitude"] if isinstance(row, dict) else row.longitude
        city = row["city"] if isinstance(row, dict) else row.city
    elif len(args) >= 3:
        lat, lon, city = args[0], args[1], args[2]
    else:
        lat = kwargs.get("latitude", 23.8103)
        lon = kwargs.get("longitude", 90.4125)
        city = kwargs.get("city", "Dhaka")
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,weather_code,wind_speed_10m"
    }
    async with httpx.AsyncClient(timeout=12) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        d = r.json()["current"]
    return {
        "city": city,
        "temperature_c": d["temperature_2m"],
        "conditions": condition(int(d["weather_code"])),
        "wind_kmh": d["wind_speed_10m"],
        "weather_code": int(d["weather_code"])
    }
