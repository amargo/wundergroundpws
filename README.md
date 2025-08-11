# WundergroundPWS v2.1.1 - Multi-Station Support

Home Assistant custom integration for Weather Underground personal weather stations with **automatic fallback support**.

## Key Features

- **Multi-Station Fallback** - Never stuck values when stations go offline
- **Single Weather Entity** - One centralized entity (e.g., `weather.velence`) 
- **Real-time Monitoring** - See which station is active
- **Priority Management** - Configure station priority order
- **Unified Sensors** - Group-based sensor names (e.g., `sensor.velence_temperature`)

## Quick Start

1. **Get API Key** - Free for Weather Underground PWS owners
2. **Install Integration** - Copy to `custom_components/`
3. **Add Integration** - Settings → Devices & Services → Add Integration
4. **Choose Mode** - Single station or Multi-station with fallback

## Requirements

- Home Assistant 2023.1+
- Weather Underground PWS API Key
- Active weather station(s) uploading to Weather Underground

# Installation Prerequisites
Please review the minimum requirements below to determine whether you will be able to
install and use the software.


# Weather Underground PWS API Key
Free API keys are only issued to registered and active Weather Underground personal weather station users.  
To use this integration, you need a Weather Underground personal weather station API key and Station ID.  
To get a free API key:  
1) You must have a personal weather station registered and uploading data to Weather Underground.  
    a) Join weather Underground  
    b) Sign In  
    c) My Profile -> My Weather Stations  
    d) Add a New PWS  
2) get API key at  https://www.wunderground.com/member/api-keys.  

