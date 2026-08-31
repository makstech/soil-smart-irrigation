<p align="center">
  <img src="custom_components/soil_smart_irrigation/brand/logo.png" alt="Soil Smart Irrigation" width="560">
</p>

<h3 align="center">Home Assistant integration for drip &amp; soil-moisture irrigation</h3>

Water your garden by what the **soil actually needs** — not by a fixed timer. Soil Smart Irrigation is a [Home Assistant](https://www.home-assistant.io/) integration that decides **if, when and how much** to water each zone, driven by a **soil moisture sensor**, an **evapotranspiration (ET) estimate**, or both — and dosed by **volume (liters)** for drip and emitter systems, not just minutes.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Validate](https://github.com/makstech/soil-smart-irrigation/actions/workflows/validate.yml/badge.svg)](https://github.com/makstech/soil-smart-irrigation/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Why another irrigation integration?

Most Home Assistant irrigation tools either **schedule** watering (you decide the amount) or **estimate** soil dryness from the weather (evapotranspiration) and can't read a soil probe at all. If you have a moisture sensor, or you water a hedge or trees with **drippers**, neither fits well.

Soil Smart Irrigation fills that gap:

- **Measure, don't just guess.** Point it at a soil moisture sensor and it waters when the ground is genuinely dry.
- **No sensor? Use ET.** A weather-based water-balance "bucket" keeps working for plants without a probe.
- **Dose in liters, not just minutes.** Give it your emitter flow and it works out the run time to deliver the water each plant needs — the natural unit for drip and micro-irrigation.

## Features

- Per-zone setup — add one zone per plant group (lawn, hedge, trees, berries, beds).
- Plant-type presets so you don't need to know a crop coefficient from a hole in the ground.
- Three modes: **soil sensor**, **evapotranspiration**, or **hybrid**.
- **Automatic ET₀ from [Open-Meteo](https://open-meteo.com/)** (free, no API key, uses your Home Assistant location) — or plug in your own ET₀ sensor.
- Volume (litres per plant) or depth (mm) dosing, converted to a run time from your zone flow.
- Rainfall-aware — skips after real rain, and counts only *effective* rain in the water balance (a per-zone effectiveness factor plus daily interception), so mulched, deep-rooted or drip zones aren't fooled by light showers that only wet the surface.
- Minimum interval between waterings, so roots grow deep.
- Simple outputs you wire to any valve or switch — works with any hardware.

## Installation (HACS)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=makstech&repository=soil-smart-irrigation&category=integration)

Click the badge to add the repository to HACS, or add it manually:

1. In HACS, open the menu → **Custom repositories**.
2. Add `https://github.com/makstech/soil-smart-irrigation` with category **Integration**.
3. Search for **Soil Smart Irrigation**, download, and restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration → Soil Smart Irrigation** and add a zone.

## Configuration

Each zone is one entry. The fields you'll see depend on the mode:

| Field | Meaning |
| --- | --- |
| Mode | `sensor`, `et`, or `hybrid` |
| Soil moisture sensor | The probe for this zone (sensor / hybrid) |
| Water below / target moisture | Trigger and target moisture (%) |
| Reference ET₀ sensor + Kc | Daily ET₀ (mm) and crop coefficient (et / hybrid) |
| Dosing | `volume` (liters) or `depth` (mm over an area) |
| Water per run | Liters, or mm + area |
| Total zone flow | Combined emitter/nozzle flow in L/min |
| Recent rainfall sensor | e.g. a 7-day rainfall total |
| Minimum days between watering | Keep watering deep and infrequent |

## What it gives you

For each zone:

- `binary_sensor.<zone>_irrigation_needed` — whether to water now.
- `sensor.<zone>_recommended_duration` — how long to run (minutes).
- `sensor.<zone>_required_water` — how much to deliver (liters).
- `sensor.<zone>_soil_deficit` — the ET water-balance deficit (mm).
- Buttons to mark a zone watered or reset its deficit.

You wire these to your valves with a small automation, so it works with any controller — a Shelly, an ESPHome board, a Zigbee valve, anything.

## How it works

- **Sensor mode** waters when the moisture reading falls to your low threshold.
- **ET mode** keeps a per-zone water balance: it accrues crop water use (ET₀ × Kc) and subtracts *effective* rainfall — `max(0, daily rain − interception) × effectiveness` — so rain that runs off mulch or never reaches deep roots doesn't wipe the deficit; when the deficit reaches your trigger, it's time to water.
- **Hybrid** trusts the probe when it's reporting and falls back to the ET estimate otherwise.

A minimum interval and a rainfall skip keep watering deep and infrequent, which is better for roots than a daily sprinkle.

### Automatic ET₀ (uses the internet)

In ET or Hybrid mode the default ET₀ source is **Automatic**: once an hour the integration fetches the *hourly* reference-evapotranspiration series from the free [Open-Meteo](https://open-meteo.com/) API, using your Home Assistant location, and accrues the deficit hour by hour — so hot, sunny afternoons push it up faster than cool nights. No API key, no account, and no weather integration required.

- **What's sent:** only your latitude and longitude.
- **What comes back:** the finished FAO-56 Penman-Monteith ET₀, resolved hourly. All the meteorology — temperature, humidity, wind (standardised to 2 m), solar radiation — is computed on Open-Meteo's side, so there's nothing to wire up and no unit or wind-height gotchas.
- **Offline:** the fetched series runs a couple of days ahead, so short outages keep advancing the deficit; the balance also recovers missed hours after a restart.
- **Prefer not to reach out?** Set the ET₀ source (under Advanced) to **Use an ET₀ sensor** and feed your own value; the integration then makes no external calls.

## Roadmap

- Use a soil sensor to auto-calibrate the ET estimate (hybrid mode).
- Soak-and-cycle splitting to avoid runoff on sprinkler zones.
- Optional weather-entity ET₀ source (offline, or your own provider).
- Tests and more translations.

## Related

- [esphome-irrigation-system](https://github.com/makstech/esphome-irrigation-system) — the DIY ESP32 valve/pump controller this was built alongside.

## Contributing

Issues and pull requests are welcome. This is a young project — real-world zones, plant types, and sensors are exactly what it needs.

## License

MIT — see [LICENSE](LICENSE).
