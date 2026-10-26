from .dimensions import physical_dimensions
from .unit_types import TYPE_DIMENSIONS
import math

EMPTY_TYPES = ("", "null", "none")
PASSTHROUGH_TYPES = EMPTY_TYPES + (
    "unitless", "dimensionless", "passthrough", "timestamp", "datetime", "date time",
)

def _type_error(supplied: str | None, dimension: str) -> tuple[str, str] | None:
    if supplied is not None and not isinstance(supplied, str):
        raise ValueError("unit_type must be a string or null.")
    if supplied is None or supplied.strip().casefold() in EMPTY_TYPES:
        return None
    kind = supplied.strip().lower().replace("-", "_").replace(" ", "_")
    if kind.startswith("dimension:"):
        if kind.removeprefix("dimension:").upper() != dimension.upper():
            return (
                "unit_type_conflict",
                "Supplied unit dimension conflicts with the dictionary meaning.",
            )
        return None
    expected = TYPE_DIMENSIONS.get(kind)
    if expected is None:
        return (
            "unit_type_unresolved",
            "The supplied unit type is not supported by this lookup.",
        )
    semantic_conflict = (
        (expected in ("A", "A/T") and dimension != expected)
        or (kind in ("frequency", "dimensionless", "unitless") and "A" in dimension)
        or (kind == "temperature" and dimension == "D")
        or (kind == "temperature_interval" and dimension == "K")
    )
    if semantic_conflict or physical_dimensions(expected) != physical_dimensions(dimension):
        return (
            "unit_type_conflict",
            "Supplied unit type conflicts with the dictionary meaning.",
        )
    return None

def validate_reading(reading: dict, mappings: dict[str, dict]) -> dict:
    if not isinstance(reading, dict):
        raise ValueError("Each reading must be a JSON object.")
    if set(reading) - {"mnemonic", "value", "source_unit", "unit_type"}:
        raise ValueError("Only mnemonic, value, source_unit and unit_type are accepted.")
    if not isinstance(reading.get("mnemonic"), str) or not reading["mnemonic"].strip():
        raise ValueError("A nonblank mnemonic is required.")
    value = reading.get("value")
    if "value" not in reading or isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError("Value must be a number or string; booleans are not readings.")
    symbol = reading.get("source_unit")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("A source_unit is required for dictionary lookup.")
    symbol = symbol.strip()
    result = {"mnemonic": reading["mnemonic"], "source_unit": symbol}
    row = mappings.get(symbol)
    if row is None:
        return {
            **result, "status": "unknown_unit",
            "message": "Source unit does not exactly match a dictionary symbol.",
        }
    if row["status"] == "passthrough":
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("A nonblank passthrough value is required.")
        elif not math.isfinite(value):
            raise ValueError("A finite numeric value is required.")
        supplied = reading.get("unit_type")
        if supplied is not None and (
            not isinstance(supplied, str)
            or supplied.strip().casefold() not in PASSTHROUGH_TYPES
        ):
            return {
                **result, "status": "unit_type_conflict",
                "message": "Passthrough does not establish a physical measurement type.",
            }
        return {**result, "status": "converted", "target_unit": row["target_unit"]}
    if row["status"] != "validated":
        return {
            **result, "status": row["status"],
            "message": row.get("reason", "Mapping needs review."),
        }
    try:
        finite_number = type(value) in (int, float) and math.isfinite(value)
    except (OverflowError, ValueError):
        finite_number = False
    if not finite_number:
        raise ValueError("A finite numeric value is required for a physical conversion formula.")
    error = _type_error(reading.get("unit_type"), row["dimension"])
    if error:
        status, message = error
        return {**result, "status": status, "message": message}
    return {**result, "status": "converted", "target_unit": row["target_unit"]}
