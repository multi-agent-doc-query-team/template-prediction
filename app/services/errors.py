from typing import Any

class ConversionBatchError(Exception):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__("One or more readings cannot be converted.")
