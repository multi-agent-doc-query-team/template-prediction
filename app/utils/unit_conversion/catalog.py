from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from app.utils.constants import UNIT_CATALOG_FILE as CATALOG_FILE
import hashlib
import json

def content_hash(payload: dict) -> str:
    content = {key: value for key, value in payload.items() if key != "content_sha256"}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()

def _unique_keys(pairs: list[tuple]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate unit catalog key: {key}")
        result[key] = value
    return result

@dataclass(frozen=True)
class UnitCatalog:
    version: str
    dictionary_sha256: str
    units: dict[str, dict]
    custom_definitions: dict[str, str]

    @property
    def supported(self) -> dict[str, dict]:
        return {
            symbol: row for symbol, row in self.units.items()
            if row["status"] == "validated"
        }

    @property
    def unsupported(self) -> dict[str, dict]:
        return {
            symbol: row for symbol, row in self.units.items()
            if row["status"] == "unsupported"
        }

def load_catalog(path: Path = CATALOG_FILE) -> UnitCatalog:
    with path.open(encoding="utf-8") as source:
        payload = json.load(source, object_pairs_hook=_unique_keys)
    if not isinstance(payload, dict):
        raise ValueError("Invalid unit catalog structure.")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("Unsupported unit catalog schema.")
    if payload.get("content_sha256") != content_hash(payload):
        raise ValueError("Unit catalog content does not match its fingerprint.")
    for key in ("catalog_version", "dictionary_sha256"):
        if not isinstance(payload.get(key), str) or not payload[key]:
            raise ValueError(f"Missing unit catalog metadata: {key}")
    units = payload.get("units")
    definitions = payload.get("custom_definitions")
    if not isinstance(units, dict) or not units or not isinstance(definitions, dict):
        raise ValueError("Invalid unit catalog structure.")
    for symbol, row in units.items():
        if not symbol or not isinstance(row, dict):
            raise ValueError("Invalid unit catalog entry.")
        required = ("name", "status")
        if row.get("status") == "validated":
            required += ("dimension", "target_unit", "pint_expression")
        elif row.get("status") == "unsupported":
            required += ("reason",)
        else:
            raise ValueError(f"Invalid unit status: {symbol}")
        if any(not isinstance(row.get(key), str) or not row[key] for key in required):
            raise ValueError(f"Incomplete unit catalog entry: {symbol}")
        if {"multiply", "divide", "add", "subtract"} & row.keys():
            raise ValueError("Live unit metadata must not contain cached formula factors.")
    if any(not name or not isinstance(value, str) or not value
           for name, value in definitions.items()):
        raise ValueError("Invalid custom Pint definition.")
    return UnitCatalog(
        version=payload["catalog_version"],
        dictionary_sha256=payload["dictionary_sha256"],
        units=units,
        custom_definitions=definitions,
    )

@lru_cache(maxsize=1)
def get_catalog() -> UnitCatalog:
    return load_catalog()
