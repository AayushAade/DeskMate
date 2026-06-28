class BaseBackend:
    def generate_response(self, chat_history: list, context: str = "") -> str:
        """
        Generates a text response from the LLM.
        chat_history format: [{"role": "user"|"model", "text": text}]
        context: Dynamic context details (e.g. memories) to inject.
        """
        raise NotImplementedError

    def generate_stream(self, chat_history: list, context: str = ""):
        """
        Yields text chunks (tokens) sequentially from the LLM.
        chat_history format: [{"role": "user"|"model", "text": text}]
        context: Dynamic context details (e.g. memories) to inject.
        """
        yield self.generate_response(chat_history, context)
