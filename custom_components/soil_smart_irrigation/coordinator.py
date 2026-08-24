"""Water-need calculation for a Soil Smart Irrigation zone."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AREA_M2,
    CONF_CROP_COEFFICIENT,
    CONF_DOSING_TYPE,
    CONF_EFFICIENCY,
    CONF_ET0_SENSOR,
    CONF_ET_SOURCE,
    CONF_ET_TRIGGER_MM,
    CONF_FLOW_LPM,
    CONF_MIN_INTERVAL_DAYS,
    CONF_MODE,
    CONF_MOISTURE_LOW,
    CONF_MOISTURE_TARGET,
    CONF_LITERS_PER_PLANT,
    CONF_PLANT_COUNT,
    CONF_RAIN_EFFECTIVENESS,
    CONF_RAIN_INTERCEPTION_MM,
    CONF_RAIN_SENSOR,
    CONF_RAIN_SKIP_MM,
    CONF_SOIL_SENSOR,
    CONF_TARGET_MM,
    DEFAULT_CROP_COEFFICIENT,
    DEFAULT_EFFICIENCY,
    DEFAULT_ET_SOURCE,
    DEFAULT_ET_TRIGGER_MM,
    DEFAULT_MIN_INTERVAL_DAYS,
    DEFAULT_MOISTURE_LOW,
    DEFAULT_MOISTURE_TARGET,
    DEFAULT_RAIN_EFFECTIVENESS,
    DEFAULT_RAIN_INTERCEPTION_MM,
    DEFAULT_RAIN_SKIP_MM,
    DOMAIN,
    DOSING_DEPTH,
    ET_SOURCE_SENSOR,
    MODE_ET,
    MODE_HYBRID,
    MODE_SENSOR,
    OPEN_METEO_URL,
    SENSOR_CORRECTION,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

type SoilConfigEntry = ConfigEntry["SoilIrrigationCoordinator"]


class SoilIrrigationCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Compute whether a zone needs water and how much."""

    def __init__(self, hass: HomeAssistant, entry: SoilConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.title}",
            update_interval=timedelta(minutes=10),
        )
        self.entry = entry
        self._store = Store[dict[str, Any]](
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self._deficit_mm = 0.0
        self._last_watered: datetime | None = None
        self._last_rain: float | None = None
        self._last_calc: datetime | None = None
        self._et0: float | None = None
        self._et0_at: datetime | None = None
        # Daily interception window: gross rain seen today and how much of the
        # resulting effective rain has already been credited to the deficit.
        self._rain_day: str | None = None
        self._rain_accum = 0.0
        self._rain_credited = 0.0

    def opt(self, key: str, default: Any = None) -> Any:
        return self.entry.options.get(key, self.entry.data.get(key, default))

    async def async_load_state(self) -> None:
        data = await self._store.async_load() or {}
        self._deficit_mm = float(data.get("deficit_mm", 0.0))
        self._last_rain = data.get("last_rain")
        self._last_watered = _parse(data.get("last_watered"))
        self._last_calc = _parse(data.get("last_calc"))
        self._rain_day = data.get("rain_day")
        self._rain_accum = float(data.get("rain_accum", 0.0))
        self._rain_credited = float(data.get("rain_credited", 0.0))

    async def _async_save(self) -> None:
        await self._store.async_save(
            {
                "deficit_mm": self._deficit_mm,
                "last_rain": self._last_rain,
                "last_watered": _iso(self._last_watered),
                "last_calc": _iso(self._last_calc),
                "rain_day": self._rain_day,
                "rain_accum": self._rain_accum,
                "rain_credited": self._rain_credited,
            }
        )

    def _num(self, entity_id: str | None) -> float | None:
        if not entity_id:
            return None
        state: State | None = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", ""):
            return None
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return None

    async def async_mark_watered(self) -> None:
        self._deficit_mm = 0.0
        self._last_watered = dt_util.utcnow()
        await self._async_save()
        await self.async_request_refresh()

    async def async_reset_deficit(self) -> None:
        self._deficit_mm = 0.0
        await self._async_save()
        await self.async_request_refresh()

    async def _async_update_data(self) -> dict[str, Any]:
        now = dt_util.utcnow()
        mode = self.opt(CONF_MODE, MODE_SENSOR)
        moisture = self._num(self.opt(CONF_SOIL_SENSOR))

        if mode in (MODE_ET, MODE_HYBRID):
            et0 = await self._async_et0()
            if et0 is not None and self._last_calc is not None:
                days = (now - self._last_calc).total_seconds() / 86400
                kc = float(self.opt(CONF_CROP_COEFFICIENT, DEFAULT_CROP_COEFFICIENT))
                self._deficit_mm += kc * et0 * days
            rain = self._num(self.opt(CONF_RAIN_SENSOR))
            if rain is not None:
                if self._last_rain is not None and rain > self._last_rain:
                    self._credit_rain(now, rain - self._last_rain)
                self._last_rain = rain
            self._deficit_mm = max(0.0, self._deficit_mm)

            if mode == MODE_HYBRID:
                measured = self._sensor_deficit(moisture)
                if measured is not None:
                    self._deficit_mm += SENSOR_CORRECTION * (measured - self._deficit_mm)
                    self._deficit_mm = max(0.0, self._deficit_mm)

        self._last_calc = now

        interval_ok = self._interval_ok(now)
        rain_skip = self._rain_skip()

        need_sensor = (
            moisture is not None
            and moisture <= float(self.opt(CONF_MOISTURE_LOW, DEFAULT_MOISTURE_LOW))
        )
        need_et = self._deficit_mm >= float(
            self.opt(CONF_ET_TRIGGER_MM, DEFAULT_ET_TRIGGER_MM)
        )

        # Hybrid deficit is already pulled toward the sensor, so it triggers on need_et too.
        base_need = need_sensor if mode == MODE_SENSOR else need_et

        needed = bool(base_need and interval_ok and not rain_skip)
        liters = self._required_liters(mode)

        result = {
            "needed": needed,
            "required_liters": round(liters, 1),
            "duration_min": self._duration(liters),
            "deficit_mm": round(self._deficit_mm, 2),
            "moisture": moisture,
            "et0": self._et0,
            "interval_ok": interval_ok,
            "rain_skipped": rain_skip,
            "last_watered": _iso(self._last_watered),
        }
        await self._async_save()
        return result

    async def _async_et0(self) -> float | None:
        if self.opt(CONF_ET_SOURCE, DEFAULT_ET_SOURCE) == ET_SOURCE_SENSOR:
            return self._num(self.opt(CONF_ET0_SENSOR))

        now = dt_util.utcnow()
        if self._et0 is not None and self._et0_at and now - self._et0_at < timedelta(hours=1):
            return self._et0
        try:
            value = await self._fetch_open_meteo_et0()
        except (TimeoutError, aiohttp.ClientError, ValueError, KeyError, IndexError) as err:
            _LOGGER.debug("Open-Meteo ET0 fetch failed: %s", err)
            return self._et0
        if value is not None:
            self._et0 = value
            self._et0_at = now
        return self._et0

    async def _fetch_open_meteo_et0(self) -> float | None:
        session = async_get_clientsession(self.hass)
        params = {
            "latitude": self.hass.config.latitude,
            "longitude": self.hass.config.longitude,
            "daily": "et0_fao_evapotranspiration",
            "timezone": "auto",
            "forecast_days": 1,
        }
        async with asyncio.timeout(20):
            response = await session.get(OPEN_METEO_URL, params=params)
            payload = await response.json()
        values = (payload.get("daily") or {}).get("et0_fao_evapotranspiration") or []
        return float(values[0]) if values and values[0] is not None else None

    def _credit_rain(self, now: datetime, delta: float) -> None:
        """Credit new rainfall against the deficit, per calendar day.

        The first ``rain_interception_mm`` of each day is written off to surface
        evaporation, and only ``rain_effectiveness`` of the rest reaches the root
        zone (mulch, deep roots and drip all shed gauge rainfall). rain-skip is
        left to use the raw gauge total.
        """
        today = dt_util.as_local(now).date().isoformat()
        if self._rain_day != today:
            self._rain_day = today
            self._rain_accum = 0.0
            self._rain_credited = 0.0
        self._rain_accum += delta
        interception = float(
            self.opt(CONF_RAIN_INTERCEPTION_MM, DEFAULT_RAIN_INTERCEPTION_MM)
        )
        effectiveness = float(
            self.opt(CONF_RAIN_EFFECTIVENESS, DEFAULT_RAIN_EFFECTIVENESS)
        ) / 100
        effective = max(0.0, self._rain_accum - interception) * effectiveness
        self._deficit_mm -= max(0.0, effective - self._rain_credited)
        self._rain_credited = effective

    def _sensor_deficit(self, moisture: float | None) -> float | None:
        """Turn a moisture reading into a deficit: 0 at target, trigger at low."""
        if moisture is None:
            return None
        low = float(self.opt(CONF_MOISTURE_LOW, DEFAULT_MOISTURE_LOW))
        target = float(self.opt(CONF_MOISTURE_TARGET, DEFAULT_MOISTURE_TARGET))
        trigger = float(self.opt(CONF_ET_TRIGGER_MM, DEFAULT_ET_TRIGGER_MM))
        if target <= low:
            return None
        frac = (target - moisture) / (target - low)
        return max(0.0, min(frac, 3.0)) * trigger

    def _interval_ok(self, now: datetime) -> bool:
        min_days = float(self.opt(CONF_MIN_INTERVAL_DAYS, DEFAULT_MIN_INTERVAL_DAYS))
        if self._last_watered is None:
            return True
        return (now - self._last_watered).total_seconds() / 86400 >= min_days

    def _rain_skip(self) -> bool:
        rain = self._num(self.opt(CONF_RAIN_SENSOR))
        if rain is None:
            return False
        return rain >= float(self.opt(CONF_RAIN_SKIP_MM, DEFAULT_RAIN_SKIP_MM))

    def _required_liters(self, mode: str) -> float:
        eff = float(self.opt(CONF_EFFICIENCY, DEFAULT_EFFICIENCY)) / 100 or 1.0
        if self.opt(CONF_DOSING_TYPE) == DOSING_DEPTH:
            mm = (
                self._deficit_mm
                if mode in (MODE_ET, MODE_HYBRID)
                else float(self.opt(CONF_TARGET_MM, 0.0))
            )
            area = float(self.opt(CONF_AREA_M2, 0.0))
            return mm * area / eff
        per_plant = float(self.opt(CONF_LITERS_PER_PLANT, 0.0))
        plants = float(self.opt(CONF_PLANT_COUNT, 1) or 1)
        return per_plant * plants / eff

    def _duration(self, liters: float) -> float:
        flow = float(self.opt(CONF_FLOW_LPM, 0.0))
        if flow <= 0:
            return 0.0
        return round(liters / flow, 1)


def _parse(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
