"""
Support for WUndergroundPWS weather service.
For more details about this platform, please refer to the documentation at
https://github.com/cytech/Home-Assistant-wundergroundpws/tree/v2.X.X
"""

from . import WundergroundPWSUpdateCoordinator
from .multi_station_coordinator import MultiStationUpdateCoordinator
from .multi_station_weather import MultiStationWeather
from .base_weather import BaseWundergroundPWSWeatherEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.util import dt as dt_util
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
    FIELD_FORECAST_ICONCODE, CONF_PWS_ID,
)

# Multi-station constants
CONF_INTEGRATION_TYPE = "integration_type"
CONF_GROUP_NAME = "group_name"

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


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add weather entity."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    
    # Check if this is a multi-station or single station setup
    integration_type = entry.data.get(CONF_INTEGRATION_TYPE, "single")
    
    if integration_type == "multi":
        # Multi-station setup
        group_name: str = entry.data[CONF_GROUP_NAME]
        async_add_entities([MultiStationWeather(group_name, coordinator)])
    else:
        # Single station setup
        pws_id: str = entry.data[CONF_PWS_ID]
        async_add_entities([WUWeather(pws_id, coordinator)])


class WUWeather(BaseWundergroundPWSWeatherEntity):

    def __init__(
            self,
            pws_id: str,
            coordinator: WundergroundPWSUpdateCoordinator
    ):
        super().__init__(coordinator, None)
        """Initialize the sensor."""
        self._attr_name = pws_id
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, f"{self._attr_name}", hass=coordinator.hass
        )
        self._attr_unique_id = f"{coordinator.pws_id},{WEATHER_DOMAIN}".lower()

    @property
    def supported_features(self) -> int | None:
        """Flag supported features."""
        # return WeatherEntityFeature.FORECAST_HOURLY if self.coordinator.config.hourly_forecast else WeatherEntityFeature.FORECAST_DAILY
        return WeatherEntityFeature.FORECAST_DAILY

    @property
    def ozone(self) -> float:
        """Return the ozone level."""
        return self._attr_ozone

    # @property
    # def native_visibility(self) -> float:
    #     """Return the visibility in native units."""
    #     return self._attr_visibility
    #
    # @property
    # def native_visibility_unit(self) -> str:
    #     """Return the native unit of measurement for visibility."""
    #     return self._attr_visibility_unit




    def _forecast(self) -> list[Forecast]:
        """Return the forecast in native units."""
        return self._forecast_legacy()

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast_new()
