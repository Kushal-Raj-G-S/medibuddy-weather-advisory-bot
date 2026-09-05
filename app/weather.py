"""Open-Meteo access layer. The single source of every number the bot reports.

Nothing here consults the LLM, and nothing outside here is allowed to produce a
weather value. The composer receives only the `facts` mapping built in this
module, which is why a reported number can always be traced to an API response.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

from app import config

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Geocoding is effectively static; a forecast is worth re-fetching sooner.
# Caching cuts duplicate calls from repeated/identical questions, which is
# what actually burns through Open-Meteo's free-tier daily quota under real
# traffic (a retry can't help once that quota, not a transient blip, is the
# reason for the 429).
_CACHE_TTL_SECONDS = {GEOCODE_URL: 3600, FORECAST_URL: 300}
_response_cache = {}

# Requested explicitly: Open-Meteo returns metadata only if no field list is
# passed, and fields such as uv_index are omitted unless named.
CURRENT_FIELDS = [
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
    "wind_gusts_10m",
    "pressure_msl",
    "cloud_cover",
    "visibility",
    "uv_index",
]

HOURLY_FIELDS = CURRENT_FIELDS + ["precipitation_probability"]

DAILY_FIELDS = [
    "precipitation_sum",
    "precipitation_probability_max",
    "uv_index_max",
    "temperature_2m_max",
    "temperature_2m_min",
    "wind_gusts_10m_max",
    "weather_code",
]

# Daily weather_code would collide with the current-conditions one.
DAILY_RENAME = {"weather_code": "weather_code_daily"}

# Hours covered by each named part of the day, in the location's local time.
WINDOWS = {
    "morning": range(6, 12),
    "afternoon": range(12, 17),
    "evening": range(17, 22),
    "night": list(range(22, 24)) + list(range(0, 6)),
}

# How an hourly series collapses to one value over a window. Chosen so the
# aggregate is the risk-relevant one: worst gust, total rain, lowest visibility.
AGGREGATION = {
    "temperature_2m": "max",
    "apparent_temperature": "max",
    "relative_humidity_2m": "mean",
    "precipitation": "sum",
    "precipitation_probability": "max",
    "weather_code": "max",
    "wind_speed_10m": "max",
    "wind_gusts_10m": "max",
    "pressure_msl": "min",
    "cloud_cover": "mean",
    "visibility": "min",
    "uv_index": "max",
}

INTEGER_FIELDS = {
    "relative_humidity_2m",
    "cloud_cover",
    "weather_code",
    "weather_code_daily",
    "precipitation_probability",
    "precipitation_probability_max",
}


class WeatherFetchError(RuntimeError):
    """Base class for every failure that must produce an honest refusal."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class LocationNotResolved(WeatherFetchError):
    pass


class WeatherUnavailable(WeatherFetchError):
    pass


@dataclass
class WeatherSnapshot:
    facts: dict
    units: dict
    resolved_location: str
    latitude: float
    longitude: float
    timezone_name: str
    target_date: str
    window: str
    alternatives: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    fetched_at: str = ""


def _get(url, params, retries=2, backoff_seconds=0.6):
    """GET with a small cache and a short retry for transient failures.

    Only 429/5xx and network errors are retried — those are the ones a second
    attempt a moment later can plausibly fix. Any other 4xx means the request
    itself is wrong, so it's raised immediately instead of retried.
    """
    ttl = _CACHE_TTL_SECONDS.get(url, 0)
    key = (url, tuple(sorted(params.items())))
    if ttl:
        cached = _response_cache.get(key)
        if cached is not None and (time.monotonic() - cached[0]) < ttl:
            return cached[1]

    last_error = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, timeout=config.HTTP_TIMEOUT)
        except requests.RequestException as exc:
            last_error = WeatherUnavailable(f"could not reach {url}: {exc}")
        else:
            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise WeatherUnavailable(f"{url} returned a non-JSON body") from exc
                if ttl:
                    _response_cache[key] = (time.monotonic(), payload)
                return payload
            if response.status_code == 429 or response.status_code >= 500:
                last_error = WeatherUnavailable(
                    f"{url} returned HTTP {response.status_code}"
                )
            else:
                raise WeatherUnavailable(f"{url} returned HTTP {response.status_code}")

        if attempt < retries:
            time.sleep(backoff_seconds * (attempt + 1))

    raise last_error


