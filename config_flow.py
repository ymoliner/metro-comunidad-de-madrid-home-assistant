"""Config flow for CITRAM Transport."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from . import _get_stop_info
from .const import DOMAIN, CONF_STOP_CODE, CONF_STOP_NAME

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_STOP_CODE): str,
        vol.Optional(CONF_STOP_NAME): str,
    }
)


class CitramConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CITRAM Transport."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            stop_code = user_input[CONF_STOP_CODE]
            await self.async_set_unique_id(stop_code)
            self._abort_if_unique_id_configured()

            try:
                stop_data = await self.hass.async_add_executor_job(_get_stop_info, stop_code)
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                name = user_input.get(CONF_STOP_NAME) or stop_data.get("stopName", stop_code)
                return self.async_create_entry(
                    title=name,
                    data={CONF_STOP_CODE: stop_code, CONF_STOP_NAME: name},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )
