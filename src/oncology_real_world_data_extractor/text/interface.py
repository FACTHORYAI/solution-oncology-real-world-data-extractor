"""The one interface every text task is written against."""

from typing import Protocol


class TextModel(Protocol):
    """Anything that reads free text (entity extraction, coding) implements this."""

    def complete(self, instructions: str, text: str) -> str:
        """Return the model's answer for one text."""
        ...
