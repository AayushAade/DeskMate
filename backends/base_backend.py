class BaseBackend:
    def generate_response(self, chat_history: list) -> str:
        """
        Generates a text response from the LLM.
        chat_history format: [{"role": "user"|"model", "text": text}]
        """
        raise NotImplementedError
