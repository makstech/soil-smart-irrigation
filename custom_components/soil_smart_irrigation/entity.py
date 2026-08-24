"""Base entity for Soil Smart Irrigation."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SoilIrrigationCoordinator


class SoilZoneEntity(CoordinatorEntity[SoilIrrigationCoordinator]):
    """Common device wiring for a zone's entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SoilIrrigationCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="Soil Smart Irrigation",
            entry_type=DeviceEntryType.SERVICE,
        )
