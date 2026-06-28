import re
import urllib.request
import urllib.parse
import json
import subprocess
from datetime import datetime

class Tool:
    @property
    def name(self) -> str:
        raise NotImplementedError
        
    @property
    def description(self) -> str:
        raise NotImplementedError
        
    def can_handle(self, query: str) -> bool:
        raise NotImplementedError
        
    def execute(self, query: str) -> str:
        raise NotImplementedError


class DateTimeTool(Tool):
    @property
    def name(self) -> str:
        return "Current Date & Time Tool"
        
    @property
    def description(self) -> str:
        return "Tells the current date, time, and timezone information."
        
    def can_handle(self, query: str) -> bool:
        q = query.lower()
        return any(word in q for word in ["time", "date", "clock", "what day", "what today", "what's the time"])

    def execute(self, query: str) -> str:
        now = datetime.now()
        return (
            f"Current Date and Time details:\n"
            f"- Date: {now.strftime('%A, %B %d, %Y')}\n"
            f"- Time: {now.strftime('%I:%M:%S %p')}\n"
            f"- Timezone: {now.astimezone().tzname()}"
        )


class CalculatorTool(Tool):
    @property
    def name(self) -> str:
        return "Calculator Tool"
        
    @property
    def description(self) -> str:
        return "Evaluates basic mathematical expressions (addition, subtraction, multiplication, division, exponentiation)."
        
    def can_handle(self, query: str) -> bool:
        q = query.lower()
        if any(keyword in q for keyword in ["calculate", "what is", "what's", "math", "evaluate"]):
            # Confirm if there are some digits or math symbols
            return any(c.isdigit() for c in q) or any(c in "+-*/^()%" for c in q)
        # Fallback check: query has at least one digit and one operator
        has_digit = any(c.isdigit() for c in query)
        has_operator = any(c in "+-*/%^()" for c in query)
        return has_digit and has_operator

    def execute(self, query: str) -> str:
        sanitized = query.lower()
        prefixes = ["what is", "calculate", "what's", "math", "evaluate"]
        for prefix in prefixes:
            sanitized = sanitized.replace(prefix, "")
            
        # Clean query: only allow numbers, math operators, decimals, spaces
        expression = "".join(c for c in sanitized if c in "0123456789+-*/%().^ \t")
        expression = expression.replace("^", "**").strip()
        
        if not expression or not any(c.isdigit() for c in expression):
            return "Invalid math expression."
            
        try:
            # Safe eval execution with restricted builtins
            result = eval(expression, {"__builtins__": None}, {})
            return f"Expression: {expression}\nResult: {result}"
        except Exception as e:
            return f"Failed to evaluate expression '{expression}': {e}"


class OpenAppTool(Tool):
    @property
    def name(self) -> str:
        return "Open Application Tool"
        
    @property
    def description(self) -> str:
        return "Launches system applications (VS Code, Chrome, Spotify, Terminal, Finder, Safari, etc.) on macOS."
        
    def can_handle(self, query: str) -> bool:
        q = query.lower()
        return any(q.startswith(prefix) for prefix in ["open ", "launch "])

    def execute(self, query: str) -> str:
        app_name = query.lower()
        if app_name.startswith("open "):
            app_name = app_name[5:].strip()
        elif app_name.startswith("launch "):
            app_name = app_name[7:].strip()
            
        # Map common input names to macOS Application names
        app_map = {
            "vs code": "Visual Studio Code",
            "vscode": "Visual Studio Code",
            "visual studio code": "Visual Studio Code",
            "chrome": "Google Chrome",
            "google chrome": "Google Chrome",
            "terminal": "Terminal",
            "spotify": "Spotify",
            "finder": "Finder",
            "safari": "Safari",
            "slack": "Slack",
            "zoom": "zoom.us",
            "discord": "Discord",
            "calculator": "Calculator",
            "textedit": "TextEdit",
            "app store": "App Store"
        }
        
        mac_app_name = app_map.get(app_name)
        if not mac_app_name:
            mac_app_name = app_name.title()
            
        try:
            # Run 'open -a AppName' on macOS
            subprocess.Popen(["open", "-a", mac_app_name])
            return f"Successfully launched application: '{mac_app_name}'."
        except Exception as e:
            return f"Failed to open application '{mac_app_name}': {e}"


