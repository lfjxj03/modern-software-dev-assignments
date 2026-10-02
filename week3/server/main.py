"""Open-Meteo MCP server: ping, current weather, and daily forecast (stdio or HTTP)."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any

from mcp.server.mcpserver import MCPServer

from week3.server.client import OpenMeteoClient, OpenMeteoError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,  # 将日志输出到标准错误流
)
logger = logging.getLogger("week3.mcp")

mcp = MCPServer("open-meteo")
_client = OpenMeteoClient()


def _json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _place_label(place: dict[str, Any]) -> str:
    return ", ".join(p for p in (place["name"], place.get("admin1"), place.get("country")) if p)


@mcp.tool()
def ping() -> str:
    """Health check that does not call any external API."""
    return "pong"


@mcp.tool()
def get_current_weather(location: str, timezone: str | None = None) -> str:
    """Look up current conditions for a place via Open-Meteo geocoding + forecast.

    Args:
        location: City or place name, e.g. "Beijing" or "Tokyo".
        timezone: Optional IANA timezone (default: timezone from geocoding, else auto).
    """
    try:
        result = _client.current_weather(location, timezone=timezone)
    except OpenMeteoError as exc:
        logger.warning("get_current_weather failed: %s", exc)
        return f"Error: {exc}"
    place = result["place"]
    return _json(
        {
            "location": _place_label(place),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "timezone": result["timezone"],
            "observed_at": result["time"],
            "conditions": result["conditions"],
            "temperature_c": result["temperature_c"],
            "apparent_temperature_c": result["apparent_temperature_c"],
            "relative_humidity_percent": result["relative_humidity_percent"],
            "wind_speed_kmh": result["wind_speed_kmh"],
        }
    )


@mcp.tool()
def get_weather_forecast(location: str, days: int = 3, timezone: str | None = None) -> str:
    """Daily forecast for a place (1–7 days, including today) via Open-Meteo.

    Args:
        location: City or place name, e.g. "Tokyo".
        days: Number of daily periods to return (1–7). Default 3.
        timezone: Optional IANA timezone.
    """
    try:
        result = _client.forecast(location, days=days, timezone=timezone)
    except OpenMeteoError as exc:
        logger.warning("get_weather_forecast failed: %s", exc)
        return f"Error: {exc}"
    place = result["place"]
    return _json(
        {
            "location": _place_label(place),
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "timezone": result["timezone"],
            "forecast": result["days"],
        }
    )


@mcp.resource("weather://open-meteo/docs")
def open_meteo_docs() -> str:
    """Read-only description of the wrapped Open-Meteo endpoints."""
    return (
        "Open-Meteo MCP wraps two public REST APIs (no API key):\n"
        "- Geocoding: GET https://geocoding-api.open-meteo.com/v1/search?name={place}&count=1\n"
        "- Forecast: GET https://api.open-meteo.com/v1/forecast"
        "?latitude={lat}&longitude={lon}&current=...&daily=...&forecast_days={n}\n"
        "Tools: ping, get_current_weather, get_weather_forecast.\n"
        "Failures (timeout, HTTP errors, empty geocode, HTTP 429 after retries) "
        "are returned as strings starting with 'Error: '.\n"
    )


@mcp.prompt()
def compare_two_cities(city_a: str, city_b: str) -> str:
    """Ask the model to compare current weather in two cities using the tools."""
    return (
        f"Compare current weather in {city_a} and {city_b}. "
        "Call get_current_weather once per city, then summarize temperature, wind, and conditions. "
        "If a lookup fails, report the Error: ... text instead of guessing."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Open-Meteo MCP server (stdio or streamable HTTP).")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default=os.environ.get("MCP_TRANSPORT", "stdio"),
        help="stdio for Cursor/Inspector; http for Streamable HTTP (default: stdio or MCP_TRANSPORT).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("MCP_HTTP_HOST", "127.0.0.1"),
        help="Bind address when --transport http (default 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("MCP_HTTP_PORT", "8000")),
        help="TCP port when --transport http (default 8000).",
    )
    args = parser.parse_args()

    # Tools / resources / prompts are the same; only mcp.run(...) kwargs differ.
    # CLI uses "http"; the SDK name is "streamable-http".
    if args.transport == "http":
        run_kwargs: dict[str, Any] = {
            "transport": "streamable-http",
            "host": args.host,
            "port": args.port,
        }
        logger.info(
            "starting Open-Meteo MCP (streamable-http) at http://%s:%s/mcp",
            args.host,
            args.port,
        )
    else:
        run_kwargs = {"transport": "stdio"}
        logger.info("starting Open-Meteo MCP (stdio)")

    mcp.run(**run_kwargs)


if __name__ == "__main__":
    main()
