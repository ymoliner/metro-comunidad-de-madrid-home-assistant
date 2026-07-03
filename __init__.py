"""The CITRAM Transport integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

import requests

from .const import DOMAIN, CONF_STOP_CODE, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

CRTM_BASE = "https://www.crtm.es/widgets/api"
TIMEOUT = 10


def _get_stop_info(stop_code: str) -> dict:
    resp = requests.get(f"{CRTM_BASE}/GetStops.php", params={"codStop": stop_code}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["stops"]["Stop"]


def _get_line_info(cod_line: str) -> dict:
    resp = requests.get(f"{CRTM_BASE}/GetLinesInformation.php", params={"codLine": cod_line}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()["lines"]["LineInformation"]


def _get_stop_times(cod_stop: str, stop_type: str, cod_itinerary: str) -> dict:
    resp = requests.get(
        f"{CRTM_BASE}/GetStopsTimes.php",
        params={
            "codStop": cod_stop,
            "type": stop_type,
            "orderBy": 2,
            "stopTimesByIti": cod_itinerary,
        },
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _fetch_arrivals(stop_code: str) -> list[dict]:
    """Blocking call: same logic as the original script, but talking to CRTM directly."""
    info = _get_stop_info(stop_code)
    lines = info["codLines"]["Line"]
    if isinstance(lines, str):
        lines = [lines]

    arrivals: dict[tuple, bool] = {}
    for cod_line in lines:
        line = _get_line_info(cod_line)
        itineraries = line["itinerary"]["Itinerary"]
        if isinstance(itineraries, dict):
            itineraries = [itineraries]

        for itinerary in itineraries:
            times = _get_stop_times(
                info["codStop"],
                info["stopType"],
                itinerary["codItinerary"],
            )
            time_entries = times.get("stopTimes", {}).get("times", {}).get("Time", [])
            if isinstance(time_entries, dict):
                time_entries = [time_entries]

            for t in time_entries:
                key = (t["line"]["shortDescription"], t["destination"], t["time"])
                arrivals[key] = True

    result = [
        {"line": line_name, "destination": destination, "time": time}
        for (line_name, destination, time) in sorted(arrivals, key=lambda k: k[2])
    ]
    return result


class CitramCoordinator(DataUpdateCoordinator):
    """Fetches arrival data for a single stop code."""

    def __init__(self, hass: HomeAssistant, stop_code: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{stop_code}",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.stop_code = stop_code

    async def _async_update_data(self) -> list[dict]:
        try:
            return await self.hass.async_add_executor_job(_fetch_arrivals, self.stop_code)
        except Exception as err:  # noqa: BLE001 - library raises plain Exceptions/KeyErrors
            raise UpdateFailed(f"Error fetching CITRAM data for {self.stop_code}: {err}") from err


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CITRAM Transport from a config entry."""
    stop_code = entry.data[CONF_STOP_CODE]
    coordinator = CitramCoordinator(hass, stop_code)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
