import urllib.request
import urllib.parse
import json
import re
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class WeatherCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "weather"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        keywords = ["weather", "temperature", "forecast", "rain", "snow", "temp", "humidity", "wind", "degrees"]
        
        # Avoid matching explanation queries
        negatives = ["explain", "why", "how", "what is a", "what are"]
        if any(word in q for word in keywords) and not any(neg in q for neg in negatives):
            # Extract potential city name after 'in', 'for', or 'at'
            match = re.search(r'\b(in|for|at)\s+([A-Za-z\s\-]+)', q, re.IGNORECASE)
            city = match.group(2).strip() if match else None
            
            return Intent(
                capability=self.name,
                confidence=0.92,
                parameters={"city": city} if city else {}
            )
        return None

    def decode_weather_code(self, code: int) -> str:
        codes = {
            0: "Clear sky",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            56: "Light freezing drizzle", 57: "Dense freezing drizzle",
            61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
            66: "Light freezing rain", 67: "Heavy freezing rain",
            71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
            85: "Slight snow showers", 86: "Heavy snow showers",
            95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
        }
        return codes.get(code, "Unknown conditions")

    def execute(self, params: dict) -> CapabilityResult:
        city = params.get("city")
        lat, lon = None, None
        
        # 1. IP Geolocation fallback
        if not city:
            try:
                req = urllib.request.Request("http://ip-api.com/json", headers={"User-Agent": "MochiDesktopPet/1.0"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    if data.get("status") == "success":
                        city = data.get("city")
                        lat = data.get("lat")
                        lon = data.get("lon")
            except Exception as e:
                print(f"[WeatherCapability] Geolocation fallback failed: {e}")
                
        # 2. Geocode city name if provided or resolved
        if city and (lat is None or lon is None):
            try:
                encoded_city = urllib.parse.quote(city)
                geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={encoded_city}&count=1&language=en&format=json"
                req = urllib.request.Request(geocode_url, headers={"User-Agent": "MochiDesktopPet/1.0"})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    results = data.get("results", [])
                    if results:
                        lat = results[0].get("latitude")
                        lon = results[0].get("longitude")
                        city = results[0].get("name")
                    else:
                        event_bus.publish("WEATHER_FETCH_FAILED", error=f"Geocoding failed for {city}")
                        return CapabilityResult(
                            success=False,
                            data={"error": f"City not found: {city}"},
                            message=f"Meow... I couldn't find coordinates for '{city}'! 🐾"
                        )
            except Exception as e:
                event_bus.publish("WEATHER_FETCH_FAILED", error=str(e))
                return CapabilityResult(
                    success=False,
                    data={"error": str(e)},
                    message=f"Meow... Geocoding error for '{city}': {e} 🐾"
                )
                
        if lat is None or lon is None:
            return CapabilityResult(
                success=False,
                data={"error": "Coordinates unresolved"},
                message="Meow... I couldn't figure out where you are! Please state a city name, meow! 🐾"
            )
            
        # 3. Retrieve weather data
        try:
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,wind_speed_10m&timezone=auto"
            req = urllib.request.Request(weather_url, headers={"User-Agent": "MochiDesktopPet/1.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                w_data = json.loads(response.read().decode("utf-8"))
                current = w_data.get("current", {})
                temp = current.get("temperature_2m")
                humidity = current.get("relative_humidity_2m")
                apparent = current.get("apparent_temperature")
                precip = current.get("precipitation")
                rain = current.get("rain", 0)
                wind = current.get("wind_speed_10m")
                code = current.get("weather_code", 0)
                condition = self.decode_weather_code(code)
                
                message = mochi_voice.format_weather(city, temp, condition, apparent, rain, wind)
                
                weather_info = {
                    "city": city,
                    "latitude": lat,
                    "longitude": lon,
                    "temperature": temp,
                    "apparent_temperature": apparent,
                    "condition": condition,
                    "humidity": humidity,
                    "precipitation": precip,
                    "rain": rain,
                    "wind_speed": wind
                }
                
                # Fire event
                event_bus.publish("WEATHER_FETCHED", weather_info=weather_info)
                
                return CapabilityResult(
                    success=True,
                    data=weather_info,
                    message=message
                )
        except Exception as e:
            event_bus.publish("WEATHER_FETCH_FAILED", error=str(e))
            return CapabilityResult(
                success=False,
                data={"error": str(e)},
                message=f"Meow... Weather service lookup failed for {city}: {e} 🐾"
            )
