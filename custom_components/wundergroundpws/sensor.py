"""
Sensor Support for WUndergroundPWS weather service.
For more details about this platform, please refer to the documentation at
https://github.com/cytech/Home-Assistant-wundergroundpws/tree/v2.X.X
"""
from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.unit_system import METRIC_SYSTEM

from .coordinator import WundergroundPWSUpdateCoordinator

from .const import (
    CONF_ATTRIBUTION, DOMAIN, FIELD_DAYPART, FIELD_OBSERVATIONS, MAX_FORECAST_DAYS,
    FEATURE_CONDITIONS, FEATURE_FORECAST, FEATURE_FORECAST_DAYPART, FIELD_FORECAST_DAYPARTNAME,
    FIELD_FORECAST_DAYOFWEEK, FIELD_FORECAST_EXPIRED
)
from .wupws_obs_sensors import *
from .wupws_forecast_sensors import *

_LOGGER = logging.getLogger(__name__)

# Declaration of supported WUpws observation/condition sensors
SENSOR_DESCRIPTIONS: tuple[WundergroundPWSSensorEntityDescription, ...] = (
    obs_sensor_descriptions
)

# Declaration of supported WUpws forecast sensors
FORECAST_SENSOR_DESCRIPTIONS: tuple[WundergroundPWSSensorEntityDescription, ...] = (
    forecast_sensor_descriptions
)


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Add WundergroundPWS entities from a config_entry."""
    coordinator: WundergroundPWSUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    sensors = [
        WundergroundPWSSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    ]

    if coordinator.forecast_enable:
        sensors.extend(
            WundergroundPWSForecastSensor(coordinator, description, forecast_day=day)
            for day in range(MAX_FORECAST_DAYS)
            for description in FORECAST_SENSOR_DESCRIPTIONS
            if description.feature == FEATURE_FORECAST
        )

        sensors.extend(
            WundergroundPWSForecastSensor(coordinator, description, forecast_day=day)
            for day in range(MAX_FORECAST_DAYS * 2)
            for description in FORECAST_SENSOR_DESCRIPTIONS
            if description.feature == FEATURE_FORECAST_DAYPART
        )

    async_add_entities(sensors)


class WundergroundPWSSensor(CoordinatorEntity, SensorEntity):
    """Implementing the WUnderground sensor."""
    _attr_has_entity_name = True
    _attr_attribution = CONF_ATTRIBUTION
    entity_description: WundergroundPWSSensorEntityDescription

    def __init__(
            self,
            coordinator: WundergroundPWSUpdateCoordinator,
            description: WundergroundPWSSensorEntityDescription,
            forecast_day: int | None = None,
    ):
        super().__init__(coordinator)
        self.entity_description = description

        entity_id_format = description.key + ".{}"

        if forecast_day is not None:
            if description.feature == FEATURE_FORECAST_DAYPART:
                self._attr_unique_id = (
                    f"{self.coordinator.pws_id},{description.key}_{forecast_day}fdp".lower()
                )
                if forecast_day in range(0, MAX_FORECAST_DAYS * 2, 2):  # [0, 2, 4, 6, 8]  days
                    self.entity_id = generate_entity_id(
                        entity_id_format, f"{self.coordinator.pws_id}_{description.name}_{forecast_day}d",
                        hass=coordinator.hass
                    )
                else:  # nights
                    self.entity_id = generate_entity_id(
                        entity_id_format, f"{self.coordinator.pws_id}_{description.name}_{forecast_day}n",
                        hass=coordinator.hass
                    )
            else:  # forecast outside daypart
                self._attr_unique_id = (
                    f"{self.coordinator.pws_id},{description.key}_{forecast_day}f".lower()
                )
                self.entity_id = generate_entity_id(
                    entity_id_format, f"{self.coordinator.pws_id}_{description.name}_{forecast_day}",
                    hass=coordinator.hass
                )
            self.forecast_day = forecast_day
        else:
            self._attr_unique_id = f"{self.coordinator.pws_id},{description.key}".lower()
            self.entity_id = generate_entity_id(
                entity_id_format, f"{self.coordinator.pws_id}_{description.name}", hass=coordinator.hass
            )
            self.forecast_day = None
        self._unit_system = coordinator.unit_system
        self._sensor_data = _get_sensor_data(
            coordinator.data, description.key, self._unit_system, description.feature, forecast_day)
        self._attr_native_unit_of_measurement = self.entity_description.unit_fn(
            self.coordinator.hass.config.units is METRIC_SYSTEM) if self._sensor_data is not None else ""

    @property
    def available(self) -> bool:
        """Return if weather data is available."""
        return self.coordinator.data is not None

    @property
    def name(self):
        """Return the name of the sensor."""
        if self.entity_description.key in self.coordinator._tranfile.keys() or \
                self.entity_description.key in self.coordinator._tranfile[FIELD_DAYPART].keys():
            if self.forecast_day is not None:
                if self.entity_description.feature == FEATURE_FORECAST_DAYPART:
                    if self.coordinator.data[FIELD_DAYPART][0][FIELD_FORECAST_DAYPARTNAME][self.forecast_day] is not None:
                        return self.coordinator._tranfile[FIELD_DAYPART][self.entity_description.key] + " " + \
                            self.coordinator.data[FIELD_DAYPART][0][FIELD_FORECAST_DAYPARTNAME][
                                self.forecast_day]
                    else:
                        return self.coordinator._tranfile[FIELD_DAYPART][self.entity_description.key] + " " + \
                            self.coordinator._tranfile[FIELD_DAYPART][FIELD_FORECAST_EXPIRED]
                return self.coordinator._tranfile[self.entity_description.key] + " " + \
                    self.coordinator.data[FIELD_FORECAST_DAYOFWEEK][self.forecast_day]
            return self.coordinator._tranfile[self.entity_description.key]

        return self.entity_description.name

    @property
    def native_value(self) -> StateType:
        """Return the state."""
        return self.entity_description.value_fn(self._sensor_data, self._unit_system)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.entity_description.attr_fn(self.coordinator.data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._sensor_data = _get_sensor_data(
            self.coordinator.data, self.entity_description.key, self._unit_system, self.entity_description.feature
        )
        self.async_write_ha_state()


def _get_sensor_data(
        sensors: dict[str, Any],
        kind: str,
        unit_system: str,
        feature: str,
        forecast_day: int | None = None
) -> Any:
    """Get sensor data."""
    try:
        if not sensors:
            return None
            
        if feature == FEATURE_CONDITIONS:
            if FIELD_OBSERVATIONS not in sensors or not sensors[FIELD_OBSERVATIONS]:
                return None
            obs_data = sensors[FIELD_OBSERVATIONS][0]
            if unit_system not in obs_data or not obs_data[unit_system]:
                return None
            value = obs_data[unit_system].get(kind)
            return value if value is not None else None
        elif feature == FEATURE_FORECAST:
            if kind not in sensors or not sensors[kind]:
                return None
            if forecast_day >= len(sensors[kind]):
                return None
            value = sensors[kind][forecast_day]
            return value if value is not None else None
        elif feature == FEATURE_FORECAST_DAYPART:
            if FIELD_DAYPART not in sensors or not sensors[FIELD_DAYPART] or not sensors[FIELD_DAYPART][0]:
                return None
            daypart_data = sensors[FIELD_DAYPART][0]
            if kind not in daypart_data or not daypart_data[kind]:
                return None
            if forecast_day >= len(daypart_data[kind]):
                return None
            value = daypart_data[kind][forecast_day]
            return value if value is not None else None
        elif feature == FEATURE_OBSERVATIONS:
            if FIELD_OBSERVATIONS not in sensors or not sensors[FIELD_OBSERVATIONS]:
                return None
            obs_data = sensors[FIELD_OBSERVATIONS][0]
            value = obs_data.get(kind)
            return value if value is not None else None
        else:
            return sensors
    except (KeyError, IndexError, TypeError):
        return None


class WundergroundPWSForecastSensor(WundergroundPWSSensor):
    """Define an WundergroundPWS forecast entity."""

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes."""
        return self.entity_description.attr_fn(self._sensor_data)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle data update."""
        self._sensor_data = _get_sensor_data(
            self.coordinator.data, self.entity_description.key, self._unit_system, self.entity_description.feature,
            self.forecast_day
        )
        self.async_write_ha_state()
