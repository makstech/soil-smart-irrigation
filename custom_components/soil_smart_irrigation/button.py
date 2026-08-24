"""Buttons to mark a zone watered or reset its deficit."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SoilConfigEntry, SoilIrrigationCoordinator
from .entity import SoilZoneEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoilConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            SoilButton(
                coordinator, "mark_watered", coordinator.async_mark_watered
            ),
            SoilButton(
                coordinator, "reset_deficit", coordinator.async_reset_deficit
            ),
        ]
    )


class SoilButton(SoilZoneEntity, ButtonEntity):
    def __init__(
        self,
        coordinator: SoilIrrigationCoordinator,
        key: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        super().__init__(coordinator, key)
        self._attr_translation_key = key
        self._action = action

    async def async_press(self) -> None:
        await self._action()
