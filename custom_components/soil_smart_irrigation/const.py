"""Constants for Soil Smart Irrigation."""

from __future__ import annotations

DOMAIN = "soil_smart_irrigation"

MODE_SENSOR = "sensor"
MODE_ET = "et"
MODE_HYBRID = "hybrid"
MODES = [MODE_SENSOR, MODE_ET, MODE_HYBRID]

DOSING_VOLUME = "volume"
DOSING_DEPTH = "depth"
DOSING_TYPES = [DOSING_VOLUME, DOSING_DEPTH]

CONF_MODE = "mode"
CONF_SOIL_SENSOR = "soil_sensor"
CONF_MOISTURE_LOW = "moisture_low"
CONF_MOISTURE_TARGET = "moisture_target"
CONF_ET0_SENSOR = "et0_sensor"
CONF_CROP_COEFFICIENT = "crop_coefficient"
CONF_ET_TRIGGER_MM = "et_trigger_mm"
CONF_DOSING_TYPE = "dosing_type"
CONF_LITERS_PER_PLANT = "liters_per_plant"
CONF_PLANT_COUNT = "plant_count"
CONF_TARGET_MM = "target_mm"
CONF_AREA_M2 = "area_m2"
CONF_FLOW_LPM = "flow_lpm"
CONF_EFFICIENCY = "efficiency"
CONF_RAIN_SENSOR = "rain_sensor"
CONF_RAIN_SKIP_MM = "rain_skip_mm"
CONF_RAIN_EFFECTIVENESS = "rain_effectiveness"
CONF_RAIN_INTERCEPTION_MM = "rain_interception_mm"
CONF_MIN_INTERVAL_DAYS = "min_interval_days"

DEFAULT_MOISTURE_LOW = 30.0
DEFAULT_MOISTURE_TARGET = 50.0
DEFAULT_CROP_COEFFICIENT = 0.85
DEFAULT_ET_TRIGGER_MM = 11.0
DEFAULT_EFFICIENCY = 90.0
DEFAULT_RAIN_SKIP_MM = 20.0
DEFAULT_RAIN_EFFECTIVENESS = 100.0
DEFAULT_RAIN_INTERCEPTION_MM = 0.0
DEFAULT_MIN_INTERVAL_DAYS = 3.0

# In hybrid mode, how strongly each update pulls the ET deficit toward the
# sensor-measured value (0 = ignore sensor, 1 = fully trust each reading).
SENSOR_CORRECTION = 0.25

CONF_PLANT_TYPE = "plant_type"
CONF_ET_SOURCE = "et_source"

ET_SOURCE_AUTO = "auto"
ET_SOURCE_SENSOR = "sensor"
ET_SOURCES = [ET_SOURCE_AUTO, ET_SOURCE_SENSOR]
DEFAULT_ET_SOURCE = ET_SOURCE_AUTO

PLANT_LAWN = "lawn"
PLANT_HEDGE = "hedge"
PLANT_TREES = "trees"
PLANT_VEGETABLES = "vegetables"
PLANT_FLOWERS = "flowers"
PLANT_CUSTOM = "custom"
PLANT_TYPES = [
    PLANT_LAWN,
    PLANT_HEDGE,
    PLANT_TREES,
    PLANT_VEGETABLES,
    PLANT_FLOWERS,
    PLANT_CUSTOM,
]

# Per plant type: crop coefficient, deficit trigger (mm), min interval (days),
# soil-moisture low/target (%), rain skip (mm), rain effectiveness (%) + daily
# interception (mm), and a starting dose (L / mm). Mulched/deep/drip plants see
# less of the gauge rain, so their effectiveness is lower.
PRESETS: dict[str, dict[str, float]] = {
    PLANT_LAWN: {"kc": 0.80, "trigger": 11, "interval": 2, "moisture_low": 30, "moisture_target": 45, "rain_skip": 20, "rain_eff": 80, "rain_intercept": 2, "liters": 10, "mm": 15},
    PLANT_HEDGE: {"kc": 0.50, "trigger": 20, "interval": 5, "moisture_low": 30, "moisture_target": 45, "rain_skip": 25, "rain_eff": 30, "rain_intercept": 2, "liters": 10, "mm": 12},
    PLANT_TREES: {"kc": 0.60, "trigger": 25, "interval": 7, "moisture_low": 25, "moisture_target": 40, "rain_skip": 25, "rain_eff": 30, "rain_intercept": 3, "liters": 15, "mm": 12},
    PLANT_VEGETABLES: {"kc": 1.00, "trigger": 8, "interval": 1, "moisture_low": 35, "moisture_target": 55, "rain_skip": 15, "rain_eff": 70, "rain_intercept": 2, "liters": 5, "mm": 12},
    PLANT_FLOWERS: {"kc": 0.90, "trigger": 8, "interval": 2, "moisture_low": 35, "moisture_target": 55, "rain_skip": 15, "rain_eff": 70, "rain_intercept": 2, "liters": 4, "mm": 10},
    PLANT_CUSTOM: {"kc": DEFAULT_CROP_COEFFICIENT, "trigger": DEFAULT_ET_TRIGGER_MM, "interval": DEFAULT_MIN_INTERVAL_DAYS, "moisture_low": DEFAULT_MOISTURE_LOW, "moisture_target": DEFAULT_MOISTURE_TARGET, "rain_skip": DEFAULT_RAIN_SKIP_MM, "rain_eff": DEFAULT_RAIN_EFFECTIVENESS, "rain_intercept": DEFAULT_RAIN_INTERCEPTION_MM, "liters": 10, "mm": 15},
}

# Sprinkler (depth) loses more to wind/evaporation than drip (volume). Percent.
EFFICIENCY_VOLUME = 90.0
EFFICIENCY_DEPTH = 72.0

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

SERVICE_MARK_WATERED = "mark_watered"
SERVICE_RESET_DEFICIT = "reset_deficit"

STORAGE_VERSION = 1
