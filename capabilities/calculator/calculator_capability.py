import re
import math
from capabilities.base_capability import BaseCapability, Intent, CapabilityResult
from assistant.personality import mochi_voice
from events import event_bus

class CalculatorCapability(BaseCapability):
    @property
    def name(self) -> str:
        return "calculator"

    def match_and_extract(self, query: str) -> Intent | None:
        q = query.lower().strip()
        
        # Keywords suggesting calculation
        prefixes = ["calculate", "what is", "what's", "math", "evaluate"]
        matched = False
        expression = q
        
        for prefix in prefixes:
            if q.startswith(prefix):
                matched = True
                expression = q[len(prefix):].strip()
                break
                
        # Fallback check: query has at least one digit and one operator
        if not matched:
            has_digit = any(c.isdigit() for c in q)
            has_operator = any(c in "+-*/%^()" for c in q)
            if has_digit and has_operator:
                matched = True
                
        if matched:
            # Clean expression from general punctuation/words if it was prefixed
            expression = expression.replace("?", "").strip()
            
            # Robust check: if any non-math alphabetical letters are in the expression, reject it.
            # Allowed math functions/constants:
            math_words = ["sin", "cos", "tan", "sqrt", "pi", "log", "exp", "abs", "e"]
            test_expr = expression
            for word in math_words:
                test_expr = re.sub(r'\b' + word + r'\b', '', test_expr)
            # Remove all non-alphabet characters
            letters_only = re.sub(r'[^a-z]', '', test_expr)
            if letters_only:
                # Contains non-math letters, reject match
                return None
                
            return Intent(
                capability=self.name,
                confidence=0.95 if any(p in q for p in prefixes) else 0.80,
                parameters={"expression": expression}
            )
            
        return None

    def execute(self, params: dict) -> CapabilityResult:
        expression = params.get("expression", "").strip()
        
        # Translate symbols
        sanitized = expression.replace("^", "**")
        # Keep only numbers, math operators, dots, parenthesis, spaces, and math word functions
        # Allow alphabetical characters for math functions like sin, cos, tan, sqrt, pi, e, log, etc.
        sanitized = "".join(c for c in sanitized if c in "0123456789+-*/%().^ abcdefghijklmnopqrstuvwxyz\t")
        
        # Build safe evaluation scope using math module
        safe_dict = {
            k: v for k, v in math.__dict__.items() if not k.startswith("__")
        }
        safe_dict["__builtins__"] = None
        
        try:
            # Evaluate within safe scope
            result = eval(sanitized, safe_dict, {})
            message = mochi_voice.format_calculator(expression, str(result))
            
            # Fire event
            event_bus.publish("CALCULATION_COMPLETED", expression=expression, result=result)
            
            return CapabilityResult(
                success=True,
                data={"expression": expression, "result": result},
                message=message
            )
        except Exception as e:
            err_msg = f"Failed to calculate '{expression}': {e}"
            # Fire event even for failure
            event_bus.publish("CALCULATION_FAILED", expression=expression, error=str(e))
            
            return CapabilityResult(
                success=False,
                data={"expression": expression, "error": str(e)},
                message=f"Meow... I couldn't calculate that, sorry! 🐾 (Error: {e})"
            )
