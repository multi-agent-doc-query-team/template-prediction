import csv
import json
import logging
import os
from pathlib import Path
from typing import Any

import ollama
import pint

from app.schemas.telemetry import (
    ConvertTelemetryRequest,
    ConvertTelemetryResponse,
    ConvertedTelemetryReading,
    TelemetryReading,
    UnitDecision,
    UnitInterpretationBatch,
)


logger = logging.getLogger(__name__)

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
MAX_READINGS_PER_REQUEST = 50
QWEN_BATCH_SIZE = 10

CATALOG_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "halliburton_sensor_catalog.csv"
)


ureg = pint.UnitRegistry(
    autoconvert_offset_to_baseunit=True,
)

ureg.define("kilopound_mass = 1000 * pound = klbm")
ureg.define("kilopound_force = 1000 * pound_force = klbf")


SI_UNIT_EXPRESSIONS = {
    "m": "meter",
    "m²": "meter ** 2",
    "m³": "meter ** 3",
    "m/s": "meter / second",
    "m/s²": "meter / second ** 2",
    "kg": "kilogram",
    "kg/m³": "kilogram / meter ** 3",
    "s": "second",
    "K": "kelvin",
    "Pa": "pascal",
    "N": "newton",
    "N·m": "newton * meter",
    "J": "joule",
    "W": "watt",
    "m³/s": "meter ** 3 / second",
    "Hz": "hertz",
    "rad": "radian",
    "rad/s": "radian / second",
    "1": "dimensionless",
    "Pa·s": "pascal * second",
    "V": "volt",
    "A": "ampere",
    "Ω": "ohm",
    "F": "farad",
    "lx": "lux",
}


SI_TARGET_BY_TYPE = {
    "length": "m",
    "distance": "m",
    "depth": "m",
    "area": "m²",
    "volume": "m³",
    "speed": "m/s",
    "velocity": "m/s",
    "rate": "m/s",
    "acceleration": "m/s²",
    "mass": "kg",
    "density": "kg/m³",
    "time": "s",
    "temperature": "K",
    "pressure": "Pa",
    "force": "N",
    "torque": "N·m",
    "energy": "J",
    "power": "W",
    "volume_flow": "m³/s",
    "frequency": "Hz",
    "angle": "rad",
    "rotational_speed": "rad/s",
    "dynamic_viscosity": "Pa·s",
    "voltage": "V",
    "electric_current": "A",
    "electrical_resistance": "Ω",
    "capacitance": "F",
    "illuminance": "lx",
}


DIMENSIONLESS_TYPES = {
    "dimensionless",
    "unitless",
}


TEXT_TYPES = {
    "text",
    "status",
    "categorical",
    "datetime",
}


UNIT_ALIASES = {
    "ft": "foot",
    "ft/hr": "foot / hour",
    "ft/h": "foot / hour",
    "m/h": "meter / hour",
    "ft/s": "foot / second",
    "ft/min": "foot / minute",
    "galus/min": "gallon / minute",
    "gallus/min": "gallon / minute",
    "kg/m3": "kilogram / meter ** 3",
    "kgm3": "kilogram / meter ** 3",
    "g/cm3": "gram / centimeter ** 3",
    "ppg": "pound / gallon",
    "lbm/galus": "pound / gallon",
    "psf": "pound_force / foot ** 2",
    "psig": "psi",
    "psi": "psi",
    "n.m": "newton * meter",
    "kn.m": "kilonewton * meter",
    "ft.lbf": "foot * pound_force",
    "kft.lbf": "kilopound_force * foot",
    "degc": "degree_Celsius",
    "degf": "degree_Fahrenheit",
    "dps": "degree / second",
    "dega": "degree",
    "spm": "1 / minute",
    "rpm": "revolution / minute",
    "bbl": "oil_barrel",
    "bbl/d": "oil_barrel / day",
    "bbl/m": "oil_barrel / minute",
    "bbl/min": "oil_barrel / minute",
    "lbm": "pound",
    "stks": "dimensionless",
    "unitless": "dimensionless",
    "%": "percent",
    "percent": "percent",
    "cp": "centipoise",
    "hr": "hour",
    "hrs": "hour",
    "min": "minute",
    "in": "inch",
    "cm": "centimeter",
    "mm": "millimeter",
    "ml": "milliliter",
    "mv": "millivolt",
    "ma": "milliampere",
    "uf": "microfarad",
}


