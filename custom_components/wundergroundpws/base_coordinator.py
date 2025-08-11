"""Base coordinator for WundergroundPWS with common functionality."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, ClassVar
from datetime import timedelta

import aiohttp
from asyncio import timeout

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util.unit_system import METRIC_SYSTEM
from homeassistant.const import (
    PERCENTAGE, UnitOfPressure, UnitOfTemperature, UnitOfLength, UnitOfSpeed, UnitOfVolumetricFlux)

from .const import (
    ICON_CONDITION_MAP,
    FIELD_OBSERVATIONS,
    FIELD_CONDITION_HUMIDITY,
    FIELD_CONDITION_WINDDIR,
    FIELD_DAYPART,
    FIELD_FORECAST_VALIDTIMEUTC,
    FIELD_FORECAST_TEMPERATUREMAX,
    FIELD_FORECAST_TEMPERATUREMIN,
    FIELD_FORECAST_CALENDARDAYTEMPERATUREMAX,
    FIELD_FORECAST_CALENDARDAYTEMPERATUREMIN,
    FIELD_FORECAST_ICONCODE,
    FIELD_FORECAST_QPF,
    FIELD_FORECAST_PRECIPCHANCE,
    FIELD_FORECAST_WINDSPEED,
    FIELD_FORECAST_WINDDIRECTION,
    DEFAULT_TIMEOUT,
    TEMPUNIT,
    LENGTHUNIT,
    SPEEDUNIT,
    PRESSUREUNIT,
)

_LOGGER = logging.getLogger(__name__)

_RESOURCESHARED = '&format=json&apiKey={apiKey}&units={units}'
_RESOURCECURRENT = ('https://api.weather.com/v2/pws/observations/current'
                    '?stationId={stationId}')
_RESOURCEFORECAST = ('https://api.weather.com/v3/wx/forecast/daily/5day'
                     '?geocode={latitude},{longitude}')

MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)


class BaseWundergroundPWSCoordinator(DataUpdateCoordinator):
    """Base coordinator for WundergroundPWS integrations."""
    
    # Shared icon condition mapping
    icon_condition_map: ClassVar[dict] = ICON_CONDITION_MAP
    
    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        api_key: str,
        unit_system_api: str,
        lang: str,
        calendarday: bool,
        update_interval=MIN_TIME_BETWEEN_UPDATES,
        **kwargs
    ) -> None:
        """Initialize base coordinator."""
        self._hass = hass
        self._api_key = api_key
        self._unit_system_api = unit_system_api
        self._lang = lang
        self._calendarday = calendarday
        self._features = set()
        self._session = async_get_clientsession(hass)
        
        # Set up unit system mapping similar to coordinator.py
        self.units_of_measurement = {
            TEMPUNIT: UnitOfTemperature.CELSIUS if unit_system_api == 'm' else UnitOfTemperature.FAHRENHEIT,
            LENGTHUNIT: UnitOfLength.MILLIMETERS if unit_system_api == 'm' else UnitOfLength.INCHES,
            SPEEDUNIT: UnitOfSpeed.KILOMETERS_PER_HOUR if unit_system_api == 'm' else UnitOfSpeed.MILES_PER_HOUR,
            PRESSUREUNIT: UnitOfPressure.MBAR if unit_system_api == 'm' else UnitOfPressure.INHG,
        }
        
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=update_interval,
        )
    
    @property
    def is_metric(self) -> bool:
        """Determine if this is the metric unit system."""
        return self._hass.config.units is METRIC_SYSTEM
    
    def request_feature(self, feature):
        """Register feature to be fetched from WU API."""
        self._features.add(feature)
    
    def get_condition(self, field):
        """Get condition from the active station data."""
        if not self.data:
            return None
        
        if field in [
            FIELD_CONDITION_HUMIDITY,
            FIELD_CONDITION_WINDDIR,
        ]:
            # Those fields are unit-less
            return self.data[FIELD_OBSERVATIONS][0].get(field)
        
        return self.data[FIELD_OBSERVATIONS][0].get(field)
    
    def get_forecast(self, field, period=0):
        """Get forecast data from the active station data."""
        try:
            if not self.data:
                return None
                
            if field in [
                FIELD_FORECAST_TEMPERATUREMAX,
                FIELD_FORECAST_TEMPERATUREMIN,
                FIELD_FORECAST_CALENDARDAYTEMPERATUREMAX,
                FIELD_FORECAST_CALENDARDAYTEMPERATUREMIN,
                FIELD_FORECAST_VALIDTIMEUTC,
            ]:
                # Those fields exist per-day, rather than per dayPart, so the period is halved
                return self.data[field][int(period / 2)]
            return self.data[FIELD_DAYPART][0][field][period]
        except (IndexError, TypeError, KeyError):
            return None

    @classmethod
    def _iconcode_to_condition(cls, icon_code):
        """Convert icon code to condition."""
        if icon_code is None:
            return None
            
        for condition, iconcodes in cls.icon_condition_map.items():
            if icon_code in iconcodes:
                return condition
        _LOGGER.warning(f'Unmapped iconCode from TWC Api. (44 is Not Available (N/A)) "{icon_code}". ')
        return None
    
    def _check_errors(self, url: str, response: dict):
        """Check for API errors."""
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
    
    def _build_url(self, baseurl, station_id, latitude=None, longitude=None):
        """Build URL for API request - works for both single and multi-station."""
        if baseurl == _RESOURCECURRENT:
            if hasattr(self, '_numeric_precision') and self._numeric_precision != 'none':
                baseurl += '&numericPrecision={numericPrecision}'
        elif baseurl == _RESOURCEFORECAST:
            baseurl += '&language={language}'

        baseurl += _RESOURCESHARED

        return baseurl.format(
            apiKey=self._api_key,
            language=self._lang,
            latitude=latitude or getattr(self, '_latitude', ''),
            longitude=longitude or getattr(self, '_longitude', ''),
            numericPrecision=getattr(self, '_numeric_precision', 'none'),
            stationId=station_id,
            units=self._unit_system_api
        )
    
    async def get_weather_data(self, station_id, latitude=None, longitude=None):
        """Get weather data for a station - common method for both single and multi-station."""
        try:
            # Fetch current conditions
            current_url = self._build_url(_RESOURCECURRENT, station_id, latitude, longitude)
            async with timeout(DEFAULT_TIMEOUT):
                async with self._session.get(current_url) as response:
                    if response.status != 200:
                        raise ValueError(f'HTTP {response.status}: {await response.text()}')
                    
                    result_current = await response.json()

                    if result_current is None:
                        raise ValueError('NO CURRENT RESULT - API returned null')
                    
                    self._check_errors(current_url, result_current)

            # Fetch forecast data if enabled
            result_forecast = {}
            if getattr(self, 'forecast_enable', True):
                forecast_url = self._build_url(_RESOURCEFORECAST, station_id, latitude, longitude)
                async with timeout(DEFAULT_TIMEOUT):
                    async with self._session.get(forecast_url) as response:
                        if response.status != 200:
                            raise ValueError(f'HTTP {response.status}: {await response.text()}')
                        
                        result_forecast = await response.json()

                        if result_forecast is None:
                            raise ValueError('NO FORECAST RESULT - API returned null')
                        
                        # Check if forecast data exists
                        if 'daypart' not in result_forecast or not result_forecast['daypart']:
                            _LOGGER.warning(f"Station {station_id}: No forecast daypart data available")
                        
                        self._check_errors(forecast_url, result_forecast)

            # Combine results
            result = {**result_current, **result_forecast}
            return result

        except Exception as err:
            _LOGGER.error(f"Error fetching data from station {station_id}: {err}")
            # Log the actual URLs for debugging
            try:
                current_url = self._build_url(_RESOURCECURRENT, station_id, latitude, longitude)
                forecast_url = self._build_url(_RESOURCEFORECAST, station_id, latitude, longitude)
                _LOGGER.debug(f"Current URL: {current_url}")
                _LOGGER.debug(f"Forecast URL: {forecast_url}")
            except Exception as url_err:
                _LOGGER.error(f"Error building URLs for {station_id}: {url_err}")
            return None
    
    # This method will be overridden by subclasses for specific behavior
    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API - base implementation."""
        # This base implementation should not be called directly
        # Subclasses should override this method
        raise NotImplementedError("Subclasses must implement _async_update_data")
