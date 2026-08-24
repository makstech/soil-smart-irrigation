"""Present config fields in the user's unit system; store everything metric."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from .const import (
    CONF_AREA_M2,
    CONF_CROP_COEFFICIENT,
    CONF_EFFICIENCY,
    CONF_ET_TRIGGER_MM,
    CONF_FLOW_LPM,
    CONF_LITERS_PER_PLANT,
    CONF_MIN_INTERVAL_DAYS,
    CONF_MOISTURE_LOW,
    CONF_MOISTURE_TARGET,
    CONF_RAIN_EFFECTIVENESS,
    CONF_RAIN_INTERCEPTION_MM,
    CONF_RAIN_SKIP_MM,
    CONF_TARGET_MM,
)

# field -> (metric unit, imperial unit, imperial->metric factor)
CONVERTED: dict[str, tuple[str, str, float]] = {
    CONF_LITERS_PER_PLANT: ("L", "gal", 3.785411784),
    CONF_FLOW_LPM: ("L/min", "gal/min", 3.785411784),
    CONF_TARGET_MM: ("mm", "in", 25.4),
    CONF_ET_TRIGGER_MM: ("mm", "in", 25.4),
    CONF_RAIN_SKIP_MM: ("mm", "in", 25.4),
    CONF_RAIN_INTERCEPTION_MM: ("mm", "in", 25.4),
    CONF_AREA_M2: ("m²", "sq ft", 0.09290304),
}

STATIC: dict[str, str | None] = {
    CONF_MOISTURE_LOW: "%",
    CONF_MOISTURE_TARGET: "%",
    CONF_CROP_COEFFICIENT: None,
    CONF_EFFICIENCY: "%",
    CONF_RAIN_EFFECTIVENESS: "%",
    CONF_MIN_INTERVAL_DAYS: "d",
}


def is_imperial(hass: HomeAssistant) -> bool:
    return hass.config.units is US_CUSTOMARY_SYSTEM


def unit_for(field: str, imperial: bool) -> str | None:
    if field in CONVERTED:
        metric, imp, _ = CONVERTED[field]
        return imp if imperial else metric
    return STATIC.get(field)


def to_metric(data: dict[str, Any], imperial: bool) -> dict[str, Any]:
    if not imperial:
        return data
    out = dict(data)
    for field, (_, _, factor) in CONVERTED.items():
        if out.get(field) is not None:
            out[field] = round(float(out[field]) * factor, 4)
    return out


def to_display(data: dict[str, Any], imperial: bool) -> dict[str, Any]:
    if not imperial:
        return data
    out = dict(data)
    for field, (_, _, factor) in CONVERTED.items():
        if out.get(field) is not None:
            out[field] = round(float(out[field]) / factor, 3)
    return out
