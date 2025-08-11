"""Base weather entity for WundergroundPWS integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.weather import WeatherEntity, Forecast, WeatherEntityFeature
from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRECIPITATION_PROBABILITY,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_WIND_BEARING,
    ATTR_FORECAST_WIND_SPEED,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    TEMPUNIT,
    LENGTHUNIT,
    SPEEDUNIT,
    PRESSUREUNIT,
    FIELD_CONDITION_HUMIDITY,
    FIELD_CONDITION_PRESSURE,
    FIELD_CONDITION_TEMP,
    FIELD_CONDITION_WINDDIR,
    FIELD_CONDITION_WINDSPEED,
    FIELD_FORECAST_ICONCODE,
    FIELD_FORECAST_QPF,
    FIELD_FORECAST_PRECIPCHANCE,
    FIELD_FORECAST_CALENDARDAYTEMPERATUREMAX,
    FIELD_FORECAST_CALENDARDAYTEMPERATUREMIN,
    FIELD_FORECAST_TEMPERATUREMAX,
    FIELD_FORECAST_TEMPERATUREMIN,
    FIELD_FORECAST_VALIDTIMEUTC,
    FIELD_FORECAST_WINDSPEED,
    FIELD_FORECAST_WINDDIRECTION,
    FIELD_FORECAST_WINDDIRECTIONCARDINAL,
)

_LOGGER = logging.getLogger(__name__)


class BaseWundergroundPWSWeatherEntity(CoordinatorEntity, WeatherEntity):
    """Base weather entity for WundergroundPWS integration."""

    def __init__(self, coordinator, config_entry):
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_attribution = "Data provided by Weather Underground"

    @property
    def supported_features(self) -> int | None:
        """Flag supported features."""
        return WeatherEntityFeature.FORECAST_DAILY

    @property
    def native_temperature(self) -> float:
        """Return the platform temperature in native units."""
        return self.coordinator.get_condition(FIELD_CONDITION_TEMP)

    @property
    def native_temperature_unit(self) -> str:
        """Return the native unit of measurement for temperature."""
        return self.coordinator.units_of_measurement[TEMPUNIT]

    @property
    def native_pressure(self) -> float:
        """Return the pressure in native units."""
        return self.coordinator.get_condition(FIELD_CONDITION_PRESSURE)

    @property
    def native_pressure_unit(self) -> str:
        """Return the native unit of measurement for pressure."""
        return self.coordinator.units_of_measurement[PRESSUREUNIT]

    @property
    def humidity(self) -> int:
        """Return the humidity in native units."""
        return self.coordinator.get_condition(FIELD_CONDITION_HUMIDITY)

    @property
    def native_wind_speed(self) -> float:
        """Return the wind speed in native units."""
        return self.coordinator.get_condition(FIELD_CONDITION_WINDSPEED)

    @property
    def native_wind_speed_unit(self) -> str:
        """Return the native unit of measurement for wind speed."""
        return self.coordinator.units_of_measurement[SPEEDUNIT]

    @property
    def wind_bearing(self) -> int:
        """Return the wind bearing in degrees."""
        return self.coordinator.get_condition(FIELD_CONDITION_WINDDIR)

    @property
    def native_precipitation_unit(self) -> str:
        """Return the native unit of measurement for accumulated precipitation."""
        return self.coordinator.units_of_measurement[LENGTHUNIT]

    @property
    def condition(self):
        """Return the current condition."""
        try:
            # Try to get condition from icon code first
            day = self.coordinator.get_forecast(FIELD_FORECAST_ICONCODE)
            night = self.coordinator.get_forecast(FIELD_FORECAST_ICONCODE, 1)
            condition = self.coordinator._iconcode_to_condition(day or night)
            
            if condition:
                return condition
                
            # Fallback to solar radiation based estimation
            return self._estimate_condition_from_solar_radiation()
            
        except (TypeError, KeyError, IndexError):
            return None

    def _estimate_condition_from_solar_radiation(self):
        """Estimate weather condition from solar radiation."""
        try:
            solar_radiation = self.coordinator.get_condition('solarRadiation')
            if solar_radiation is None:
                return None
                
            # Simple solar radiation based condition estimation
            if solar_radiation > 800:
                return 'sunny'
            elif solar_radiation > 400:
                return 'partlycloudy'
            elif solar_radiation > 100:
                return 'cloudy'
            else:
                return 'cloudy'
        except (TypeError, KeyError):
            return None

    def _get_forecast_temperature_fields(self) -> tuple[str, str]:
        """Get the appropriate temperature fields based on calendar day setting."""
        if getattr(self.coordinator, '_calendarday', False):
            return (
                FIELD_FORECAST_CALENDARDAYTEMPERATUREMAX,
                FIELD_FORECAST_CALENDARDAYTEMPERATUREMIN
            )
        return (
            FIELD_FORECAST_TEMPERATUREMAX,
            FIELD_FORECAST_TEMPERATUREMIN
        )

    def _get_forecast_periods(self) -> list[int]:
        """Get forecast periods, adjusting for missing current period."""
        periods = [0, 2, 4, 6, 8]
        # If current period temperature is None, start from next period
        if self.coordinator.get_forecast('temperature', 0) is None:
            periods[0] += 1
        return periods

    def _create_forecast_entry(self, period: int, temp_max_field: str, temp_min_field: str) -> dict[str, Any] | None:
        """Create a single forecast entry."""
        try:
            forecast_time = self.coordinator.get_forecast(FIELD_FORECAST_VALIDTIMEUTC, period)
            if forecast_time is None:
                return None

            return {
                ATTR_FORECAST_CONDITION: self.coordinator._iconcode_to_condition(
                    self.coordinator.get_forecast(FIELD_FORECAST_ICONCODE, period)
                ),
                ATTR_FORECAST_PRECIPITATION: self.coordinator.get_forecast(FIELD_FORECAST_QPF, period),
                ATTR_FORECAST_PRECIPITATION_PROBABILITY: self.coordinator.get_forecast(
                    FIELD_FORECAST_PRECIPCHANCE, period
                ),
                ATTR_FORECAST_TEMP: self.coordinator.get_forecast(temp_max_field, period),
                ATTR_FORECAST_TEMP_LOW: self.coordinator.get_forecast(temp_min_field, period),
                ATTR_FORECAST_TIME: dt_util.utc_from_timestamp(forecast_time).isoformat(),
                ATTR_FORECAST_WIND_BEARING: self.coordinator.get_forecast(
                    FIELD_FORECAST_WINDDIRECTIONCARDINAL, period
                ),
                ATTR_FORECAST_WIND_SPEED: self.coordinator.get_forecast(FIELD_FORECAST_WINDSPEED, period),
            }
        except (TypeError, ValueError, KeyError) as err:
            _LOGGER.warning("Error creating forecast entry for period %s: %s", period, err)
            return None

    def _create_forecast_entry_new_format(self, period: int, temp_max_field: str, temp_min_field: str) -> Forecast | None:
        """Create a single forecast entry in new Forecast format."""
        try:
            forecast_time = self.coordinator.get_forecast(FIELD_FORECAST_VALIDTIMEUTC, period)
            if forecast_time is None:
                return None

            return Forecast(
                condition=self.coordinator._iconcode_to_condition(
                    self.coordinator.get_forecast(FIELD_FORECAST_ICONCODE, period)
                ),
                native_precipitation=self.coordinator.get_forecast(FIELD_FORECAST_QPF, period),
                precipitation_probability=self.coordinator.get_forecast(FIELD_FORECAST_PRECIPCHANCE, period),
                native_temperature=self.coordinator.get_forecast(temp_max_field, period),
                native_templow=self.coordinator.get_forecast(temp_min_field, period),
                datetime=dt_util.utc_from_timestamp(forecast_time).isoformat(),
                native_wind_speed=self.coordinator.get_forecast(FIELD_FORECAST_WINDSPEED, period),
                wind_bearing=self.coordinator.get_forecast(FIELD_FORECAST_WINDDIRECTION, period),
            )
        except (TypeError, ValueError, KeyError) as err:
            _LOGGER.warning("Error creating forecast entry for period %s: %s", period, err)
            return None

    def _forecast_legacy(self) -> list[dict[str, Any]]:
        """Return the forecast in legacy dict format."""
        temp_max_field, temp_min_field = self._get_forecast_temperature_fields()
        periods = self._get_forecast_periods()
        
        forecast = []
        for period in periods:
            entry = self._create_forecast_entry(period, temp_max_field, temp_min_field)
            if entry:
                forecast.append(entry)
        
        return forecast

    def _forecast_new(self) -> list[Forecast] | None:
        """Return the forecast in new Forecast format."""
        temp_max_field, temp_min_field = self._get_forecast_temperature_fields()
        periods = self._get_forecast_periods()
        
        forecast = []
        for period in periods:
            entry = self._create_forecast_entry_new_format(period, temp_max_field, temp_min_field)
            if entry:
                forecast.append(entry)
        
        return forecast if forecast else None

    def _forecast(self) -> list[Forecast]:
        """Return the forecast in native units."""
        return self._forecast_legacy()

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast in native units."""
        return self._forecast_new()
