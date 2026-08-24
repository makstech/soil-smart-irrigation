"""Irrigation-needed binary sensor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SoilConfigEntry
from .entity import SoilZoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoilConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([IrrigationNeededBinarySensor(entry.runtime_data)])


class IrrigationNeededBinarySensor(SoilZoneEntity, BinarySensorEntity):
    _attr_translation_key = "irrigation_needed"
    _attr_icon = "mdi:sprinkler"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "irrigation_needed")

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("needed"))

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        return {
            "interval_ok": data.get("interval_ok"),
            "rain_skipped": data.get("rain_skipped"),
            "moisture": data.get("moisture"),
            "et0": data.get("et0"),
            "last_watered": data.get("last_watered"),
        }
