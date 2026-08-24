"""Config and options flow for Soil Smart Irrigation."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector

from .const import (
    CONF_AREA_M2,
    CONF_CROP_COEFFICIENT,
    CONF_DOSING_TYPE,
    CONF_EFFICIENCY,
    CONF_ET0_SENSOR,
    CONF_ET_SOURCE,
    CONF_ET_TRIGGER_MM,
    CONF_FLOW_LPM,
    CONF_LITERS_PER_PLANT,
    CONF_MIN_INTERVAL_DAYS,
    CONF_MODE,
    CONF_MOISTURE_LOW,
    CONF_MOISTURE_TARGET,
    CONF_PLANT_COUNT,
    CONF_PLANT_TYPE,
    CONF_RAIN_EFFECTIVENESS,
    CONF_RAIN_INTERCEPTION_MM,
    CONF_RAIN_SENSOR,
    CONF_RAIN_SKIP_MM,
    CONF_SOIL_SENSOR,
    CONF_TARGET_MM,
    DOMAIN,
    DOSING_TYPES,
    DOSING_VOLUME,
    EFFICIENCY_DEPTH,
    EFFICIENCY_VOLUME,
    ET_SOURCE_AUTO,
    ET_SOURCES,
    MODE_ET,
    MODE_HYBRID,
    MODE_SENSOR,
    MODES,
    PLANT_CUSTOM,
    PLANT_LAWN,
    PLANT_TYPES,
    PRESETS,
)
from .units import is_imperial, to_display, to_metric, unit_for

CONF_NAME = "name"
ADVANCED = "advanced"


def _sensor() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))


def _number(
    low: float, high: float, step: float, unit: str | None
) -> selector.NumberSelector:
    config = selector.NumberSelectorConfig(
        min=low, max=high, step=step, mode=selector.NumberSelectorMode.BOX
    )
    if unit is not None:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(config)


def _select(options: list[str], key: str) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            translation_key=key,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def zone_defaults(mode: str, dosing: str, plant: str) -> dict[str, Any]:
    """Expert parameters derived from the plant preset + dosing (metric)."""
    preset = PRESETS.get(plant, PRESETS[PLANT_CUSTOM])
    return {
        CONF_MOISTURE_LOW: preset["moisture_low"],
        CONF_MOISTURE_TARGET: preset["moisture_target"],
        CONF_CROP_COEFFICIENT: preset["kc"],
        CONF_ET_TRIGGER_MM: preset["trigger"],
        CONF_MIN_INTERVAL_DAYS: preset["interval"],
        CONF_RAIN_SKIP_MM: preset["rain_skip"],
        CONF_RAIN_EFFECTIVENESS: preset["rain_eff"],
        CONF_RAIN_INTERCEPTION_MM: preset["rain_intercept"],
        CONF_EFFICIENCY: EFFICIENCY_VOLUME if dosing == DOSING_VOLUME else EFFICIENCY_DEPTH,
        CONF_ET_SOURCE: ET_SOURCE_AUTO,
        CONF_LITERS_PER_PLANT: preset["liters"],
        CONF_PLANT_COUNT: 1,
        CONF_TARGET_MM: preset["mm"],
        CONF_AREA_M2: 10,
        CONF_FLOW_LPM: 10,
    }


def _key(required: bool, field: str, dd: dict[str, Any]) -> vol.Marker:
    marker = vol.Required if required else vol.Optional
    if dd.get(field) is not None:
        return marker(field, default=dd[field])
    return marker(field)


def settings_schema(
    mode: str, dosing: str, imperial: bool, defaults: dict[str, Any]
) -> vol.Schema:
    """Basic fields at the top; expert knobs in a collapsed Advanced section."""
    dd = to_display(defaults, imperial)

    def n(field: str, low: float, high: float, step: float) -> selector.NumberSelector:
        return _number(low, high, step, unit_for(field, imperial))

    basic: dict[Any, Any] = {}
    adv: dict[Any, Any] = {}

    if mode in (MODE_SENSOR, MODE_HYBRID):
        basic[_key(True, CONF_SOIL_SENSOR, dd)] = _sensor()
        basic[_key(False, CONF_MOISTURE_LOW, dd)] = n(CONF_MOISTURE_LOW, 0, 100, 0.5)
        adv[_key(False, CONF_MOISTURE_TARGET, dd)] = n(CONF_MOISTURE_TARGET, 0, 100, 0.5)

    if mode in (MODE_ET, MODE_HYBRID):
        adv[_key(False, CONF_ET_SOURCE, dd)] = _select(ET_SOURCES, "et_source")
        adv[_key(False, CONF_ET0_SENSOR, dd)] = _sensor()
        adv[_key(False, CONF_CROP_COEFFICIENT, dd)] = n(CONF_CROP_COEFFICIENT, 0, 2, 0.05)
        adv[_key(False, CONF_ET_TRIGGER_MM, dd)] = n(CONF_ET_TRIGGER_MM, 0, 100, 0.5)
        adv[_key(False, CONF_RAIN_EFFECTIVENESS, dd)] = n(CONF_RAIN_EFFECTIVENESS, 0, 100, 1)
        adv[_key(False, CONF_RAIN_INTERCEPTION_MM, dd)] = n(CONF_RAIN_INTERCEPTION_MM, 0, 25, 0.5)

    if dosing == DOSING_VOLUME:
        basic[_key(False, CONF_LITERS_PER_PLANT, dd)] = n(CONF_LITERS_PER_PLANT, 0, 1000, 0.5)
        basic[_key(False, CONF_PLANT_COUNT, dd)] = n(CONF_PLANT_COUNT, 1, 100000, 1)
    else:
        basic[_key(False, CONF_AREA_M2, dd)] = n(CONF_AREA_M2, 0, 100000, 0.5)
        if mode == MODE_SENSOR:
            basic[_key(False, CONF_TARGET_MM, dd)] = n(CONF_TARGET_MM, 0, 100, 0.5)

    basic[_key(True, CONF_FLOW_LPM, dd)] = n(CONF_FLOW_LPM, 0.1, 100000, 0.1)
    basic[_key(False, CONF_RAIN_SENSOR, dd)] = _sensor()
    basic[_key(False, CONF_MIN_INTERVAL_DAYS, dd)] = n(CONF_MIN_INTERVAL_DAYS, 0, 60, 0.5)

    adv[_key(False, CONF_EFFICIENCY, dd)] = n(CONF_EFFICIENCY, 10, 100, 1)
    adv[_key(False, CONF_RAIN_SKIP_MM, dd)] = n(CONF_RAIN_SKIP_MM, 0, 200, 1)

    schema = dict(basic)
    schema[vol.Required(ADVANCED)] = section(vol.Schema(adv), {"collapsed": True})
    return vol.Schema(schema)


def _shape_schema(defaults: dict[str, Any], with_name: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_name:
        fields[vol.Required(CONF_NAME)] = selector.TextSelector()
    fields[vol.Required(CONF_PLANT_TYPE, default=defaults.get(CONF_PLANT_TYPE, PLANT_LAWN))] = (
        _select(PLANT_TYPES, "plant_type")
    )
    fields[vol.Required(CONF_MODE, default=defaults.get(CONF_MODE, MODE_SENSOR))] = _select(
        MODES, "mode"
    )
    fields[vol.Required(CONF_DOSING_TYPE, default=defaults.get(CONF_DOSING_TYPE, DOSING_VOLUME))] = (
        _select(DOSING_TYPES, "dosing_type")
    )
    return vol.Schema(fields)


def _resolve(shape: dict[str, Any], user_input: dict[str, Any], imperial: bool) -> dict[str, Any]:
    flat = dict(user_input)
    flat.update(flat.pop(ADVANCED, None) or {})
    base = zone_defaults(shape[CONF_MODE], shape[CONF_DOSING_TYPE], shape[CONF_PLANT_TYPE])
    picks = {k: v for k, v in shape.items() if k != CONF_NAME}
    return {**base, **picks, **to_metric(flat, imperial)}


class SoilConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        self._shape: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._shape = user_input
            return await self.async_step_settings()
        return self.async_show_form(step_id="user", data_schema=_shape_schema({}, True))

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        imperial = is_imperial(self.hass)
        s = self._shape
        if user_input is not None:
            return self.async_create_entry(
                title=s[CONF_NAME], data=_resolve(s, user_input, imperial)
            )
        defaults = zone_defaults(s[CONF_MODE], s[CONF_DOSING_TYPE], s[CONF_PLANT_TYPE])
        return self.async_show_form(
            step_id="settings",
            data_schema=settings_schema(s[CONF_MODE], s[CONF_DOSING_TYPE], imperial, defaults),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry) -> OptionsFlow:
        return SoilOptionsFlow()


class SoilOptionsFlow(OptionsFlow):
    def __init__(self) -> None:
        self._shape: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            self._shape = user_input
            return await self.async_step_settings()
        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_shape_schema(current, False)
        )

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        imperial = is_imperial(self.hass)
        s = self._shape
        if user_input is not None:
            return self.async_create_entry(data=_resolve(s, user_input, imperial))
        stored = {**self.config_entry.data, **self.config_entry.options}
        defaults = {
            **zone_defaults(s[CONF_MODE], s[CONF_DOSING_TYPE], s[CONF_PLANT_TYPE]),
            **stored,
        }
        return self.async_show_form(
            step_id="settings",
            data_schema=settings_schema(s[CONF_MODE], s[CONF_DOSING_TYPE], imperial, defaults),
        )
