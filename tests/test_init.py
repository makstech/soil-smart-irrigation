"""Config-entry migration."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.soil_smart_irrigation import async_migrate_entry
from custom_components.soil_smart_irrigation.const import DOMAIN


async def test_migrate_v1_fractions_to_percent(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={"mode": "et", "efficiency": 0.9},
        options={"rain_effectiveness": 0.3},
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == 2
    assert entry.data["efficiency"] == 90
    assert entry.options["rain_effectiveness"] == 30
