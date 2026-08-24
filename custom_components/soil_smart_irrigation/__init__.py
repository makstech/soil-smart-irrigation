"""Soil Smart Irrigation integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    CONF_EFFICIENCY,
    CONF_ET0_SENSOR,
    CONF_RAIN_EFFECTIVENESS,
    CONF_RAIN_SENSOR,
    CONF_SOIL_SENSOR,
)
from .coordinator import SoilConfigEntry, SoilIrrigationCoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


async def async_migrate_entry(hass: HomeAssistant, entry: SoilConfigEntry) -> bool:
    """v1 stored efficiency and rain effectiveness as 0-1 fractions; v2 uses percent."""
    if entry.version < 2:

        def to_percent(values: dict) -> dict:
            out = dict(values)
            for key in (CONF_EFFICIENCY, CONF_RAIN_EFFECTIVENESS):
                if out.get(key) is not None:
                    out[key] = round(float(out[key]) * 100, 1)
            return out

        hass.config_entries.async_update_entry(
            entry,
            data=to_percent(entry.data),
            options=to_percent(entry.options),
            version=2,
        )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: SoilConfigEntry) -> bool:
    coordinator = SoilIrrigationCoordinator(hass, entry)
    await coordinator.async_load_state()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    sources = [
        coordinator.opt(key)
        for key in (CONF_SOIL_SENSOR, CONF_ET0_SENSOR, CONF_RAIN_SENSOR)
    ]
    sources = [s for s in sources if s]
    if sources:

        @callback
        def _source_changed(_event: Event) -> None:
            entry.async_create_task(hass, coordinator.async_request_refresh())

        entry.async_on_unload(
            async_track_state_change_event(hass, sources, _source_changed)
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: HomeAssistant, entry: SoilConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SoilConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
