import logging
import aiohttp

logger = logging.getLogger(__name__)

async def get_current_weather(latitude: float, longitude: float) -> dict:
    """
    Fetches real-time weather data (temperature, wind speed, wind direction, humidity)
    from Open-Meteo, which helps in predicting wildfire spread.
    No API key required!
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true&hourly=relativehumidity_2m"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    current = data.get("current_weather", {})
                    # Get humidity from the first hourly reading as a close approximation
                    hourly = data.get("hourly", {})
                    humidities = hourly.get("relativehumidity_2m", [])
                    humidity = humidities[0] if humidities else None

                    return {
                        "temperature_celsius": current.get("temperature"),
                        "wind_speed_kmh": current.get("windspeed"),
                        "wind_direction_degrees": current.get("winddirection"),
                        "humidity_percent": humidity
                    }
                else:
                    logger.warning(f"Failed to fetch weather data: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return {}
