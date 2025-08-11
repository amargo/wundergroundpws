"""The WundergroundPWS data coordinator."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

import aiohttp
from asyncio import timeout

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .base_coordinator import BaseWundergroundPWSCoordinator, MIN_TIME_BETWEEN_UPDATES, _RESOURCECURRENT, _RESOURCEFORECAST, _RESOURCESHARED
from .const import (
    FIELD_OBSERVATIONS,
    FIELD_LONGITUDE, 
    FIELD_LATITUDE,
    DEFAULT_TIMEOUT,
    FIELD_CONDITION_HUMIDITY,
    FIELD_CONDITION_WINDDIR
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class WundergroundPWSUpdateCoordinatorConfig:
    """Class representing coordinator configuration."""

    api_key: str
    pws_id: str
    numeric_precision: str
    unit_system_api: str
    unit_system: str
    lang: str
    calendarday: bool
    latitude: str
    longitude: str
    forecast_enable: bool
    update_interval = MIN_TIME_BETWEEN_UPDATES
    tranfile: str


class WundergroundPWSUpdateCoordinator(BaseWundergroundPWSCoordinator):
    """The WundergroundPWS update coordinator."""

    def __init__(
            self, hass: HomeAssistant, config: WundergroundPWSUpdateCoordinatorConfig
    ) -> None:
        """Initialize."""
        self._pws_id = config.pws_id
        self._numeric_precision = config.numeric_precision
        self.unit_system = config.unit_system
        self._latitude = config.latitude
        self._longitude = config.longitude
        self.forecast_enable = config.forecast_enable
        self._tranfile = config.tranfile

        super().__init__(
            hass=hass,
            name="WundergroundPWSUpdateCoordinator",
            api_key=config.api_key,
            unit_system_api=config.unit_system_api,
            lang=config.lang,
            calendarday=config.calendarday,
            update_interval=config.update_interval,
        )
        
        # Initialize session after super().__init__() so self.hass is available
        self._session = async_get_clientsession(self.hass)



    @property
    def pws_id(self):
        """Return the location used for data."""
        return self._pws_id

    async def _async_update_data(self) -> dict[str, Any]:
        return await self.get_weather()

    async def get_weather(self):
        """Get weather data."""
        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        try:
            async with timeout(DEFAULT_TIMEOUT):
                url = self._build_url(_RESOURCECURRENT)
                response = await self._session.get(url, headers=headers)
                result_current = await response.json()
                if result_current is None:
                    raise ValueError('NO CURRENT RESULT')
                self._check_errors(url, result_current)

                if not self._longitude:
                    self._longitude = (result_current[FIELD_OBSERVATIONS][0][FIELD_LONGITUDE])
                if not self._latitude:
                    self._latitude = (result_current[FIELD_OBSERVATIONS][0][FIELD_LATITUDE])

            async with timeout(DEFAULT_TIMEOUT):
                url = self._build_url(_RESOURCEFORECAST)
                response = await self._session.get(url, headers=headers)
                result_forecast = await response.json()

                if result_forecast is None:
                    raise ValueError('NO FORECAST RESULT')
                self._check_errors(url, result_forecast)

            result = {**result_current, **result_forecast}

            self.data = result

            return result

        except ValueError as err:
            _LOGGER.error("Check WUnderground API %s", err.args)
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error fetching WUnderground data: %s", repr(err))
        # _LOGGER.debug(f'WUnderground data {self.data}')

    def _build_url(self, baseurl):
        if baseurl == _RESOURCECURRENT:
            if self._numeric_precision != 'none':
                baseurl += '&numericPrecision={numericPrecision}'
        elif baseurl == _RESOURCEFORECAST:
            baseurl += '&language={language}'

        baseurl += _RESOURCESHARED

        return baseurl.format(
            apiKey=self._api_key,
            language=self._lang,
            latitude=self._latitude,
            longitude=self._longitude,
            numericPrecision=self._numeric_precision,
            stationId=self._pws_id,
            units=self._unit_system_api
        )

    def _check_errors(self, url: str, response: dict):
        # _LOGGER.debug(f'Checking errors from {url} in {response}')
        if 'errors' not in response:
            return
        if errors := response['errors']:
            raise ValueError(
                f'Error from {url}: '
                '; '.join([
                    e['message']
                    for e in errors
                ])
            )

    def get_condition(self, field):
        """Override base method to handle unit system specific fields."""
        if field in [
            FIELD_CONDITION_HUMIDITY,
            FIELD_CONDITION_WINDDIR,
        ]:
            # Those fields are unit-less
            return self.data[FIELD_OBSERVATIONS][0][field] or 0
        return self.data[FIELD_OBSERVATIONS][0][self.unit_system][field]


class InvalidApiKey(HomeAssistantError):
    """Error to indicate there is an invalid api key."""


class InvalidStationId(HomeAssistantError):
    """Error to indicate there is an invalid api key."""
