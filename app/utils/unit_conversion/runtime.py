from .aliases import CATEGORY_ALIASES, extend_mappings
from .catalog import UnitCatalog, get_catalog
from .pint_engine import PintEngine, get_engine
from .validation import validate_reading

IDENTITY_FORMULA = {"multiply": 1.0, "divide": 1.0, "add": 0.0, "subtract": 0.0}

class RuntimeConverter:
    def __init__(
        self,
        catalog: UnitCatalog | None = None,
        engine: PintEngine | None = None,
    ) -> None:
        self.catalog = get_catalog() if catalog is None else catalog
        self.mappings = extend_mappings(self.catalog.units)
        if engine is not None:
            self.engine = engine
        elif catalog is None:
            self.engine = get_engine()
        else:
            self.engine = PintEngine(self.catalog)

    def _normalize_type(self, reading: dict) -> dict:
        if not isinstance(reading, dict):
            return reading
        reading = dict(reading)
        if not isinstance(reading.get("unit_type"), str):
            return reading
        kind = reading["unit_type"].strip().casefold().replace("-", "_").replace(" ", "_")
        if kind == "hook_weights":
            symbol = reading.get("source_unit")
            row = self.mappings.get(symbol.strip(), {}) if isinstance(symbol, str) else {}
            kind = {"M": "mass", "LM/T2": "force"}.get(row.get("dimension"), "force")
        reading["unit_type"] = CATEGORY_ALIASES.get(kind, kind)
        return reading

    def formula(self, reading: dict) -> dict:
        result = validate_reading(self._normalize_type(reading), self.mappings)
        symbol = result["source_unit"]
        status = result["status"]
        if status == "converted":
            row = self.mappings[symbol]
            coefficients = (
                IDENTITY_FORMULA
                if row["status"] == "passthrough"
                else self.engine.formula(symbol, row["target_unit"])
            )
            return {**result, **coefficients}
        if status in ("unknown_unit", "needs_review", "no_generic_si_conversion", "unsupported"):
            result["status"] = "unsupported"
            result["message"] = self.mappings.get(symbol, {}).get(
                "reason", "No SI conversion formula is implemented for this source unit."
            )
        elif status == "unit_type_unresolved":
            result["status"] = "invalid_unit_type"
            result["message"] = (
                "The supplied unit_type is not supported. Use a supported type or null."
            )
        return result
