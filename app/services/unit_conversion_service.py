from functools import lru_cache
from app.schemas.telemetry import ConversionRequest, ConversionResponse, Formula
from app.services.errors import ConversionBatchError
from app.utils.unit_conversion.presentation import display_target_unit
from app.utils.unit_conversion.runtime import RuntimeConverter
from app.utils.unit_conversion.catalog import get_catalog
from app.utils.unit_conversion.unit_types import resolved_type
from app.utils.unit_conversion.aliases import PASSTHROUGH
import pint

COEFFICIENT_FIELDS = ("multiply", "divide", "add", "subtract")

@lru_cache(maxsize=1)
def get_converter() -> RuntimeConverter:
    return RuntimeConverter()

def health() -> dict:
    converter = get_converter()
    statuses = [row["status"] for row in converter.mappings.values()]
    return {
        "status": "healthy",
        "supported_units": sum(s in ("validated", "passthrough") for s in statuses),
        "si_conversion_units": statuses.count("validated"),
        "passthrough_units": len(PASSTHROUGH),
        "dictionary_supported_units": len(get_catalog().supported),
        "unsupported_units": sum(s not in ("validated", "passthrough") for s in statuses),
        "catalog_version": get_catalog().version,
        "alias_version": "workbook-v4",
        "conversion_engine": "pint",
        "pint_version": pint.__version__,
    }

def convert_readings(request: ConversionRequest) -> ConversionResponse:
    converter = get_converter()
    converted: list[Formula] = []
    errors: list[dict] = []
    for index, reading in enumerate(request.readings):
        context = {
            "reading_index": index,
            "mnemonic": reading.mnemonic,
            "source_unit": reading.source_unit,
        }
        try:
            result = converter.formula(reading.model_dump())
        except ValueError as error:
            errors.append({**context, "message": str(error)})
            continue
        if result["status"] != "converted":
            errors.append({
                **context,
                "code": result["status"],
                "message": result["message"],
            })
            continue
        mapping = converter.mappings[reading.source_unit]
        mapped_type = resolved_type(reading.source_unit, mapping)
        unit_type = reading.unit_type
        if (
            unit_type is None
            or unit_type.strip().casefold() in ("", "null", "none")
            or mapping.get("response_type")
        ):
            unit_type = mapped_type
        target_unit = (
            reading.source_unit
            if reading.source_unit in PASSTHROUGH
            else display_target_unit(mapping["dimension"], mapped_type)
        )
        converted.append(Formula(
            sensor=reading.mnemonic,
            target_unit=target_unit,
            unit_type=unit_type,
            **{key: result[key] for key in COEFFICIENT_FIELDS},
        ))
    if errors:
        raise ConversionBatchError(errors)
    return ConversionResponse(converted_values=converted)
