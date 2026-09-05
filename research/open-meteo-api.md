# Open-Meteo API Research (Forecast + Geocoding)

Research notes only. Both endpoints are free, require no API key for non-commercial use.

## 1. Geocoding API — resolve place names to coordinates

**Endpoint:** `https://geocoding-api.open-meteo.com/v1/search`

### Required query params
- `name` (string) — location name or postal code. Docs note: "Append a country or first-level administrative area after a comma to narrow the results" (e.g. `name=Portland,Oregon`).

### Optional query params
- `count` (int) — number of results, default 10, max 100
- `format` — `json` (default) or `protobuf`
- `language` — default `en`, controls translated place names
- `countryCode` — ISO-3166-1 alpha2 filter to disambiguate
- `apikey` — only needed for the paid/commercial tier with reserved resources

### Response shape
Each match in the `results` array includes: `id`, `name`, `latitude`, `longitude`, `elevation`, `timezone`, `feature_code`, `country_code`, `country`, `country_id`, `population`, `postcodes`, and hierarchical admin fields `admin1`–`admin4` (+ corresponding `adminX_id` fields) — e.g. `admin1` = state/province.

### Matching behavior
Matching is case-insensitive and diacritic-insensitive. Two-character queries require an exact name match; three-or-more character queries use normalized prefix matching against the start of an indexed name.

### Edge cases to design around
- **Ambiguous city name** (e.g. "Springfield", "Portland"): the API returns *multiple* results in the array, ranked but not deterministically singular — the calling app must decide how to disambiguate (ask the user, pick highest population, require country/admin1 qualifier, etc.). This is a real design decision, not something Open-Meteo resolves for you.
- **No results found**: docs do not explicitly document the empty case, but the structural implication (and general REST convention here) is an empty `results` array (or the key possibly absent) rather than an HTTP error — the calling code should handle "0 results" as a first-class case, not assume a hit.
- No rate-limit specific to geocoding beyond the general Open-Meteo free-tier limits (see §3).

