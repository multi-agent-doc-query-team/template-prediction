"""Shared normalization for provider and activity inputs."""

import re
from difflib import SequenceMatcher


def _key(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return re.sub(r"_+", "_", value).strip("_")


PROVIDER_ALIASES = {
    "slb": "slb",
    "slb_ltd": "slb",
    "slb_intl": "slb",
    "schlumberger": "slb",
    "schlumberger_ltd": "slb",
    "schlumberger_limited": "slb",
    "halliburton": "halliburton",
    "haliburton": "halliburton",
    "baker_hughes": "baker_hughes",
    "bakerhughes": "baker_hughes",
    "baker_hughes_company": "baker_hughes",
    "baker_hughes_co": "baker_hughes",
}

ACTIVITY_ALIASES = {
    "rotary_drilling": "rotary_drilling",
    "rotary_drill": "rotary_drilling",
    "rot_drilling": "rotary_drilling",
    "rotary_mode_drilling": "rotary_drilling",
    "slide_drilling": "slide_drilling",
    "slide_drill": "slide_drilling",
    "sliding_mode_drilling": "slide_drilling",
    "circulating": "circulating",
    "circulation": "circulating",
    "fluid_circulation": "circulating",
    "trip_in": "trip_in",
    "running_in_hole": "trip_in",
    "trip_out": "trip_out",
    "pulling_out_of_hole": "trip_out",
}


def _canonicalize(value: str, aliases: dict[str, str], threshold: float) -> str:
    normalized = _key(value)

    if normalized in aliases:
        return aliases[normalized]

    candidates = list(set(aliases.values()))
    best = max(
        candidates,
        key=lambda candidate: SequenceMatcher(None, normalized, candidate).ratio(),
    )
    score = SequenceMatcher(None, normalized, best).ratio()
    return best if score >= threshold else normalized


def normalize_provider_name(value: str) -> str:
    return _canonicalize(value, PROVIDER_ALIASES, threshold=0.72)


def normalize_activity_name(value: str) -> str:
    return _canonicalize(value, ACTIVITY_ALIASES, threshold=0.68)
