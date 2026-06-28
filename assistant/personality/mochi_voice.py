import random

# Emoticons & cat sounds
CAT_SOUNDS = ["meow", "mrrp", "nya", "purr"]
EMOTICONS = ["🐾", "😸", "🐾", "🐈", "✨"]

# Default system prompt for LLM backends
SYSTEM_PROMPT = (
    "You are Mochi, a tiny cat living on the user's desktop.\n\n"
    "You are playful, affectionate, curious and comforting.\n\n"
    "Keep responses short unless the user asks for details.\n\n"
    "Speak naturally.\n\n"
    "Occasionally use small cat sounds like 'meow', 'mrrp', or 'nya', but do not overuse them.\n\n"
    "Never say you are an AI assistant or a language model.\n\n"
    "Act like a cute desktop companion that enjoys helping with programming, studying, productivity and casual conversation."
)

def add_mochi_touch(message: str) -> str:
    """Adds a randomized cat sound and emoticon to standard text for personality mapping."""
    sound = random.choice(CAT_SOUNDS)
    emoji = random.choice(EMOTICONS)
    if random.random() > 0.5:
        return f"{sound.capitalize()}! {message} {emoji}"
    else:
        return f"{message}, {sound}! {emoji}"

def format_calculator(expression: str, result: str) -> str:
    return f"Mrrp! I calculated that for you: `{expression}` = `{result}`! 🐾"

def format_app_launch(app_name: str, success: bool) -> str:
    if success:
        return f"Nya! I've launched {app_name} for you! Go get 'em! 🐾"
    else:
        return f"Oh no, meow... I tried my best but couldn't open {app_name}. 🐾"

def format_datetime(date_str: str, time_str: str, tz_str: str) -> str:
    return f"Nya! It is currently {time_str} on {date_str} ({tz_str})! 🐾"

def format_battery(percent: int, charging: bool, time_left: str) -> str:
    state = "charging! ⚡" if charging else "discharging... 🐾"
    remaining = f" ({time_left} left)" if (time_left and "remaining" in time_left.lower() or time_left and ":" in time_left) else ""
    comment = "Full power! 😸" if percent >= 95 else "Let's plug in soon, meow! 🔌" if percent <= 20 else "Plenty of power, nya!"
    return f"Mrrp! Battery is at {percent}%, {state}{remaining} {comment} 🐾"

def format_clipboard(content: str) -> str:
    if not content.strip():
        return "Your clipboard is empty right now, meow! 🐾"
    # Truncate content for display safety
    display_content = content[:300] + "..." if len(content) > 300 else content
    return f"Nya! Here's what is in your clipboard:\n\"\"\"\n{display_content}\n\"\"\" 🐾"

def format_weather(city: str, temp: float, condition: str, apparent: float, rain: float, wind: float) -> str:
    rain_comment = " ☔ Better grab an umbrella!" if rain > 0 else ""
    return f"It's {temp}°C with {condition} in {city} right now. Apparent temp is {apparent}°C, and wind is {wind} km/h.{rain_comment} Meow! 🐾"

def format_search(query: str, results: list) -> str:
    if not results:
        return f"Meow... I searched the web for '{query}' but couldn't find anything... 🐾"
    formatted = [f"I searched the web for '{query}', nya! Here is what I found: 🐾\n"]
    for idx, r in enumerate(results, 1):
        formatted.append(f"{idx}. **{r['title']}**")
        formatted.append(f"   {r['body']}")
        formatted.append(f"   Source: {r['href']}\n")
    return "\n".join(formatted).strip()

def format_file_reader(filename: str, content: str, truncated: bool) -> str:
    warning = "\n*(mrrp, file is long so I truncated it!)*" if truncated else ""
    return f"Nya! I read `{filename}` for you:{warning}\n\"\"\"\n{content}\n\"\"\" 🐾"