Please consider this when using the following information.  
[Back to top](#top)


# Multi-Station Installation Guide

## Problem Solution

Original WundergroundPWS integration issues:
- ❌ When a station goes offline, values get stuck
- ❌ No automatic fallback to other stations  
- ❌ Separate entity needed for each station

## New Multi-Station Solution

- ✅ **Multiple station management with priority**
- ✅ **Automatic fallback** when a station goes offline
- ✅ **Centralized weather entity** (e.g. `weather.velence`)
- ✅ **Real-time station status** information
- ✅ **Unavailable status** when all stations are offline

## Installation Steps

### 1. Copy Files
```bash
# Copy the entire folder to Home Assistant config directory
cp -r custom_components/wundergroundpws /config/custom_components/
```

### 2. Restart Home Assistant
Restart Home Assistant for changes to take effect.

### 3. Add Integration

1. Go to **Settings** → **Devices & Services** → **Add Integration**
2. Search for **"WundergroundPWS"** integration
3. Select it

## Configuration

### Step 1: API Key and Type Selection
- **API Key**: Your Weather Underground PWS API key
- **Integration Type**: 
  - "Single Station" - traditional mode
  - "Multi-Station (with fallback support)" - new feature

### Step 2A: Single Station (traditional)
- **Station ID**: e.g. `IKPOLN1`

### Step 2B: Multi-Station (recommended)
1. **Group name**: e.g. `velence` (this will be the entity name: `weather.velence`)
2. **Coordinates**: optional, auto-detected

### Step 3: Add Stations (multi-station only)
For each station provide:
- **Station ID**: e.g. `IKPOLN1`, `IKPOLN2`, `IVELEN69`
- **Friendly name**: e.g. "Velence Station 1"
- **Priority**: 1 = highest, 10 = lowest

### Example Configuration
```
API Key: your_api_key_here
Group: velence

Stations:
1. IKPOLN1 - "Velence Station 1" - Priority: 1
2. IKPOLN2 - "Velence Station 2" - Priority: 2  
3. IVELEN69 - "Velence Station 3" - Priority: 3
```

## Usage

### Lovelace Card
```yaml
type: horizontal-stack
cards:
  - type: custom:vertical-stack-in-card
    cards:
      - show_current: true
        show_forecast: true
        type: weather-forecast
        entity: weather.velence  # Your group name
        forecast_type: daily
      - type: custom:weather-card
        entity: weather.velence
        current: false
        details: true
        forecast: true
        hourly_forecast: true
        number_of_forecasts: "3"
        
  # Station status card
  - type: entities
    title: Station Status
    entities:
      - entity: weather.velence
        attribute: active_station
        name: Active Station
      - entity: weather.velence
        attribute: active_station_name
        name: Station Name
```

### Status Information
Weather entity extra attributes:
- `active_station`: Currently active station ID
- `active_station_name`: Active station friendly name
- `station_status`: All stations status
- `group_name`: Group name

## How It Works

1. **Priority-based selection**: Uses the lowest priority (1) working station
2. **Automatic fallback**: When active station goes offline, automatically switches to next working station
3. **5-minute refresh**: Regularly checks all stations
4. **Unavailable status**: When all stations are offline, entity becomes unavailable

## Benefits

- **Reliability**: Values never get stuck
- **Simplicity**: One entity instead of multiple stations  
- **Transparency**: See which station is active
- **Flexibility**: Easy to add/remove stations

[Back to top](#top)

# Configure
Wundergroundpws integration configuration options available at:  
Settings-Devices & Services-Wundergroundpws-Configure  

**OPTIONS:**  
**Create Forecast Sensors?**  
Forecast sensors are not created by default. They will be created if you enable "Create Forecast Sensors" in the integration "Configure".  
Forecast sensors will then be created but are disabled. To enable, goto the integration - entities and select the sensors you would like and enable them.  

**Numeric Precision**  
none (integer) or decimal (single).  
Only applies to PWS current values (not forecast) in sensors (not weather entity).

**Language**  
Specify the language that the API returns.  
The default is English (en-US).

**Temperature by Calendar Day?** (experimental)  
**_USE AT YOUR OWN RISK_** - Undocumented in The Weather Company PWS observations API.  
If checked, retrieves Forecast temperature max/min relative to calendar day (12:00am -> 11:59pm) as opposed to API period (~7:00am -> ~6:59am).      
Only affects the weather entity forecast values, not the sensors.  
This field is undocumented in The Weather Company PWS API, so it is subject to change and if removed from API response in the future, will crash the integration if set true.

**Latitude** - Default is retrieved from StationID  
Override Latitude coordinate for weather forecast.

**Longitude** - Default is retrieved from StationID  
Override Longitude coordinate for weather forecast.  
[Back to top](#top) 
        
# Available Sensors
```yaml
# description: Conditions to display in the frontend. The following conditions can be monitored.
# See https://www.wunderground.com/about/data) for Weather Underground data information.
#
# Observations (current)
 neighborhood:
   unique_id: <pws_id>,neighborhood
   entity_id: sensor.<pws_id>_neighborhood
   description: WU PWS reference name
 obsTimeLocal:
   unique_id: <pws_id>,obstimelocal
   entity_id: sensor.<pws_id>_local_observation_time   
   description: Text summary of local observation time
 humidity:
   unique_id: <pws_id>,humidity
   entity_id: sensor.<pws_id>_relative_humidity   
   description: Relative humidity    
 stationID:
   unique_id: <pws_id>,stationid
   entity_id: sensor.<pws_id>_station_id   
   description: Your personal weather station (PWS) ID
 solarRadiation:
   unique_id: <pws_id>,solarradiation
   entity_id: sensor.<pws_id>_solar_radiation   
   description: Current levels of solar radiation
 uv:
   unique_id: <pws_id>,uv
   entity_id: sensor.<pws_id>_uv_index   
   description: Current levels of UV radiation.
 winddir:
   unique_id: <pws_id>,winddir
   entity_id: sensor.<pws_id>_wind_direction_degrees   
   description: Wind degrees
 windDirectionCardinal:
   unique_id: <pws_id>,winddirectioncardinal
   entity_id: sensor.<pws_id>_wind_direction_cardinal   
   description: Wind cardinal direction (N, NE, NNE, S, E, W, etc)
# conditions (current)       
 dewpt:
   unique_id: <PWS_ID>,dewpt
   entity_id: sensor.<pws_id>_dewpoint
   description: Temperature below which water droplets begin to condense and dew can form
 elev:
   unique_id: <pws_id>,elev
   entity_id: sensor.<pws_id>_elevation   
   description: Elevation
 heatIndex:
   unique_id: <pws_id>,heatindex
   entity_id: sensor.<pws_id>_heat_index   
   description: Heat index (combined effects of the temperature and humidity of the air)
 precipRate:
   unique_id: <pws_id>,preciprate
   entity_id: sensor.<pws_id>_precipitation_rate   
   description: Rain intensity
 precipTotal:
   unique_id: <pws_id>,preciptotal
   entity_id: sensor.<pws_id>_precipitation_today   
   description: Today Total precipitation
 pressure:
   unique_id: <pws_id>,pressure
   entity_id: sensor.<pws_id>_pressure   
   description: Atmospheric air pressure
 temp:
   unique_id: <pws_id>,temp
   entity_id: sensor.<pws_id>_temperature   
   description: Current temperature
 windChill:
   unique_id: <pws_id>,windchill
   entity_id: sensor.<pws_id>_wind_chill   
   description: Wind Chill (combined effects of the temperature and wind)      
 windGust:
   unique_id: <pws_id>,windgust
   entity_id: sensor.<pws_id>_wind_gust   
   description: Wind gusts speed
 windSpeed:
   unique_id: <pws_id>,windspeed
   entity_id: sensor.<pws_id>_wind_speed   
   description: Current wind speed      
#   Forecast
 narrative:
   unique_id: <PWS_ID>,narrative_<day>f
   entity_id: sensor.<pws_id>_weather_summary_<day>
   description: A human-readable weather forecast for Day. (<day> Variations 0, 1, 2, 3, 4)
 qpfSnow:
   unique_id: <pws_id>,qpfsnow_<day>f
   entity_id: sensor.<pws_id>_snow_amount_<day>
   description: Forecasted snow intensity. (<day> Variations 0, 1, 2, 3, 4)
#   Forecast daypart
 narrative:
   unique_id: <PWS_ID>,narrative_<daypart>fdp
   entity_id: sensor.<pws_id>_forecast_summary_<suffix>
   description: A human-readable weather forecast for Day. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
 qpf:
   unique_id: <pws_id>,qpf_<daypart>fdp
   entity_id: sensor.<pws_id>_precipitation_amount_<suffix>
   description: Forecasted precipitation intensity. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
 precipChance:
   unique_id: <pws_id>,precipchance_<daypart>fdp
   entity_id: sensor.<pws_id>_precipitation_probability_<suffix>
   description: Forecasted precipitation probability in %. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)      
 temperature:
   unique_id: <pws_id>,temperature<daypart>fdp
   entity_id: sensor.<pws_id>_forecast_temperature_<suffix>
   description: Forecasted temperature. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
 windSpeed:
   unique_id: <pws_id>,windspeed_<daypart>fdp
   entity_id: sensor.<pws_id>_average_wind_<suffix>
   description: Forecasted wind speed. (suffix Variations 0d, 1n, 2d, 3n, 4d, 5n, 6d, 7n, 8d, 9n)
```

All the conditions listed above will be updated every 5 minutes.  

**_Wunderground API caveat:   
The daypart object as well as the temperatureMax field OUTSIDE of the daypart object will appear as null in the API after 3:00pm Local Apparent Time.  
The affected sensors will return as "Today Expired" with a value of "Unknown" when this condition is met._**


Variations above marked with "#d" are daily forecasts.
Variations above marked with "#n" are nightly forecasts.


Note: While the platform is called “wundergroundpws” the sensors will show up in Home Assistant as  
```sensor.<pws_id>_forecast_temperature_<suffix>```  
(eg: sensor.samplepwsid_forecast_temperature_0d).


# Weather Entity
wundergroundpws data returned to weather entity (HASS weather forecast card):  
Current:
- temperature
- pressure
- humidity
- wind_speed
- wind_bearing

Forecast:
- datetime
- temperature (max)
- temperature (low)
- condition (icon)
- precipitation
- precipitation_probability
- wind_bearing
- wind_speed

templates can be created to access these values such as:
```
{% for state in states.weather -%}
  {%- if loop.first %}The {% elif loop.last %} and the {% else %}, the {% endif -%}
  {{ state.name | lower }} is {{state.state_with_unit}}
{%- endfor %}.

Wind is {{ states.weather.<STATIONID>.attributes.forecast[0].wind_bearing }} at {{ states.weather.<STATIONID>.attributes.forecast[0].wind_speed }} {{ states.weather.<STATIONID>.attributes.wind_speed_unit }}

```
[Back to top](#top)

# Sensors available in statistics
The following are wundergroundpws sensors exposed to the statistics card in Lovelace.  
Note that only sensors of like units can be combined in a single card.  

* **class NONE**
* sensor.samplepwsid_uv_index
* 
* **class DEGREE**
* sensor.sensor.samplepwsid_wind_direction_degrees

* 
* **class RATE & SPEED**
* sensor.samplepwsid_precipitation_rate
* sensor.samplepwsid_wind_gust
* sensor.samplepwsid_wind_speed
* 
* **class LENGTH**
* sensor.samplepwsid_precipitation_today
* 
* **class PRESSURE**
* sensor.samplepwsid_pressure
* 
* **class HUMIDITY**
* sensor.samplepwsid_relative_humidity
* 
* **class IRRADIANCE**
* sensor.samplepwsid_solar_radiation
* 
* **class TEMPERATURE**
* sensor.samplepwsid_dewpoint
* sensor.samplepwsid_heat_index
* sensor.samplepwsid_wind_chill
* sensor.samplepwsid_temperature

[Back to top](#top)


# Localization

Sensor "friendly names" are set via translation files.  
Wundergroundpws translation files are located in the 'wundergroundpws/wupws_translations' directory.
Files were translated, using 'en.json' as the base, via https://translate.i18next.com.  
Translations only use the base language code and not the variant (i.e. zh-CN/zh-HK/zh-TW uses zh).  
The default is en-US (translations/en.json) if the lang: option is not set in the wundergroundpws config.  
If lang: is set (i.e.  lang: de-DE), then the translations/de.json file is loaded, and the Weather Underground API is queried with de-DE.    
The translation file applies to all sensor friendly names.   
Forecast-narrative, forecast-dayOfWeek, forecast-daypart-narrative and forecast-daypart-daypartName are translated by the api. 
Available lang: options are:  
```
'am-ET', 'ar-AE', 'az-AZ', 'bg-BG', 'bn-BD', 'bn-IN', 'bs-BA', 'ca-ES', 'cs-CZ', 'da-DK', 'de-DE', 'el-GR', 'en-GB',
'en-IN', 'en-US', 'es-AR', 'es-ES', 'es-LA', 'es-MX', 'es-UN', 'es-US', 'et-EE', 'fa-IR', 'fi-FI', 'fr-CA', 'fr-FR',
'gu-IN', 'he-IL', 'hi-IN', 'hr-HR', 'hu-HU', 'in-ID', 'is-IS', 'it-IT', 'iw-IL', 'ja-JP', 'jv-ID', 'ka-GE', 'kk-KZ',
'km-KH', 'kn-IN', 'ko-KR', 'lo-LA', 'lt-LT', 'lv-LV', 'mk-MK', 'mn-MN', 'mr-IN', 'ms-MY', 'my-MM', 'ne-IN', 'ne-NP',
'nl-NL', 'no-NO', 'om-ET', 'pa-IN', 'pa-PK', 'pl-PL', 'pt-BR', 'pt-PT', 'ro-RO', 'ru-RU', 'si-LK', 'sk-SK', 'sl-SI',
'sq-AL', 'sr-BA', 'sr-ME', 'sr-RS', 'sv-SE', 'sw-KE', 'ta-IN', 'ta-LK', 'te-IN', 'ti-ER', 'ti-ET', 'tg-TJ', 'th-TH',
'tk-TM', 'tl-PH', 'tr-TR', 'uk-UA', 'ur-PK', 'uz-UZ', 'vi-VN', 'zh-CN', 'zh-HK', 'zh-TW'
```
Weather Entity (hass weather card) translations are handled by Home Assistant and configured under the user -> language setting.  
[Back to top](#top)

# Troubleshooting

## Multi-Station Issues

### Enable Logs
```yaml
logger:
  logs:
    custom_components.wundergroundpws.multi_station_coordinator: debug
```

### Common Issues

**No Data**
- Check API key
- Check station IDs

**Station Not Switching**  
- Check priorities
- Review logs

**Unavailable**
- Check that at least one station is online
- Wait 5 minutes for next refresh

## General Issues

**Integration Not Found**
- Ensure files are in `/config/custom_components/wundergroundpws/`
- Restart Home Assistant
- Check logs for errors

**API Rate Limit**
- Each station uses ~288 API calls per day
- Multi-station uses same rate per station
- Consider reducing number of stations if hitting limits

**Sensor Values Stuck (Single Station)**
- Consider upgrading to Multi-Station mode
- Check station is online at wunderground.com
- Restart integration

[Back to top](#top)