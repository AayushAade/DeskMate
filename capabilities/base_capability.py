class Intent:
    def __init__(self, capability: str, confidence: float, parameters: dict):
        self.capability = capability       # Target capability identifier (e.g., "calculator")
        self.confidence = confidence       # Classification score (0.0 to 1.0)
        self.parameters = parameters       # Extracted command arguments

class CapabilityResult:
    def __init__(self, success: bool, data: dict, message: str):
        self.success = success             # True if executed correctly
        self.data = data                   # Structured raw response payload
        self.message = message             # Mochi-personality-formatted output string

class BaseCapability:
    @property
    def name(self) -> str:
        raise NotImplementedError

    def match_and_extract(self, query: str) -> Intent | None:
        """
        Checks if query matches this capability.
        Returns an Intent if matched, else None.
        """
        raise NotImplementedError

    def execute(self, params: dict) -> CapabilityResult:
        """Executes the capability with given parameters and returns a CapabilityResult."""
        raise NotImplementedError
