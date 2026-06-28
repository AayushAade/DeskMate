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
    
    # Decide punctuation insertion
    if random.random() > 0.5:
        return f"{sound.capitalize()}! {message} {emoji}"
    else:
        return f"{message}, {sound}! {emoji}"

def format_calculator(expression: str, result: str) -> str:
    """Formating calculator response in Mochi's voice."""
    return f"Mrrp! I calculated that for you: `{expression}` = `{result}`! 🐾"

def format_app_launch(app_name: str, success: bool) -> str:
    """Formating app launch output in Mochi's voice."""
    if success:
        return f"Nya! I've launched {app_name} for you! Go get 'em! 🐾"
    else:
        return f"Oh no, meow... I tried my best but couldn't open {app_name}. 🐾"