def geocode(place):
    """Resolve a place name to coordinates.

    An empty result set is treated exactly like an API outage: both mean we
    cannot ground an answer, so both must route to the honest-failure branch.
    """
    place = (place or "").strip()
    if not place:
        raise LocationNotResolved("no location was given")

    payload = _get(GEOCODE_URL, {"name": place, "count": 5, "format": "json"})
    results = payload.get("results") or []
    if not results:
        raise LocationNotResolved(f"no location matched {place!r}")

    top = results[0]
    label_parts = [top.get("name"), top.get("admin1"), top.get("country")]
    alternatives = [
        " ".join(
            str(p) for p in (r.get("name"), r.get("admin1"), r.get("country")) if p
        )
        for r in results[1:]
        if r.get("name")
    ]
    return {
        "label": ", ".join(str(p) for p in label_parts if p),
        "latitude": top["latitude"],
        "longitude": top["longitude"],
        "alternatives": alternatives,
    }


def _round(name, value):
    if value is None:
        return None
    if name in INTEGER_FIELDS:
        return int(round(value))
    return round(float(value), 1)


def _aggregate(name, values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    how = AGGREGATION.get(name, "max")
    if how == "sum":
        return _round(name, sum(values))
    if how == "min":
        return _round(name, min(values))
    if how == "mean":
        return _round(name, sum(values) / len(values))
    return _round(name, max(values))


def _window_facts(hourly, target_date, window):
    """Collapse the hourly series for one part of one day into single values."""
    times = hourly.get("time") or []
    hours = WINDOWS[window]
    indices = []
    for i, stamp in enumerate(times):
        date_part, _, hour_part = stamp.partition("T")
        if not hour_part:
            continue
        hour = int(hour_part[:2])
        if hour not in hours:
            continue
        # The night window wraps past midnight, so its early hours belong to
        # the morning of the following calendar day.
        if window == "night" and hour < 6:
            if date_part <= target_date:
                continue
        elif date_part != target_date:
            continue
        indices.append(i)

    if not indices:
        return {}

    facts = {}
    for name in HOURLY_FIELDS:
        series = hourly.get(name)
        if not series:
            continue
        facts[name] = _aggregate(name, [series[i] for i in indices if i < len(series)])
    return facts


def fetch_weather(place, target_day="today", window=None):
    """Fetch and normalise weather for a place.

    `target_day` is "today" or "tomorrow"; `window` is None (use current
    conditions) or one of WINDOWS. Field names in the returned `facts` are
    identical either way, so an SOP condition is written once and works for
    "right now" and for "this evening" alike.
    """
    if window is not None and window not in WINDOWS:
        raise ValueError(f"unknown window {window!r}")

    location = geocode(place)

    day_index = 1 if target_day == "tomorrow" else 0
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": ",".join(CURRENT_FIELDS),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": ",".join(DAILY_FIELDS),
        "timezone": "auto",
        "forecast_days": 3,
    }
    payload = _get(FORECAST_URL, params)

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    hourly = payload.get("hourly") or {}
    if not current or not daily.get("time"):
        raise WeatherUnavailable("forecast response contained no weather values")

    dates = daily["time"]
    if day_index >= len(dates):
        raise WeatherUnavailable("forecast response did not cover the requested day")
    target_date = dates[day_index]

    units = dict(payload.get("current_units") or {})
    for name, unit in (payload.get("daily_units") or {}).items():
        units[DAILY_RENAME.get(name, name)] = unit
    for name, unit in (payload.get("hourly_units") or {}).items():
        units.setdefault(name, unit)

    facts = {}
    if window is None and day_index == 0:
        for name in CURRENT_FIELDS:
            facts[name] = _round(name, current.get(name))
        basis = "current conditions"
    else:
        resolved_window = window or "afternoon"
        facts.update(_window_facts(hourly, target_date, resolved_window))
        if not facts:
            raise WeatherUnavailable(
                "forecast response had no hourly values for the requested window"
            )
        basis = f"{resolved_window} of {target_date}"

    for name in DAILY_FIELDS:
        series = daily.get(name)
        if not series or day_index >= len(series):
            continue
        facts[DAILY_RENAME.get(name, name)] = _round(
            DAILY_RENAME.get(name, name), series[day_index]
        )

    facts["resolved_location"] = location["label"]

    return WeatherSnapshot(
        facts=facts,
        units=units,
        resolved_location=location["label"],
        latitude=payload.get("latitude", location["latitude"]),
        longitude=payload.get("longitude", location["longitude"]),
        timezone_name=payload.get("timezone", ""),
        target_date=target_date,
        window=basis,
        alternatives=location["alternatives"],
        raw=payload,
        fetched_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
