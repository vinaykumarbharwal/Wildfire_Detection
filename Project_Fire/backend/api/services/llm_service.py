import logging
import aiohttp
from api.config.settings import settings

logger = logging.getLogger(__name__)

# Groq REST API — OpenAI-compatible, ultra-fast, free tier
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # Current fast free model (replaces decommissioned llama3-8b-8192)



async def generate_tactical_report(detection_data: dict) -> str:
    """
    Calls Groq (LLaMA 3 via REST API) to generate a wildfire tactical
    assessment from the detection's location, severity, and weather data.
    """
    api_key = settings.GROQ_API_KEY or settings.GEMINI_API_KEY  # fallback support

    if not api_key:
        return "⚠️ AI Incident Reporting is unavailable: No AI API key configured in `.env`."

    # Use Groq if GROQ_API_KEY is set, else fall back to Gemini REST
    if settings.GROQ_API_KEY:
        return await _groq_generate(detection_data)
    else:
        return await _gemini_generate(detection_data)


def _build_prompt(detection_data: dict) -> str:
    weather = detection_data.get("weather_snapshot") or {}
    weather_text = (
        f"Temp: {weather.get('temperature_celsius', 'N/A')}°C | "
        f"Wind Speed: {weather.get('wind_speed_kmh', 'N/A')} km/h | "
        f"Wind Direction: {weather.get('wind_direction_degrees', 'N/A')}° | "
        f"Humidity: {weather.get('humidity_percent', 'N/A')}%"
    ) if weather else "No live weather metrics available."

    stations = detection_data.get("nearby_stations", [])
    stations_text = "\n".join([
        f"- {s.get('name')} ({s.get('distance')} km away)" 
        for s in stations[:3]
    ]) if stations else "- No responders within 50km radius."

    return f"""### LIVE INCIDENT INTEL - AGNIVEER COMMAND HUB ###
You are an Elite Wildfire Tactical AI. Analyze the following data and issue a strategic directive.

INCIDENT PARAMETERS:
- **Location:** {detection_data.get('address', 'Remote Grid')} (Lat: {detection_data.get('latitude')}, Lng: {detection_data.get('longitude')})
- **Severity/Confidence:** {detection_data.get('severity', 'Pending Analysis')} / {round((detection_data.get('confidence') or 0) * 100)}%
- **Environmental Context:** {weather_text}
- **Responder Proximity:**
{stations_text}

Provide an "Elite Tactical Assessment" (max 150 words). Focus on:
1. **Threat Assessment:** Immediate danger to life/property.
2. **Spread Vector:** Predict fire path based on wind direction ({weather.get('wind_direction_degrees', 'N/A')}°).
3. **Strategic Directives:** Specific instructions for the nearest stations (e.g., specific containment lines, drone deployment, or evacuation triggers).

Use a professional, authoritative, military-style tone. 
FORMAT:
**⚡ AGNIVEER TACTICAL DIRECTIVE**
- **THREAT ANALYSIS:** [Analysis]
- **ENVIRONMENTAL IMPACT:** [Weather risk]
- **OPERATIONAL ORDERS:** [Directives]"""


async def _groq_generate(detection_data: dict) -> str:
    """Generate report using Groq (LLaMA 3) — ultra-fast, free."""
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a wildfire tactical analyst. Be concise, professional, and prioritize safety."
            },
            {
                "role": "user",
                "content": _build_prompt(detection_data)
            }
        ],
        "temperature": 0.4,
        "max_tokens": 300,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                GROQ_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    error_text = await resp.text()
                    logger.error("Groq API error %s: %s", resp.status, error_text)
                    return f"⚠️ Groq error ({resp.status}): {error_text[:200]}"
    except Exception as e:
        logger.error("Error calling Groq API: %s", e)
        return f"⚠️ AI generation failed: {e}"


async def _gemini_generate(detection_data: dict) -> str:
    """Fallback: Generate report using Gemini REST API v1."""
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent"
    payload = {
        "contents": [{"parts": [{"text": _build_prompt(detection_data)}]}],
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300}
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                params={"key": settings.GEMINI_API_KEY},
                timeout=aiohttp.ClientTimeout(total=15)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0]["content"]["parts"][0]["text"]
                    return "⚠️ Gemini returned no candidates."
                else:
                    error_text = await resp.text()
                    logger.error("Gemini API error %s: %s", resp.status, error_text)
                    return f"⚠️ Gemini error ({resp.status}): {error_text[:200]}"
    except Exception as e:
        logger.error("Error calling Gemini API: %s", e)
        return f"⚠️ AI generation failed: {e}"
