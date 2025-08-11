"""Multi-station coordinator for WundergroundPWS with fallback support."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

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
class StationConfig:
    """Configuration for a single weather station."""
    pws_id: str
    priority: int  # Lower number = higher priority
    name: str


@dataclass
class MultiStationCoordinatorConfig:
    """Class representing multi-station coordinator configuration."""
    
    api_key: str
    stations: List[StationConfig]
    group_name: str  # e.g., "velence"
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
    max_station_age_minutes: int = 30  # Max age before considering station stale


class MultiStationUpdateCoordinator(BaseWundergroundPWSCoordinator):
    """Multi-station WundergroundPWS update coordinator with fallback support."""

    def __init__(
            self, hass: HomeAssistant, config: MultiStationCoordinatorConfig
    ) -> None:
        """Initialize."""
        self._stations = sorted(config.stations, key=lambda x: x.priority)
        self._group_name = config.group_name
        self._numeric_precision = config.numeric_precision
        self.unit_system = config.unit_system
        self._latitude = config.latitude
        self._longitude = config.longitude
        self.forecast_enable = config.forecast_enable
        self._max_station_age_minutes = config.max_station_age_minutes
        self._session = async_get_clientsession(hass)
        self._tranfile = config.tranfile
        self._station_data = {}  # Store data from each station
        self._active_station = None  # Currently active station

        super().__init__(
            hass=hass,
            name="MultiStationUpdateCoordinator",
            api_key=config.api_key,
            unit_system_api=config.unit_system_api,
            lang=config.lang,
            calendarday=config.calendarday,
            update_interval=config.update_interval,
        )



    @property
    def group_name(self):
        """Return the group name."""
        return self._group_name

    @property
    def active_station(self):
        """Return the currently active station."""
        return self._active_station

    @property
    def station_status(self):
        """Return status of all stations."""
        return {
            station.pws_id: {
                'name': station.name,
                'priority': station.priority,
                'active': station.pws_id == self._active_station.pws_id if self._active_station else False,
                'last_update': self._station_data.get(station.pws_id, {}).get('last_update'),
                'status': 'online' if station.pws_id in self._station_data else 'offline'
            }
            for station in self._stations
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from all stations and select the best one."""
        return await self.get_weather()

    async def get_weather(self):
        """Get weather data with fallback logic."""
        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        
        successful_stations = []
        
        # Try to fetch data from all stations
        for station in self._stations:
            try:
                station_data = await self._fetch_station_data(station, headers)
                if station_data:
                    successful_stations.append((station, station_data))
                    _LOGGER.debug(f"Successfully fetched data from station {station.pws_id}")
            except Exception as err:
                _LOGGER.warning(f"Failed to fetch data from station {station.pws_id}: {err}")
                # Remove failed station from cache
                self._station_data.pop(station.pws_id, None)

        if not successful_stations:
            _LOGGER.error("No stations available - all stations failed")
            return None

        # Select the best station (highest priority that's working)
        selected_station, selected_data = successful_stations[0]
        self._active_station = selected_station
        
        # Update station data cache
        for station, data in successful_stations:
            self._station_data[station.pws_id] = {
                'data': data,
                'last_update': self._hass.loop.time()
            }

        _LOGGER.info(f"Using data from station {selected_station.pws_id} ({selected_station.name})")
        
        self.data = selected_data
        return selected_data

    async def _fetch_station_data(self, station: StationConfig, headers: dict) -> Optional[dict]:
        """Fetch data from a single station."""
        try:
            # Fetch current conditions
            async with timeout(DEFAULT_TIMEOUT):
                url = self._build_url(_RESOURCECURRENT, station.pws_id)
                response = await self._session.get(url, headers=headers)
                
                # Check HTTP status first
                if response.status != 200:
                    raise ValueError(f'HTTP {response.status}: {await response.text()}')
                
                result_current = await response.json()
                
                if result_current is None:
                    raise ValueError('NO CURRENT RESULT - API returned null')
                
                # Check if observations exist
                if FIELD_OBSERVATIONS not in result_current or not result_current[FIELD_OBSERVATIONS]:
                    raise ValueError('NO OBSERVATIONS DATA - Station may be offline')
                
                self._check_errors(url, result_current)

                # Get coordinates from the station if not set
                if not self._longitude:
                    self._longitude = (result_current[FIELD_OBSERVATIONS][0][FIELD_LONGITUDE])
                if not self._latitude:
                    self._latitude = (result_current[FIELD_OBSERVATIONS][0][FIELD_LATITUDE])

            # Fetch forecast
            async with timeout(DEFAULT_TIMEOUT):
                url = self._build_url(_RESOURCEFORECAST, station.pws_id)
                response = await self._session.get(url, headers=headers)
                
                # Check HTTP status first
                if response.status != 200:
                    raise ValueError(f'HTTP {response.status}: {await response.text()}')
                
                result_forecast = await response.json()

                if result_forecast is None:
                    raise ValueError('NO FORECAST RESULT - API returned null')
                
                # Check if forecast data exists
                if 'daypart' not in result_forecast or not result_forecast['daypart']:
                    _LOGGER.warning(f"Station {station.pws_id}: No forecast daypart data available")
                
                self._check_errors(url, result_forecast)

            # Combine results
            result = {**result_current, **result_forecast}
            return result

        except Exception as err:
            _LOGGER.error(f"Error fetching data from station {station.pws_id}: {err}")
            # Log the actual URL for debugging
            try:
                current_url = self._build_url(_RESOURCECURRENT, station.pws_id)
                forecast_url = self._build_url(_RESOURCEFORECAST, station.pws_id)
                _LOGGER.debug(f"Current URL: {current_url}")
                _LOGGER.debug(f"Forecast URL: {forecast_url}")
            except Exception as url_err:
                _LOGGER.error(f"Error building URLs for {station.pws_id}: {url_err}")
            return None

    def _build_url(self, baseurl, station_id):
        """Build URL for API request."""
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
            stationId=station_id,
            units=self._unit_system_api
        )

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

    def request_feature(self, feature):
        """Register feature to be fetched from WU API."""
        self._features.add(feature)

    def get_condition(self, field):
        """Get condition from the active station data."""
        if not self.data or FIELD_OBSERVATIONS not in self.data:
            return None
            
        observations = self.data[FIELD_OBSERVATIONS]
        if not observations or len(observations) == 0:
            return None
            
        observation = observations[0]
        
        # Unit-less fields (directly from observation)
        unit_less_fields = [
            'humidity',           # FIELD_CONDITION_HUMIDITY
            'winddir',           # FIELD_CONDITION_WINDDIR  
            'solarRadiation',    # solar radiation
            'uv',                # UV index
            'stationID',         # station ID
            'neighborhood',      # neighborhood name
            'obsTimeLocal',      # local observation time
            'obsTimeUtc',        # UTC observation time
            'softwareType',      # software type
            'country',           # country
            'lon',               # longitude
            'lat',               # latitude
            'realtimeFrequency', # realtime frequency
            'epoch',             # epoch time
            'qcStatus',          # QC status
            'windDirectionCardinal', # wind direction cardinal
        ]
        
        if field in unit_less_fields:
            return observation.get(field)
        
        # Metric/Imperial fields (from metric/imperial sub-object)
        metric_data = observation.get(self.unit_system, {})
        if metric_data and field in metric_data:
            return metric_data.get(field)
            
        # Fallback: try to get from observation directly
        return observation.get(field)
