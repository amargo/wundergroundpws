"""
Multi-station weather entity for WUndergroundPWS with fallback support.
"""

from . import WundergroundPWSUpdateCoordinator
from .multi_station_coordinator import MultiStationUpdateCoordinator
from .base_weather import BaseWundergroundPWSWeatherEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
from datetime import timedelta
from .const import (
    DOMAIN,
    TEMPUNIT,
    LENGTHUNIT,
    SPEEDUNIT,
    PRESSUREUNIT,
    FIELD_CONDITION_HUMIDITY,
    FIELD_CONDITION_PRESSURE,
    FIELD_CONDITION_TEMP,
    FIELD_CONDITION_WINDDIR,
    FIELD_CONDITION_WINDSPEED,
    FIELD_FORECAST_VALIDTIMEUTC,
    FIELD_FORECAST_PRECIPCHANCE,
    FIELD_FORECAST_QPF,
    FIELD_FORECAST_TEMPERATUREMAX,
    FIELD_FORECAST_TEMPERATUREMIN,
    FIELD_FORECAST_CALENDARDAYTEMPERATUREMAX,
    FIELD_FORECAST_CALENDARDAYTEMPERATUREMIN,
    FIELD_FORECAST_WINDDIRECTIONCARDINAL,
    FIELD_FORECAST_WINDSPEED,
    FIELD_FORECAST_ICONCODE,
)

import logging

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
    WeatherEntity,
    WeatherEntityFeature,
    Forecast,
    DOMAIN as WEATHER_DOMAIN
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback

_LOGGER = logging.getLogger(__name__)

ENTITY_ID_FORMAT = WEATHER_DOMAIN + ".{}"


class MultiStationWeather(BaseWundergroundPWSWeatherEntity):
    """Multi-station weather entity with fallback support."""

    def __init__(
            self,
            group_name: str,
            coordinator: MultiStationUpdateCoordinator
    ):
        super().__init__(coordinator, None)
        """Initialize the multi-station weather entity."""
        self._attr_name = group_name
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, f"{self._attr_name}", hass=coordinator.hass
        )
        self._attr_unique_id = f"{group_name}_multi_station_{WEATHER_DOMAIN}".lower()





    @property
    def attribution(self) -> str:
        """Return the attribution."""
        active_station = self.coordinator.active_station
        if active_station:
            return f"Data provided by Weather Underground PWS {active_station.pws_id} ({active_station.name})"
        return "Data provided by Weather Underground PWS"

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional state attributes."""
        attrs = super().extra_state_attributes or {}
        
        # Add station status information
        attrs.update({
            "active_station": self.coordinator.active_station.pws_id if self.coordinator.active_station else None,
            "active_station_name": self.coordinator.active_station.name if self.coordinator.active_station else None,
            "station_status": self.coordinator.station_status,
            "group_name": self.coordinator.group_name,
        })
        
        return attrs

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast_new()
