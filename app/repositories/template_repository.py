from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from app.utils.config import get_template_file, get_validation_dataset_file
from app.utils.normalization import normalize_activity_name, normalize_provider_name
import csv
import json

def normalize_well_name(value: str) -> str:
    return value.strip().lower().replace("-", "_").replace(" ", "_")

class TemplateRepository:
    def __init__(self, template_file: Path, validation_file: Path) -> None:
        with template_file.open(encoding="utf-8") as source:
            templates = json.load(source)
        if not isinstance(templates, list) or not templates:
            raise ValueError("Invalid templates.json.")
        self._templates: dict[str, dict] = {}
        for template in templates:
            template_id = template.get("template_id")
            if not template_id:
                raise ValueError("Template is missing template_id.")
            if template_id in self._templates:
                raise ValueError(f"Duplicate template ID: {template_id}")
            self._templates[template_id] = template
        self._providers: set[str] = set()
        self._activities: set[str] = set()
        self._wells: set[str] = set()
        self._combinations: dict[tuple[str, str, str], str | None] = {}
        with validation_file.open(encoding="utf-8-sig", newline="") as source:
            for row in csv.DictReader(source):
                key = self._key(
                    row.get("activity", ""),
                    row.get("well_name", ""),
                    row.get("service_provider", ""),
                )
                provider, activity, well = key
                self._providers.add(provider)
                self._activities.add(activity)
                self._wells.add(well)
                self._combinations.setdefault(key, row.get("template_id") or None)

    @staticmethod
    def _key(activity: str, well: str, provider: str) -> tuple[str, str, str]:
        return (
            normalize_provider_name(provider),
            normalize_activity_name(activity),
            normalize_well_name(well),
        )

    def validate(self, activity: str, well: str, provider: str) -> list[str]:
        key = self._key(activity, well, provider)
        errors = []
        for value, known, code in (
            (key[0], self._providers, "INVALID_SERVICE_PROVIDER"),
            (key[1], self._activities, "INVALID_ACTIVITY"),
            (key[2], self._wells, "INVALID_WELL_NAME"),
        ):
            if value not in known:
                errors.append(code)
        if not errors and key not in self._combinations:
            errors.append("INVALID_WELL_NAME")
        return errors

    def expected_id(self, activity: str, well: str, provider: str) -> str | None:
        return self._combinations.get(self._key(activity, well, provider))

    def get(self, template_id: str) -> dict | None:
        return deepcopy(self._templates.get(template_id))

@lru_cache(maxsize=1)
def get_template_repository() -> TemplateRepository:
    return TemplateRepository(get_template_file(), get_validation_dataset_file())
