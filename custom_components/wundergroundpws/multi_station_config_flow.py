"""Config flow for Multi-Station WundergroundPWS integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_LANG,
    CONF_NUMERIC_PRECISION,
    CONF_PWS_ID,
    DOMAIN,
    CONF_CALENDARDAYTEMPERATURE,
    CONF_FORECAST_SENSORS,
)
from .multi_station_coordinator import StationConfig

_LOGGER = logging.getLogger(__name__)

CONF_GROUP_NAME = "group_name"
CONF_STATIONS = "stations"
CONF_STATION_NAME = "station_name"
CONF_STATION_PRIORITY = "station_priority"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_GROUP_NAME): str,
        vol.Optional(CONF_LATITUDE): cv.latitude,
        vol.Optional(CONF_LONGITUDE): cv.longitude,
    }
)

STEP_STATION_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PWS_ID): str,
        vol.Required(CONF_STATION_NAME): str,
        vol.Required(CONF_STATION_PRIORITY, default=1): vol.All(int, vol.Range(min=1, max=10)),
    }
)


class MultiStationConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Multi-Station WundergroundPWS."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._api_key = None
        self._group_name = None
        self._latitude = None
        self._longitude = None
        self._stations = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._api_key = user_input[CONF_API_KEY]
            self._group_name = user_input[CONF_GROUP_NAME]
            self._latitude = user_input.get(CONF_LATITUDE)
            self._longitude = user_input.get(CONF_LONGITUDE)

            # Check if group name already exists
            await self.async_set_unique_id(f"multi_station_{self._group_name}")
            self._abort_if_unique_id_configured()

            return await self.async_step_add_station()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_add_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a weather station."""
        errors = {}

        if user_input is not None:
            pws_id = user_input[CONF_PWS_ID]
            station_name = user_input[CONF_STATION_NAME]
            priority = user_input[CONF_STATION_PRIORITY]

            # Check if station ID already exists in this group
            if any(station.pws_id == pws_id for station in self._stations):
                errors["base"] = "station_already_exists"
            else:
                self._stations.append(StationConfig(
                    pws_id=pws_id,
                    priority=priority,
                    name=station_name
                ))

                # Ask if user wants to add more stations
                return self.async_show_menu(
                    step_id="station_menu",
                    menu_options=["add_another_station", "finish_setup"]
                )

        return self.async_show_form(
            step_id="add_station",
            data_schema=STEP_STATION_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "group_name": self._group_name,
                "station_count": len(self._stations),
            },
        )

    async def async_step_station_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle station menu selection."""
        return self.async_show_menu(
            step_id="station_menu",
            menu_options=["add_another_station", "finish_setup"]
        )

    async def async_step_add_another_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add another station."""
        return await self.async_step_add_station()

    async def async_step_finish_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Finish the setup."""
        if len(self._stations) == 0:
            return self.async_abort(reason="no_stations")

        # Create the config entry
        return self.async_create_entry(
            title=f"Multi-Station {self._group_name}",
            data={
                CONF_API_KEY: self._api_key,
                CONF_GROUP_NAME: self._group_name,
                CONF_STATIONS: [
                    {
                        CONF_PWS_ID: station.pws_id,
                        CONF_STATION_NAME: station.name,
                        CONF_STATION_PRIORITY: station.priority,
                    }
                    for station in self._stations
                ],
            },
            options={
                CONF_LATITUDE: self._latitude,
                CONF_LONGITUDE: self._longitude,
                CONF_LANG: "en-US",
                CONF_NUMERIC_PRECISION: "none",
                CONF_CALENDARDAYTEMPERATURE: False,
                CONF_FORECAST_SENSORS: False,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> MultiStationOptionsFlow:
        """Create the options flow."""
        return MultiStationOptionsFlow(config_entry)


class MultiStationOptionsFlow(config_entries.OptionsFlow):
    """Multi-Station WundergroundPWS options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_LATITUDE,
                        default=self.config_entry.options.get(CONF_LATITUDE),
                    ): cv.latitude,
                    vol.Optional(
                        CONF_LONGITUDE,
                        default=self.config_entry.options.get(CONF_LONGITUDE),
                    ): cv.longitude,
                    vol.Optional(
                        CONF_LANG,
                        default=self.config_entry.options.get(CONF_LANG, "en-US"),
                    ): str,
                    vol.Optional(
                        CONF_NUMERIC_PRECISION,
                        default=self.config_entry.options.get(CONF_NUMERIC_PRECISION, "none"),
                    ): vol.In(["none", "decimal"]),
                    vol.Optional(
                        CONF_CALENDARDAYTEMPERATURE,
                        default=self.config_entry.options.get(CONF_CALENDARDAYTEMPERATURE, False),
                    ): bool,
                    vol.Optional(
                        CONF_FORECAST_SENSORS,
                        default=self.config_entry.options.get(CONF_FORECAST_SENSORS, False),
                    ): bool,
                }
            ),
        )
