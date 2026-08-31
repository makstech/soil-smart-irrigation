"""Water-need calculation."""

from datetime import datetime, timedelta, timezone

import pytest
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.soil_smart_irrigation.const import DOMAIN
from custom_components.soil_smart_irrigation.coordinator import SoilIrrigationCoordinator


def _coord(hass, **data):
    entry = MockConfigEntry(domain=DOMAIN, data=data)
    entry.add_to_hass(hass)
    return SoilIrrigationCoordinator(hass, entry)


async def test_sensor_deficit(hass):
    c = _coord(hass, moisture_low=30, moisture_target=50, et_trigger_mm=10)
    assert c._sensor_deficit(50) == 0  # at target
    assert c._sensor_deficit(30) == 10  # at low -> trigger
    assert c._sensor_deficit(40) == pytest.approx(5)  # halfway
    assert c._sensor_deficit(None) is None


async def test_required_liters_volume(hass):
    c = _coord(hass, dosing_type="volume", liters_per_plant=15, plant_count=3, efficiency=90)
    assert c._required_liters("et") == pytest.approx(50)  # 45 net / 0.9


async def test_required_liters_depth(hass):
    c = _coord(hass, dosing_type="depth", area_m2=100, efficiency=72)
    c._deficit_mm = 10
    assert c._required_liters("et") == pytest.approx(10 * 100 / 0.72)


async def test_duration(hass):
    assert _coord(hass, flow_lpm=0.8)._duration(50) == pytest.approx(62.5)
    assert _coord(hass, flow_lpm=0)._duration(50) == 0  # guarded against div-by-zero


async def test_credit_rain_interception_and_effectiveness(hass):
    c = _coord(hass, rain_interception_mm=2, rain_effectiveness=30)
    c._deficit_mm = 30
    now = dt_util.utcnow()
    c._credit_rain(now, 1)  # 1 mm < interception -> nothing
    assert c._deficit_mm == 30
    c._credit_rain(now, 4)  # day total 5 mm -> (5-2) * 0.3 = 0.9
    assert c._deficit_mm == pytest.approx(29.1)


async def test_credit_rain_resets_each_day(hass):
    c = _coord(hass, rain_interception_mm=2, rain_effectiveness=100)
    c._deficit_mm = 30
    day1 = dt_util.utcnow()
    c._credit_rain(day1, 5)  # (5-2) * 1.0 = 3
    assert c._deficit_mm == pytest.approx(27)
    c._credit_rain(day1 + timedelta(days=1), 1)  # new day, 1 mm < interception
    assert c._deficit_mm == pytest.approx(27)


async def test_reload_skips_first_sensor_correction(hass):
    hass.states.async_set("sensor.moisture", "40")  # at low -> measured = trigger = 20
    hass.states.async_set("sensor.et0", "0")  # isolate the blend from ET accrual
    c = _coord(
        hass,
        mode="hybrid",
        et_source="sensor",
        et0_sensor="sensor.et0",
        soil_sensor="sensor.moisture",
        moisture_low=40,
        moisture_target=50,
        et_trigger_mm=20,
    )
    c._deficit_mm = 30
    c._last_calc = dt_util.utcnow()
    await c._async_update_data()  # first refresh after (re)load -> blend skipped
    assert c._deficit_mm == pytest.approx(30)
    await c._async_update_data()  # next update -> 30 + 0.25 * (20 - 30)
    assert c._deficit_mm == pytest.approx(27.5)


def _hour(h):
    return datetime(2026, 9, 1, h, tzinfo=timezone.utc)


async def test_et0_between_integrates_hourly(hass):
    c = _coord(hass)
    c._et0_series = {_hour(10): 0.2, _hour(11): 0.4, _hour(12): 0.3}
    # half of 10:00 (0.1) + all of 11:00 (0.4)
    assert c._et0_between(_hour(10) + timedelta(minutes=30), _hour(12)) == pytest.approx(0.5)
    # a 10-minute slice inside one hourly bucket
    assert c._et0_between(_hour(11), _hour(11) + timedelta(minutes=10)) == pytest.approx(0.4 / 6)
    assert c._et0_between(_hour(20), _hour(21)) == 0  # outside the series


async def test_et_accrual_uses_hourly_integral(hass):
    c = _coord(hass, mode="et", et_source="auto", crop_coefficient=0.5)
    now = dt_util.utcnow()
    top = now.replace(minute=0, second=0, microsecond=0)
    c._et0_series = {top - timedelta(hours=i): 0.6 for i in range(-1, 5)}  # 0.6 mm/h band
    c._et0_series_at = now  # fresh -> no network fetch
    c._last_calc = now - timedelta(hours=1)
    c._deficit_mm = 0
    await c._async_update_data()  # ~1 h * 0.6 mm/h * kc 0.5
    assert c._deficit_mm == pytest.approx(0.3, abs=0.02)
