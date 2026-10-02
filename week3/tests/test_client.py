from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from week3.server.client import OpenMeteoClient, OpenMeteoError


def _response(
    status: int,
    json_body: Any | None = None,
    text: str = "",
    headers: dict | None = None,
) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    resp.headers = headers or {}
    if json_body is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_body
    return resp


def _client(mock_http: MagicMock, **kwargs: Any) -> OpenMeteoClient:
    return OpenMeteoClient(client=mock_http, sleep=lambda _: None, **kwargs)


GEOCODE_OK = {
    "results": [
        {
            "name": "Beijing",
            "country": "China",
            "admin1": "Beijing Municipality",
            "latitude": 39.9075,
            "longitude": 116.3972,
            "timezone": "Asia/Shanghai",
        }
    ]
}

CURRENT_OK = {
    "timezone": "Asia/Shanghai",
    "current": {
        "time": "2026-09-30T12:00",
        "temperature_2m": 22.5,
        "apparent_temperature": 21.0,
        "relative_humidity_2m": 40,
        "weather_code": 0,
        "wind_speed_10m": 8.2,
    },
}

DAILY_OK = {
    "timezone": "Asia/Shanghai",
    "daily": {
        "time": ["2026-09-30", "2026-10-01"],
        "temperature_2m_max": [24.0, 23.0],
        "temperature_2m_min": [14.0, 13.5],
        "precipitation_sum": [0.0, 1.2],
        "weather_code": [0, 61],
    },
}


def test_current_weather_success() -> None:
    mock_http = MagicMock()
    mock_http.get.side_effect = [_response(200, GEOCODE_OK), _response(200, CURRENT_OK)]
    result = _client(mock_http).current_weather("Beijing")
    assert result["place"]["name"] == "Beijing"
    assert result["temperature_c"] == 22.5
    assert result["conditions"] == "Clear sky"
    assert mock_http.get.call_count == 2


def test_forecast_success() -> None:
    mock_http = MagicMock()
    mock_http.get.side_effect = [_response(200, GEOCODE_OK), _response(200, DAILY_OK)]
    result = _client(mock_http).forecast("Beijing", days=2)
    assert len(result["days"]) == 2
    assert result["days"][1]["conditions"] == "Slight rain"


def test_geocode_not_found() -> None:
    mock_http = MagicMock()
    mock_http.get.return_value = _response(200, {"results": []})
    with pytest.raises(OpenMeteoError, match="no matching place"):
        _client(mock_http).geocode("NotARealCityXYZ")


def test_empty_location() -> None:
    mock_http = MagicMock()
    with pytest.raises(OpenMeteoError, match="location is required"):
        _client(mock_http).geocode("   ")
    mock_http.get.assert_not_called()


def test_timeout() -> None:
    mock_http = MagicMock()
    mock_http.get.side_effect = httpx.TimeoutException("slow")
    with pytest.raises(OpenMeteoError, match="timed out"):
        _client(mock_http).geocode("Beijing")


def test_http_error() -> None:
    mock_http = MagicMock()
    mock_http.get.return_value = _response(500, None, text="upstream down")
    with pytest.raises(OpenMeteoError, match="HTTP 500"):
        _client(mock_http).geocode("Beijing")


def test_rate_limit_then_success() -> None:
    mock_http = MagicMock()
    limited = _response(429, None, text="slow down", headers={"Retry-After": "0.1"})
    mock_http.get.side_effect = [limited, _response(200, GEOCODE_OK)]
    place = _client(mock_http).geocode("Beijing")
    assert place["latitude"] == 39.9075
    assert mock_http.get.call_count == 2


def test_rate_limit_exhausted() -> None:
    mock_http = MagicMock()
    mock_http.get.return_value = _response(429, None, text="slow down")
    with pytest.raises(OpenMeteoError, match="429"):
        _client(mock_http, max_retries=2).geocode("Beijing")
    assert mock_http.get.call_count == 3