class UnitConversionError(ValueError):
    pass


class UnitModelUnavailable(RuntimeError):
    pass


class _DecisionBatchError(ValueError):
    pass


def _load_sensor_catalog() -> dict[str, dict[str, str]]:
    if not CATALOG_PATH.exists():
        raise FileNotFoundError(
            f"Sensor catalog not found: {CATALOG_PATH}"
        )

    catalog: dict[str, dict[str, str]] = {}

    with CATALOG_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        for row in csv.DictReader(file):
            mnemonic = (
                row.get("mnemonic") or ""
            ).strip().upper()

            if mnemonic:
                catalog[mnemonic] = {
                    "description": (
                        row.get("description") or ""
                    ).strip()
                }

    return catalog


SENSOR_CATALOG = _load_sensor_catalog()


SYSTEM_PROMPT = f"""
You classify structured oilfield telemetry readings.

Return exactly one decision for every reading, in the same order.

Each decision must contain only:

- reading_type
- unit_type

Valid reading_type values:

- physical
- dimensionless
- text
- unknown

Allowed physical unit types:

{", ".join(SI_TARGET_BY_TYPE.keys())}

Rules:

1. Use the supplied unit_type when it is present and supported.
2. If unit_type is missing, infer it from the mnemonic, source_unit,
   and catalog description.
3. Do not calculate values.
4. Do not return target units.
5. Do not return formulas.
6. Do not return explanations.
7. Percent values are dimensionless.
8. Values with unitless source units may be dimensionless,
   categorical, text, or datetime depending on the mnemonic and value.
9. Return only valid JSON.
10. Return no Markdown code fences.

Required format:

{{
  "decisions": [
    {{
      "reading_type": "physical",
      "unit_type": "length"
    }}
  ]
}}
"""


def _normalize_unit_type(value: str) -> str:
    return (
        value.strip()
        .casefold()
        .replace("-", "_")
        .replace(" ", "_")
    )


def _parse_source_unit(source_unit: str):
    cleaned = " ".join(
        source_unit.strip().split()
    )

    expression = UNIT_ALIASES.get(
        cleaned.casefold(),
        cleaned,
    )

    try:
        return ureg.parse_units(expression)
    except Exception as exc:
        raise UnitConversionError(
            f"Unrecognized source unit '{source_unit}'."
        ) from exc


def _catalog_reference(sensor: str) -> dict[str, str] | None:
    entry = SENSOR_CATALOG.get(
        sensor.strip().upper()
    )

    if entry is None:
        return None

    return {
        "mnemonic": sensor.strip().upper(),
        "description": entry.get("description", ""),
    }


def _decision_from_supplied_type(
    reading: TelemetryReading,
) -> UnitDecision | None:
    if not reading.unit_type:
        return None

    supplied_type = reading.unit_type.strip()

    if supplied_type.casefold() == "null":
        return None

    normalized_type = _normalize_unit_type(
        supplied_type
    )

    if normalized_type in DIMENSIONLESS_TYPES:
        return UnitDecision(
            reading_type="dimensionless",
            unit_type=normalized_type,
        )

    if normalized_type in TEXT_TYPES:
        return UnitDecision(
            reading_type="text",
            unit_type=normalized_type,
        )

    if normalized_type in SI_TARGET_BY_TYPE:
        return UnitDecision(
            reading_type="physical",
            unit_type=normalized_type,
        )

    return None


def _ask_qwen_batch(
    readings: list[TelemetryReading],
) -> UnitInterpretationBatch:
    payload = {
        "readings": [
            {
                "Mnemonic": reading.sensor,
                "value": reading.value,
                "source_unit": reading.source_unit,
                "unit_type": reading.unit_type,
                "catalog_reference": _catalog_reference(
                    reading.sensor
                ),
            }
            for reading in readings
        ]
    }

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL,
            think=False,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        payload,
                        ensure_ascii=False,
                    ),
                },
            ],
            format=UnitInterpretationBatch.model_json_schema(),
            options={
                "temperature": 0,
                "num_predict": max(
                    128,
                    len(readings) * 32,
                ),
            },
            keep_alive="30m",
        )

    except Exception as exc:
        logger.exception("Ollama call failed")
        raise UnitModelUnavailable(
            "Could not connect to the local Qwen model."
        ) from exc

    raw_response = (
        response.message.content or ""
    ).strip()

    if not raw_response:
        raise _DecisionBatchError(
            "Qwen returned an empty response."
        )

    raw_response = raw_response.replace(
        "```json",
        "",
    ).replace(
        "```",
        "",
    ).strip()

    try:
        result = (
            UnitInterpretationBatch
            .model_validate_json(raw_response)
        )

    except Exception as exc:
        logger.exception(
            "Qwen response parsing failed: %r",
            raw_response,
        )
        raise _DecisionBatchError(
            "Qwen returned invalid JSON."
        ) from exc

    if len(result.decisions) != len(readings):
        raise _DecisionBatchError(
            "Qwen returned an incorrect number of decisions."
        )

    return result


