"""The wundergroundpws component."""
import logging
import os.path
from typing import Final
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_API_KEY,
    CONF_LATITUDE, CONF_LONGITUDE, Platform
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.util.unit_system import METRIC_SYSTEM
from homeassistant.util import json
from .coordinator import WundergroundPWSUpdateCoordinator, WundergroundPWSUpdateCoordinatorConfig
from .multi_station_coordinator import MultiStationUpdateCoordinator, MultiStationCoordinatorConfig, StationConfig
from .const import (
    CONF_LANG,
    CONF_NUMERIC_PRECISION,
    CONF_PWS_ID,
    DOMAIN, API_METRIC, API_IMPERIAL, API_URL_METRIC, API_URL_IMPERIAL, CONF_CALENDARDAYTEMPERATURE,
    CONF_FORECAST_SENSORS
)

# Multi-station constants
CONF_INTEGRATION_TYPE = "integration_type"
CONF_GROUP_NAME = "group_name"
CONF_STATIONS = "stations"
CONF_STATION_NAME = "station_name"
CONF_STATION_PRIORITY = "station_priority"

PLATFORMS: Final = [Platform.WEATHER, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up the WundergroundPWS component."""
    hass.data.setdefault(DOMAIN, {})

    # Check if this is a multi-station or single station setup
    integration_type = entry.data.get(CONF_INTEGRATION_TYPE, "single")
    
    if integration_type == "multi":
        return await _async_setup_multi_station_entry(hass, entry)
    else:
        return await _async_setup_single_station_entry(hass, entry)


async def _async_setup_single_station_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up single station entry."""
    latitude = entry.options.get(CONF_LATITUDE)
    longitude = entry.options.get(CONF_LONGITUDE)

    if hass.config.units is METRIC_SYSTEM:
        unit_system_api = API_URL_METRIC
        unit_system = API_METRIC
    else:
        unit_system_api = API_URL_IMPERIAL
        unit_system = API_IMPERIAL

    config = WundergroundPWSUpdateCoordinatorConfig(
        api_key=entry.data[CONF_API_KEY],
        pws_id=entry.data[CONF_PWS_ID],
        numeric_precision=entry.options.get(CONF_NUMERIC_PRECISION, "none"),
        unit_system_api=unit_system_api,
        unit_system=unit_system,
        lang=entry.options.get(CONF_LANG, "en-US"),
        calendarday=entry.options.get(CONF_CALENDARDAYTEMPERATURE, False),
        latitude=latitude,
        longitude=longitude,
        forecast_enable=entry.options.get(CONF_FORECAST_SENSORS, False),
        tranfile=""
    )

    # Get translation file for sensor friendly_name
    tfiledir = f'{hass.config.config_dir}/custom_components/{DOMAIN}/wupws_translations/'
    tfilename = config.lang.split('-', 1)[0]

    if os.path.isfile(f'{tfiledir}{tfilename}.json'):
        config.tranfile = await hass.async_add_executor_job(json.load_json, f'{tfiledir}{tfilename}.json')
    else:
        config.tranfile = await hass.async_add_executor_job(json.load_json, f'{tfiledir}en.json')
        _LOGGER.warning(f'Sensor translation file {tfilename}.json does not exist. Defaulting to en-US.')

    wupwscoordinator = WundergroundPWSUpdateCoordinator(hass, config)
    await wupwscoordinator.async_config_entry_first_refresh()
    if not wupwscoordinator.last_update_success:
        raise ConfigEntryNotReady

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    hass.data[DOMAIN][entry.entry_id] = wupwscoordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_setup_multi_station_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up multi-station entry."""
    latitude = entry.options.get(CONF_LATITUDE)
    longitude = entry.options.get(CONF_LONGITUDE)

    if hass.config.units is METRIC_SYSTEM:
        unit_system_api = API_URL_METRIC
        unit_system = API_METRIC
    else:
        unit_system_api = API_URL_IMPERIAL
        unit_system = API_IMPERIAL

    # Parse station configurations
    stations = []
    for station_data in entry.data[CONF_STATIONS]:
        stations.append(StationConfig(
            pws_id=station_data[CONF_PWS_ID],
            priority=station_data[CONF_STATION_PRIORITY],
            name=station_data[CONF_STATION_NAME]
        ))

    config = MultiStationCoordinatorConfig(
        api_key=entry.data[CONF_API_KEY],
        stations=stations,
        group_name=entry.data[CONF_GROUP_NAME],
        numeric_precision=entry.options.get(CONF_NUMERIC_PRECISION, "none"),
        unit_system_api=unit_system_api,
        unit_system=unit_system,
        lang=entry.options.get(CONF_LANG, "en-US"),
        calendarday=entry.options.get(CONF_CALENDARDAYTEMPERATURE, False),
        latitude=latitude,
        longitude=longitude,
        forecast_enable=entry.options.get(CONF_FORECAST_SENSORS, False),
        tranfile=""
    )

    # Get translation file for sensor friendly_name
    tfiledir = f'{hass.config.config_dir}/custom_components/{DOMAIN}/wupws_translations/'
    tfilename = config.lang.split('-', 1)[0]

    if os.path.isfile(f'{tfiledir}{tfilename}.json'):
        config.tranfile = await hass.async_add_executor_job(json.load_json, f'{tfiledir}{tfilename}.json')
    else:
        config.tranfile = await hass.async_add_executor_job(json.load_json, f'{tfiledir}en.json')
        _LOGGER.warning(f'Sensor translation file {tfilename}.json does not exist. Defaulting to en-US.')

    # Create multi-station coordinator
    coordinator = MultiStationUpdateCoordinator(hass, config)
    await coordinator.async_config_entry_first_refresh()
    
    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Set up both weather and sensor platforms for multi-station
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener."""
    await hass.config_entries.async_reload(entry.entry_id)