class WeatherTool(Tool):
    @property
    def name(self) -> str:
        return "Weather Tool"
        
    @property
    def description(self) -> str:
        return "Retrieves the current weather (temperature, conditions, wind, humidity) for any city or the user's geolocated IP location."
        
    def can_handle(self, query: str) -> bool:
        q = query.lower()
        return any(word in q for word in ["weather", "temperature", "forecast", "rain", "snow", "temp", "humidity", "wind", "degrees"])

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

    def execute(self, query: str) -> str:
        # Heuristically extract city name after 'in', 'for', or 'at'
        match = re.search(r'\b(?:in|for|at)\s+([A-Za-z\s\-]+)', query, re.IGNORECASE)
        city = match.group(1).strip() if match else None
        
        lat, lon = None, None
        
        # 1. Fallback to IP geolocation if no location is mentioned
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
                print(f"[WeatherTool] Geolocation fallback lookup failed: {e}")
                
        # 2. Geocode city if location coordinates are not resolved yet
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
                        return f"Could not find coordinates for city: '{city}'"
            except Exception as e:
                return f"Geocoding error for '{city}': {e}"
                
        if lat is None or lon is None:
            return "Could not determine location coordinates. Please state a city name clearly."
            
        # 3. Retrieve weather data from Open-Meteo
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
                wind = current.get("wind_speed_10m")
                code = current.get("weather_code", 0)
                condition = self.decode_weather_code(code)
                
                return (
                    f"Weather for {city} (Lat: {lat}, Lon: {lon}):\n"
                    f"- Temperature: {temp}°C (Apparent: {apparent}°C)\n"
                    f"- Condition: {condition}\n"
                    f"- Humidity: {humidity}%\n"
                    f"- Precipitation: {precip} mm\n"
                    f"- Wind Speed: {wind} km/h"
                )
        except Exception as e:
            return f"Failed to get weather data for {city}: {e}"


class WebSearchTool(Tool):
    @property
    def name(self) -> str:
        return "Web Search Tool"
        
    @property
    def description(self) -> str:
        return "Searches the web for latest news and topics using DuckDuckGo."
        
    def can_handle(self, query: str) -> bool:
        q = query.lower()
        return any(word in q for word in ["search", "google", "web search", "duckduckgo", "latest news", "news about", "find info on"])

    def execute(self, query: str) -> str:
        search_query = query.lower()
        strip_phrases = [
            "search the web for", "web search for", "search for", 
            "google search", "duckduckgo search", "search", 
            "find info on", "find information on"
        ]
        for phrase in strip_phrases:
            search_query = search_query.replace(phrase, "")
        search_query = search_query.strip()
        
        if not search_query:
            search_query = query.strip()
            
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=3))
                if not results:
                    return f"No search results found for '{search_query}'."
                
                summary = []
                for idx, r in enumerate(results, 1):
                    title = r.get("title", "No Title")
                    href = r.get("href", "")
                    body = r.get("body", "")
                    summary.append(f"{idx}. {title}\n   Snippet: {body}\n   Source: {href}")
                
                return f"Web Search results for '{search_query}':\n\n" + "\n\n".join(summary)
        except Exception as e:
            return f"Web search failed: {e}"


class ToolManager:
    def __init__(self):
        # Register tools in order of priority checking
        self.tools = [
            DateTimeTool(),
            CalculatorTool(),
            OpenAppTool(),
            WeatherTool(),
            WebSearchTool()
        ]
        
    def get_tool_context(self, query: str) -> str:
        cleaned_query = query.strip()
        for tool in self.tools:
            if tool.can_handle(cleaned_query):
                print(f"[ToolManager] Query '{cleaned_query}' matched tool: '{tool.name}'")
                result = tool.execute(cleaned_query)
                context = (
                    f"Result from executed tool ({tool.name}):\n"
                    f"\"\"\"\n{result}\n\"\"\""
                )
                return context
        return None
