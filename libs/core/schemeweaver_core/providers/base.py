from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> str:
        """Send a system + user message and return the response text."""
        ...
