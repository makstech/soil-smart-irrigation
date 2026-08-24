"""Zone sensors: recommended duration, required water, soil deficit."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfPrecipitationDepth, UnitOfTime, UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SoilConfigEntry, SoilIrrigationCoordinator
from .entity import SoilZoneEntity


@dataclass(frozen=True, kw_only=True)
class SoilSensorDescription(SensorEntityDescription):
    value: Callable[[dict[str, Any]], float | None]


DESCRIPTIONS: tuple[SoilSensorDescription, ...] = (
    SoilSensorDescription(
        key="duration_min",
        translation_key="recommended_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:timer-sand",
        value=lambda d: d.get("duration_min"),
    ),
    SoilSensorDescription(
        key="required_liters",
        translation_key="required_water",
        device_class=SensorDeviceClass.VOLUME_STORAGE,
        native_unit_of_measurement=UnitOfVolume.LITERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:water",
        value=lambda d: d.get("required_liters"),
    ),
    SoilSensorDescription(
        key="deficit_mm",
        translation_key="soil_deficit",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        icon="mdi:water-minus",
        value=lambda d: d.get("deficit_mm"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SoilConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(SoilSensor(coordinator, desc) for desc in DESCRIPTIONS)


class SoilSensor(SoilZoneEntity, SensorEntity):
    entity_description: SoilSensorDescription

    def __init__(
        self, coordinator: SoilIrrigationCoordinator, description: SoilSensorDescription
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | None:
        return self.entity_description.value(self.coordinator.data)
