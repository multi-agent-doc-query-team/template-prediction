import csv
from typing import Dict, List

from app.utils.config import BASE_DIR


UNIT_FILE = BASE_DIR / "data" / "unit_conversions.csv"


def _load_rules() -> Dict[str, Dict]:
    with open(UNIT_FILE, "r", encoding="utf-8-sig", newline="") as file:
        return {
            row["target_sensor"].strip().upper(): row
            for row in csv.DictReader(file)
        }


def get_unit_metadata(sensor: str) -> Dict[str, str]:
    rule = _load_rules().get(sensor.strip().upper())

    if rule is None:
        raise KeyError(f"No conversion rule exists for sensor: {sensor}")

    return {
        "sensor": rule["target_sensor"],
        "unit_type": rule["unit_type"],
        "source_unit": rule["source_unit"],
        "target_unit": rule["storage_unit"],
    }


def convert_readings(readings: List[Dict]) -> List[Dict]:
    rules = _load_rules()
    converted = []

    for reading in readings:
        sensor = reading["sensor"].strip().upper()
        rule = rules.get(sensor)

        if rule is None:
            raise KeyError(f"No conversion rule exists for sensor: {sensor}")

        source_unit = rule["source_unit"].strip()
        storage_unit = rule["storage_unit"].strip()
        desired_unit = reading["desired_unit"].strip()

        if desired_unit.lower() == source_unit.lower():
            converted_value = float(reading["value"])
        elif desired_unit.lower() == storage_unit.lower():
            converted_value = float(rule["a"]) + float(rule["m"]) * float(reading["value"])
        else:
            raise ValueError(
                f"Sensor {sensor} supports desired units "
                f"{source_unit} and {storage_unit}; received {desired_unit}."
            )

        converted.append(
            {
                "sensor": rule["target_sensor"],
                "value": converted_value,
                "source_unit": source_unit,
                "target_unit": desired_unit,
            }
        )

    return converted