def _ask_qwen_with_split(
    readings: list[TelemetryReading],
) -> list[UnitDecision]:
    decisions: list[UnitDecision] = []

    for start in range(
        0,
        len(readings),
        QWEN_BATCH_SIZE,
    ):
        batch = readings[
            start : start + QWEN_BATCH_SIZE
        ]

        try:
            result = _ask_qwen_batch(batch)
            decisions.extend(result.decisions)

        except _DecisionBatchError:
            if len(batch) == 1:
                raise UnitConversionError(
                    "Qwen could not interpret a reading."
                )

            midpoint = len(batch) // 2

            decisions.extend(
                _ask_qwen_with_split(
                    batch[:midpoint]
                )
            )

            decisions.extend(
                _ask_qwen_with_split(
                    batch[midpoint:]
                )
            )

    return decisions


def _get_interpretations(
    readings: list[TelemetryReading],
) -> list[UnitDecision]:
    decisions: list[UnitDecision | None] = [
        None
    ] * len(readings)

    unresolved_indexes: list[int] = []

    for index, reading in enumerate(readings):
        sensor = reading.sensor.strip().upper()

        if sensor not in SENSOR_CATALOG:
            raise UnitConversionError(
                f"Unknown sensor mnemonic '{reading.sensor}'."
            )

        supplied_decision = (
            _decision_from_supplied_type(reading)
        )

        if supplied_decision is not None:
            decisions[index] = supplied_decision
        else:
            unresolved_indexes.append(index)

    unresolved_readings = [
        readings[index]
        for index in unresolved_indexes
    ]

    if unresolved_readings:
        inferred_decisions = _ask_qwen_with_split(
            unresolved_readings
        )

        for index, decision in zip(
            unresolved_indexes,
            inferred_decisions,
        ):
            decisions[index] = decision

    return [
        decision
        for decision in decisions
        if decision is not None
    ]


def _display_conversion_rule(
    source_unit_text: str,
    target_unit: str | None,
) -> tuple[float, float, float, float]:
    """
    Returns:
    multiply, subtract, divide, add

    Formula:
    output = (((input - subtract) / divide) * multiply) + add
    """

    unit = source_unit_text.strip().casefold()

    if target_unit == "K" and unit in {
        "degf",
        "°f",
    }:
        return 1.0, 32.0, 1.8, 273.15

    if target_unit == "K" and unit in {
        "degc",
        "°c",
    }:
        return 1.0, 0.0, 1.0, 273.15

    if target_unit == "Hz" and unit == "spm":
        return 1.0, 0.0, 60.0, 0.0

    if target_unit == "rad/s" and unit == "rpm":
        return 2 * 3.141592653589793, 0.0, 60.0, 0.0

    if target_unit == "m" and unit == "ft":
        return 0.3048, 0.0, 1.0, 0.0

    if target_unit == "m" and unit == "in":
        return 0.0254, 0.0, 1.0, 0.0

    if target_unit == "Pa" and unit in {
        "psi",
        "psig",
    }:
        return 6894.757293, 0.0, 1.0, 0.0

    if target_unit == "kg/m³" and unit == "ppg":
        return 119.8264273, 0.0, 1.0, 0.0

    if target_unit == "kg/m³" and unit == "g/cm3":
        return 1000.0, 0.0, 1.0, 0.0

    if target_unit == "N" and unit == "klbf":
        return 4448.221615, 0.0, 1.0, 0.0

    if target_unit == "N·m" and unit == "kft.lbf":
        return 1355.817948, 0.0, 1.0, 0.0

    if target_unit == "m³" and unit == "bbl":
        return 0.1589872949, 0.0, 1.0, 0.0

    if target_unit == "m³/s" and unit == "galus/min":
        return 0.0000630902, 0.0, 1.0, 0.0

    if target_unit == "m³/s" and unit in {
        "bbl/m",
        "bbl/min",
    }:
        return 0.1589872949, 0.0, 1.0, 0.0

    if target_unit == "m/s" and unit in {
        "ft/hr",
        "ft/h",
    }:
        return 0.3048, 0.0, 3600.0, 0.0

    if target_unit == "rad" and unit in {
        "dega",
        "deg",
        "degree",
    }:
        return 3.141592653589793, 0.0, 180.0, 0.0

    if target_unit is None:
        return 1.0, 0.0, 1.0, 0.0

    return 1.0, 0.0, 1.0, 0.0