Source: [Geocoding API docs](https://open-meteo.com/en/docs/geocoding-api), [open-meteo/geocoding-api GitHub](https://github.com/open-meteo/geocoding-api), [Reverse Geocoding discussion](https://github.com/open-meteo/open-meteo/discussions/698)

## 2. Forecast API — live weather data

**Endpoint:** `https://api.open-meteo.com/v1/forecast`

### Required params
- `latitude`, `longitude` — WGS84 floating point coordinates (from geocoding step, or user-supplied)

### Key optional params
- `timezone` — IANA name (e.g. `Asia/Kolkata`); defaults to GMT if omitted — important because "today"/"this evening" phrasing needs the right local timezone
- `forecast_days` — integer 0–16, default 7 (set to `16` for up to 16-day forecast)
- `past_days` — integer 0–92, default 0 (for "how was the weather yesterday" style questions)
- `temperature_unit` — `celsius` (default) or `fahrenheit`
- `wind_speed_unit` — `kmh` (default), `ms`, `mph`, `kn`
- `precipitation_unit` — `mm` (default) or `inch`
- `current=` , `hourly=`, `daily=` — comma-separated variable lists selecting exactly which fields to return (nothing is included unless requested — you must explicitly list the variables you need)

### Field names available (confirmed from docs)

**Current weather:** "Every weather variable available in hourly data is available as current condition as well" — so `current=temperature_2m,wind_speed_10m,...` pulls the instantaneous now-value of any hourly variable.

**Hourly variables** (selected relevant ones for an outdoor-activity bot):
- Temperature/humidity/atmosphere: `temperature_2m`, `relative_humidity_2m`, `dew_point_2m`, `apparent_temperature` (feels-like), `pressure_msl`, `surface_pressure`, `cloud_cover` (+ `cloud_cover_low/mid/high`)
- Wind: `wind_speed_10m` / `80m` / `120m` / `180m`, `wind_direction_10m` (+ other heights), `wind_gusts_10m`
- Precipitation: `precipitation`, `rain`, `showers`, `snowfall`, `precipitation_probability`, `snow_depth`
- Radiation/UV-adjacent: `shortwave_radiation`, `direct_radiation`, `diffuse_radiation`, `global_tilted_irradiance`
- Other: `visibility`, `evapotranspiration`, `cape` (convective available potential energy — thunderstorm risk proxy), `weather_code` (WMO code), `is_day`
- Note: `uv_index` appears as an **hourly** variable in the general variable catalogue (confirm exact name at request time — closely related to `uv_index_max` in daily); daily has `uv_index_max` and `uv_index_clear_sky_max` confirmed.

**Daily variables:**
- `temperature_2m_max/mean/min`, `apparent_temperature_max/mean/min`
- `precipitation_sum`, `rain_sum`, `showers_sum`, `snowfall_sum`, `precipitation_hours`, `precipitation_probability_max/mean/min`
- `shortwave_radiation_sum`, `wind_speed_10m_max`, `wind_gusts_10m_max`, `wind_direction_10m_dominant`
- `sunshine_duration`, `daylight_duration`, `sunrise`, `sunset`
- `weather_code`, `uv_index_max`, `uv_index_clear_sky_max`, `et0_fao_evapotranspiration`

### Response JSON shape (example structure)
```json
{
  "latitude": 52.52,
  "longitude": 13.419,
  "elevation": 44.8,
  "generationtime_ms": 2.21,
  "utc_offset_seconds": 0,
  "timezone": "Europe/Berlin",
  "current": { "time": "...", "temperature_2m": 18.3, "wind_speed_10m": 12.1 },
  "current_units": { "temperature_2m": "°C" },
  "hourly": { "time": ["2026-09-04T00:00", "..."], "temperature_2m": [13, 12.7] },
  "hourly_units": { "temperature_2m": "°C" },
  "daily": { "time": ["2026-09-04"], "temperature_2m_max": [29.1] },
  "daily_units": { "temperature_2m_max": "°C" }
}
```
Every data block is paired with a `*_units` object — this is directly useful for grounding: the bot can quote both the number and its unit straight from the response rather than assuming units.

### Error / edge cases
- Invalid parameters return **HTTP 400** with a JSON body `{"error": true, "reason": "..."}` — the calling code should check for this rather than assuming 200 always.
- API downtime / network failure: no special error contract documented beyond standard HTTP failure — the app-level design must treat "request failed or timed out" as its own explicit branch (this is exactly the brief's "must honestly say API unreachable" requirement).
- 7-day-forecast is the default window; anything beyond `forecast_days=16` is out of range.

Source: [Open-Meteo Docs (forecast)](https://open-meteo.com/en/docs), [Open-Meteo Features](https://open-meteo.com/en/features), [Weather Forecast using OpenMeteo API tutorial](https://www.geopythontutorials.com/notebooks/openmeteo_weather_forecast.html)

## 3. Rate limits / terms of use (free tier)

- Free tier is for **non-commercial use only**, no uptime guarantee.
- Commonly cited free-tier limits: **600 calls/minute, 5,000 calls/hour, 10,000 calls/day, 300,000 calls/month** (aggregated across all Open-Meteo APIs, including Geocoding).
- Commercial plans start at $29/month with unlimited rate and 99.9% uptime SLA on reserved infrastructure — not relevant for a take-home but worth noting as a design boundary (don't build assuming SLA-grade uptime).
- Both the forecast and geocoding endpoints share the general free-tier ceiling; no separate published rate limit specific to `/v1/forecast` vs `/v1/search`.

Source: [Open-Meteo Pricing](https://open-meteo.com/en/pricing), [Open-Meteo API guide (freeapisforyou)](https://www.freeapisforyou.in/api/open-meteo), [apio.sh Open-Meteo overview](https://apio.sh/apis/open-meteo)

## 4. Implications for a "never fabricate numbers" bot

- Because nothing is returned unless explicitly requested via `current=`/`hourly=`/`daily=`, the app must decide up front the fixed list of fields it always requests (e.g., temperature, wind, gusts, precipitation probability, UV index) so the LLM composing the final answer only ever has real API-returned numbers in its context — never numbers it "recalls" or infers.
- The `*_units` companion objects should be threaded straight into the LLM's context alongside the numeric values, so unit labels in the response are also grounded, not guessed.
- HTTP-400/network-failure must be caught as a distinct state before ever reaching the answer-composition step (this maps directly to the `handle_api_error` branch discussed in `langgraph-patterns.md`).
