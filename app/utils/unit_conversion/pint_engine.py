from functools import lru_cache
from .aliases import ALIASES
from .catalog import UnitCatalog, get_catalog
import math
import pint

TEMPERATURE_INTERVALS = {
    "degree_Celsius": "delta_degree_Celsius",
    "degree_Fahrenheit": "delta_degree_Fahrenheit",
}

class PintEngine:
    def __init__(self, catalog: UnitCatalog | None = None) -> None:
        catalog = get_catalog() if catalog is None else catalog
        self.ureg = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
        for name, expression in catalog.custom_definitions.items():
            self.ureg.define(f"{name} = {expression}")
        self.sources = {}
        for symbol, row in catalog.supported.items():
            quantity = self.ureg.parse_expression(row["pint_expression"])
            if not isinstance(quantity, self.ureg.Quantity):
                quantity = self.ureg.Quantity(quantity, "dimensionless")
            self.sources[symbol] = quantity
        for alias, (canonical, scale) in ALIASES.items():
            quantity = self.sources[canonical]
            self.sources[alias] = self.ureg.Quantity(
                quantity.magnitude * scale, quantity.units
            )

    def formula(self, symbol: str, target: str) -> dict[str, float]:
        try:
            source = self.sources[symbol]
            scale = float(source.magnitude)
            zero = float(self.ureg.Quantity(0, source.units).to(target).magnitude)
            delta = TEMPERATURE_INTERVALS.get(str(source.units))
            slope = float(
                self.ureg.Quantity(scale, delta or source.units).to(target).magnitude
            )
            if not all(math.isfinite(value) for value in (slope, zero)) or slope <= 0:
                raise ValueError("Pint returned nonfinite or nonpositive conversion coefficients.")
            alias_scale = ALIASES.get(symbol, (symbol, 1))[1]
            canonical_slope = slope / alias_scale
            multiply = alias_scale if canonical_slope < 1 else slope
            divide = 1 / canonical_slope if canonical_slope < 1 else 1.0
            if delta == "delta_degree_Fahrenheit" and scale == 1:
                rounded = float(format(divide, ".15g"))
                if math.isclose(rounded, divide, rel_tol=1e-15, abs_tol=0):
                    divide = rounded
            return {
                "multiply": multiply,
                "divide": divide,
                "add": max(0.0, zero),
                "subtract": max(0.0, -zero),
            }
        except (pint.PintError, KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(
                f"Pint could not calculate a safe SI formula for {symbol}."
            ) from error

@lru_cache(maxsize=1)
def get_engine() -> PintEngine:
    return PintEngine()
