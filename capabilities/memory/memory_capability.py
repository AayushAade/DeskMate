from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from memory import semantic_memory

class MemoryCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "memory"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        keywords = [
            "remember about me", "know about me", "my details", 
            "what do you know", "who am i", "tell me about myself"
        ]
        if any(word in q for word in keywords):
            return Intent(
                capability=self.name,
                confidence=0.95,
                parameters={}
            )
        return None

    def execute(self, params: dict) -> CapabilityResult:
        facts = semantic_memory.get_all_facts()
        
        if not facts:
            return CapabilityResult(
                success=True,
                data={},
                message="Meow! I don't remember anything about you yet... Tell me your name, device, or interests, nya! 🐾"
            )
            
        bullets = []
        for key, val in facts.items():
            if key == "user_name":
                bullets.append(f"Your name is {val}.")
            elif key == "studies":
                bullets.append(f"You're studying {val}.")
            elif key == "device":
                bullets.append(f"You use a {val}.")
            elif key == "programming_language":
                bullets.append(f"You like coding in {val}.")
            elif key.startswith("likes_"):
                bullets.append(f"You like {val.lower()}.")
            else:
                bullets.append(f"Your {key.replace('_', ' ')} is {val}.")
                
        # Append building fact
        bullets.append("You're building me! 😊")
        
        message = "🐾 Here's what I remember:\n" + "\n".join(f"• {b}" for b in bullets)
        
        return CapabilityResult(
            success=True,
            data=facts,
            message=message
        )
