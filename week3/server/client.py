"""Open-Meteo HTTP client. Step 5: no MCP — call this from a normal Python process."""
# 这个文件是Open-Meteo客户端的实现，用于通过HTTP请求获取天气数据；
# 根据这个文件后续可以搭建一个MCP服务，提供天气数据给其他程序使用。

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

import httpx

# 日志记录器，用于记录Open-Meteo客户端的日志
logger = logging.getLogger("week3.open_meteo")

# Open-Meteo API URLs，分别用于获取地理编码、天气预报和当前天气数据
GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
)
DAILY_FIELDS = "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum"

WEATHER_CODES: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    51: "Light drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    80: "Slight rain showers",
    95: "Thunderstorm",
}


class OpenMeteoError(Exception):
    """Upstream Open-Meteo request failed or returned nothing useful."""


def describe_weather_code(code: int | None) -> str:
    if code is None:
        return "Unknown"
    return WEATHER_CODES.get(int(code), f"Weather code {code}")


class OpenMeteoClient:
    def __init__(
        self,
        *,
        timeout: float = 10.0,
        max_retries: int = 3,
        client: httpx.Client | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._owns_client = client is None
        self._http = client or httpx.Client(
            timeout=httpx.Timeout(timeout),
            headers={"User-Agent": "cs146s-week3-open-meteo/1.0"},
        )
        self._max_retries = max_retries
        self._sleep = sleep

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def geocode(self, location: str) -> dict[str, Any]:
        name = location.strip()
        if not name:
            raise OpenMeteoError("location is required")
        data = self._get(GEOCODE_URL, {"name": name, "count": 1, "language": "en"})
        results = data.get("results") or []
        if not results:
            raise OpenMeteoError(f"no matching place found for {name!r}")
        hit = results[0]
        try:
            latitude = hit["latitude"]
            longitude = hit["longitude"]
        except KeyError as exc:
            raise OpenMeteoError("geocode result missing coordinates") from exc
        return {
            "name": hit.get("name") or name,
            "country": hit.get("country") or "",
            "admin1": hit.get("admin1") or "",  # 一级行政区
            "latitude": latitude,
            "longitude": longitude,
            "timezone": hit.get("timezone") or "auto",
        }

    def current_weather(self, location: str, timezone: str | None = None) -> dict[str, Any]:
        place = self.geocode(location)
        tz = (timezone or place["timezone"] or "auto").strip() or "auto"
        data = self._get(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "current": CURRENT_FIELDS,
                "timezone": tz,
            },
        )
        current = data.get("current")
        if not current:
            raise OpenMeteoError(f"empty current-weather payload for {place['name']}")
        code = current.get("weather_code")
        return {
            "place": place,
            "timezone": data.get("timezone") or tz,
            "time": current.get("time"),
            "temperature_c": current.get("temperature_2m"),
            "apparent_temperature_c": current.get("apparent_temperature"),
            "relative_humidity_percent": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "weather_code": code,
            "conditions": describe_weather_code(code),
        }

    def forecast(self, location: str, days: int = 3, timezone: str | None = None) -> dict[str, Any]:
        if days < 1 or days > 7:
            raise OpenMeteoError("days must be between 1 and 7")
        place = self.geocode(location)
        tz = (timezone or place["timezone"] or "auto").strip() or "auto"
        data = self._get(
            FORECAST_URL,
            {
                "latitude": place["latitude"],
                "longitude": place["longitude"],
                "daily": DAILY_FIELDS,
                "forecast_days": days,
                "timezone": tz,
            },
        )
        daily = data.get("daily") or {}
        dates = daily.get("time") or []
        if not dates:
            raise OpenMeteoError(f"empty forecast payload for {place['name']}")
        tmax = daily.get("temperature_2m_max") or []
        tmin = daily.get("temperature_2m_min") or []
        precip = daily.get("precipitation_sum") or []
        codes = daily.get("weather_code") or []
        days_out: list[dict[str, Any]] = []
        for i, date in enumerate(dates):
            code = codes[i] if i < len(codes) else None
            days_out.append(
                {
                    "date": date,
                    "temperature_max_c": tmax[i] if i < len(tmax) else None,
                    "temperature_min_c": tmin[i] if i < len(tmin) else None,
                    "precipitation_mm": precip[i] if i < len(precip) else None,
                    "weather_code": code,
                    "conditions": describe_weather_code(code),
                }
            )
        return {"place": place, "timezone": data.get("timezone") or tz, "days": days_out}

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """发送 HTTP GET；对 HTTP 429 做有限次退避，其它 4xx/5xx 不重试。"""
        last_error: OpenMeteoError | None = None
        attempts = self._max_retries + 1
        for attempt in range(1, attempts + 1):
            logger.info("GET %s attempt=%s params=%s", url, attempt, params)
            try:
                response = self._http.get(url, params=params)
            except httpx.TimeoutException as exc:
                raise OpenMeteoError(f"request to {url} timed out") from exc
            except httpx.RequestError as exc:
                raise OpenMeteoError(f"network error calling {url}: {exc}") from exc

            if response.status_code == 429:
                wait = _retry_after_seconds(response, attempt)
                last_error = OpenMeteoError(
                    f"rate limited by Open-Meteo (HTTP 429); retry after {wait:.1f}s"
                )
                logger.warning("%s (attempt %s/%s)", last_error, attempt, attempts)
                if attempt >= attempts:
                    break
                self._sleep(wait)
                continue

            if response.status_code >= 400:
                snippet = (response.text or "")[:200]
                raise OpenMeteoError(
                    f"Open-Meteo HTTP {response.status_code} for {url}: {snippet or 'no body'}"
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise OpenMeteoError(f"invalid JSON from {url}") from exc
            if not isinstance(payload, dict):
                raise OpenMeteoError(f"unexpected JSON shape from {url}")
            return payload

        assert last_error is not None
        raise last_error


def _retry_after_seconds(response: httpx.Response, attempt: int) -> float:
    header = response.headers.get("Retry-After") if response.headers is not None else None
    if header:
        try:
            return max(float(header), 0.1)
        except (TypeError, ValueError):
            pass
    return min(2 ** (attempt - 1), 8.0)  # 返回重试等待时间，随着重试次数增加，等待时间呈指数增长，但不超过8秒。


def _demo() -> None:
    """One live round-trip: geocode Beijing, then current weather. Logs on stderr."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    client = OpenMeteoClient()
    try:
        result = client.current_weather("Beijing")
        # 将返回结果转换为JSON字符串，并写入标准输出
        # 后续构造MCP服务时，就是通过标准输出传递给MCP客户端的。
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    finally:
        client.close()


if __name__ == "__main__":
    _demo()