def _convert_one(
    reading: TelemetryReading,
    interpretation: UnitDecision,
) -> ConvertedTelemetryReading:
    sensor = reading.sensor.strip().upper()
    reading_type = interpretation.reading_type

    if reading_type == "unknown":
        raise UnitConversionError(
            f"Could not identify the unit type for '{sensor}'."
        )

    if reading_type == "text":
        return ConvertedTelemetryReading(
            sensor=sensor,
            target_unit=None,
            unit_type=interpretation.unit_type,
            multiply=None,
            subtract=None,
            divide=None,
            add=None,
        )

    if reading_type == "dimensionless":
        if reading.source_unit:
            source_unit = _parse_source_unit(
                reading.source_unit
            )

            try:
                ureg.Quantity(
                    1,
                    source_unit,
                ).to(
                    SI_UNIT_EXPRESSIONS["1"]
                )

            except pint.errors.DimensionalityError as exc:
                raise UnitConversionError(
                    f"'{reading.source_unit}' is not "
                    f"dimensionless for '{sensor}'."
                ) from exc

        return ConvertedTelemetryReading(
            sensor=sensor,
            target_unit=None,
            unit_type=interpretation.unit_type,
            multiply=1.0,
            subtract=0.0,
            divide=1.0,
            add=0.0,
        )

    if not isinstance(
        reading.value,
        (int, float),
    ):
        raise UnitConversionError(
            f"Physical reading '{sensor}' must be numeric."
        )

    if not reading.source_unit:
        raise UnitConversionError(
            f"Source unit is required for '{sensor}'."
        )

    unit_type = interpretation.unit_type

    if not unit_type:
        raise UnitConversionError(
            f"Could not identify unit type for '{sensor}'."
        )

    normalized_type = _normalize_unit_type(
        unit_type
    )

    target_label = SI_TARGET_BY_TYPE.get(
        normalized_type
    )

    if target_label is None:
        raise UnitConversionError(
            f"Unsupported unit_type '{unit_type}' "
            f"for '{sensor}'."
        )

    source_unit = _parse_source_unit(
        reading.source_unit
    )

    target_expression = SI_UNIT_EXPRESSIONS[
        target_label
    ]

    try:
        ureg.Quantity(
            reading.value,
            source_unit,
        ).to(target_expression)

    except pint.errors.DimensionalityError as exc:
        raise UnitConversionError(
            f"'{reading.source_unit}' is not compatible with "
            f"unit_type '{unit_type}' for '{sensor}'."
        ) from exc

    (
        multiply,
        subtract,
        divide,
        add,
    ) = _display_conversion_rule(
        reading.source_unit,
        target_label,
    )

    return ConvertedTelemetryReading(
        sensor=sensor,
        target_unit=target_label,
        unit_type=unit_type,
        multiply=multiply,
        subtract=subtract,
        divide=divide,
        add=add,
    )


def convert_readings(
    request: ConvertTelemetryRequest,
) -> ConvertTelemetryResponse:
    if len(request.readings) > MAX_READINGS_PER_REQUEST:
        raise UnitConversionError(
            f"Maximum {MAX_READINGS_PER_REQUEST} readings allowed."
        )

    interpretations = _get_interpretations(
        request.readings
    )

    if len(interpretations) != len(
        request.readings
    ):
        raise UnitConversionError(
            "The number of decisions did not match readings."
        )

    converted_values = [
        _convert_one(
            reading,
            interpretation,
        )
        for reading, interpretation in zip(
            request.readings,
            interpretations,
        )
    ]

    return ConvertTelemetryResponse(
        converted_values=converted_values,
    )