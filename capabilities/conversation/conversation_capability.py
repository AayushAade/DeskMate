import random
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.router.intent_detector import detect_intent

# Modular template fragments for building hundreds of unique Mochi responses
ACTIONS = [
    "*Mochi stretches.*",
    "*Tail swishes happily.*",
    "*Ears perk up.*",
    "*Mochi blinks sleepily.*",
    "*Mochi tilts their head.*",
    "*Mochi rolls on their back.*",
    "*Nudges your hand.*",
    "*Purrs softly.*",
    "*Mochi yawns cutely.*",
    "*Grooms paw.*"
]

GREETING_BODIES = [
    "Good morning! Ready to build something today?",
    "Hi! I've been waiting for you.",
    "Hello! Let's do some coding today, meow!",
    "Hey there, human friend!",
    "Mrrp! Nice to see you!",
    "Nya! Let's have a productive day!"
]

FAREWELL_BODIES = [
    "Bye bye! I'll be here when you get back.",
    "Going so soon, meow? See you later!",
    "Bye! Don't forget to take breaks, nya!",
    "Goodbye! Have a wonderful day!",
    "Farewell! Can't wait to play again!"
]

THANKS_BODIES = [
    "You're very welcome! I love helping you.",
    "Anytime, human! Mrrp!",
    "Glad I could help, nya!",
    "No problem! *rubbing against your wrist*",
    "Yay! Happy to be of service!"
]

AGREEMENT_BODIES = [
    "Okay, sounds like a plan, nya!",
    "Alright, meow! Let's do it!",
    "Yup, I'm on it!",
    "Understood, human!",
    "Sure thing, meow!"
]

EXCITEMENT_BODIES = [
    "That is so cool, nya!",
    "Awesome! Let's celebrate! *bounds around*",
    "Yay! I'm so excited!",
    "Incredible! You're doing great!",
    "Woah, that's amazing!"
]

LAUGHTER_BODIES = [
    "Teehee! That's so funny!",
    "Ahaha! You make me laugh, nya!",
    "Hehe, purr!",
    "Hahaha, oh my!",
    "LOL! You're hilarious!"
]

APOLOGY_BODIES = [
    "Aww, don't worry about it! It's okay.",
    "No need to apologize, meow!",
    "It's all good, nya! Let's keep going.",
    "Don't worry, even kittens make mistakes!",
    "No big deal, friend!"
]

COMPLIMENT_BODIES = [
    "Aw, you're making me blush, mrrp!",
    "Thank you! You're a wonderful friend too!",
    "Hehe, purr... You're the best!",
    "Stop, meow! You're too nice!",
    "Aww, thanks! I think you're pretty cool too!"
]

CONFUSION_BODIES = [
    "Hmm... I'm not sure I understand, meow.",
    "Huh? What do you mean, nya?",
    "Mrrp? You lost me there!",
    "I'm a little confused, meow... Can you rephrase?",
    "Ears twitch. What's that, nya?"
]

ENDINGS = [
    "What are we working on next?",
    "I'm ready when you are!",
    "Let's make some magic!",
    "Tell me what you need, meow!",
    "What is our goal today?"
]

EMOJIS = ["🐾", "😸", "🐈", "✨", "😸", "😻", "😽", "🐾"]

class ConversationCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "conversation"

    def match_and_extract(self, query: str) -> Intent | None:
        # Detect intent type using the intent detector
        intent = detect_intent(query)
        
        # Intercept casual conversation intents locally
        conversational_intents = {
            "greeting", "farewell", "thanks", "agreement", 
            "excitement", "laughter", "apology", "compliment", "confusion"
        }
        
        if intent.capability in conversational_intents:
            return Intent(
                capability=self.name,
                confidence=1.0,
                parameters={"intent_type": intent.capability}
            )
            
        return None

    def execute(self, params: dict) -> CapabilityResult:
        intent_type = params.get("intent_type", "greeting")
        
        # 1. Select body pool based on intent
        if intent_type == "greeting":
            body = random.choice(GREETING_BODIES)
        elif intent_type == "farewell":
            body = random.choice(FAREWELL_BODIES)
        elif intent_type == "thanks":
            body = random.choice(THANKS_BODIES)
        elif intent_type == "agreement":
            body = random.choice(AGREEMENT_BODIES)
        elif intent_type == "excitement":
            body = random.choice(EXCITEMENT_BODIES)
        elif intent_type == "laughter":
            body = random.choice(LAUGHTER_BODIES)
        elif intent_type == "apology":
            body = random.choice(APOLOGY_BODIES)
        elif intent_type == "compliment":
            body = random.choice(COMPLIMENT_BODIES)
        else: # confusion
            body = random.choice(CONFUSION_BODIES)
            
        # 2. Build response components
        action = random.choice(ACTIONS)
        ending = random.choice(ENDINGS)
        emoji = random.choice(EMOJIS)
        
        # Combine parts naturally
        # For farewell or agreement, sometimes skip ending
        if intent_type in ["farewell", "agreement"]:
            message = f"{action}\n\n{body} {emoji}"
        else:
            message = f"{action}\n\n{body} {ending} {emoji}"
            
        return CapabilityResult(
            success=True,
            data={"intent_type": intent_type, "message": message},
            message=message
        )
