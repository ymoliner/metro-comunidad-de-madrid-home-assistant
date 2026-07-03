"""Sensor platform for CITRAM Transport."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import CitramCoordinator
from .const import DOMAIN, CONF_STOP_CODE, CONF_STOP_NAME, ATTR_ARRIVALS, MAX_ARRIVALS_SHOWN


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: CitramCoordinator = hass.data[DOMAIN][entry.entry_id]
    stop_name = entry.data.get(CONF_STOP_NAME, entry.data[CONF_STOP_CODE])
    async_add_entities([CitramNextArrivalSensor(coordinator, entry, stop_name)])


class CitramNextArrivalSensor(CoordinatorEntity[CitramCoordinator], SensorEntity):
    """Shows the next arrival time; full list as an attribute."""

    _attr_icon = "mdi:bus-clock"

    def __init__(self, coordinator: CitramCoordinator, entry: ConfigEntry, stop_name: str) -> None:
        super().__init__(coordinator)
        self._attr_name = f"{stop_name} Next Arrival"
        self._attr_unique_id = f"{entry.entry_id}_next_arrival"

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or []
        if not data:
            return None
        first = data[0]
        return f"{first['line']} -> {first['destination']} ({first['time']})"

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or []
        return {ATTR_ARRIVALS: data[:MAX_ARRIVALS_SHOWN]}
