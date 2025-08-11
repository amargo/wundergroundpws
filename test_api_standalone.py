#!/usr/bin/env python3
"""
Standalone API test script for WundergroundPWS multi-station.
This script tests the Weather Underground API directly without Home Assistant dependencies.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import aiohttp
from dotenv import load_dotenv
from dataclasses import dataclass

@dataclass
class StationConfig:
    """Configuration for a weather station."""
    pws_id: str
    name: str
    priority: int

class StandaloneMultiStationTester:
    """Standalone multi-station tester without Home Assistant dependencies."""
    
    def __init__(self, api_key: str, stations: List[StationConfig], 
                 language: str = 'en-US', unit_system: str = 'metric'):
        self.api_key = api_key
        self.stations = sorted(stations, key=lambda x: x.priority)  # Sort by priority
        self.language = language
        self.unit_system_api = 'm' if unit_system == 'metric' else 'e'
        self.session = None
        self.active_station = None
        self.station_data = {}
        
        # API URLs
        self._RESOURCESHARED = '&format=json&apiKey={apiKey}&units={units}'
        self._RESOURCECURRENT = ('https://api.weather.com/v2/pws/observations/current'
                                '?stationId={stationId}&numericPrecision=decimal')
        self._RESOURCEFORECAST = ('https://api.weather.com/v3/wx/forecast/daily/5day'
                                 '?geocode={latitude},{longitude}&language={language}')
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def _build_url(self, baseurl: str, station_id: str, latitude: float = 0, longitude: float = 0) -> str:
        """Build URL for API request."""
        if baseurl == self._RESOURCECURRENT:
            baseurl += '&numericPrecision=decimal'
        elif baseurl == self._RESOURCEFORECAST:
            baseurl += f'&language={self.language}'
        
        baseurl += self._RESOURCESHARED
        
        return baseurl.format(
            apiKey=self.api_key,
            language=self.language,
            latitude=latitude,
            longitude=longitude,
            stationId=station_id,
            units=self.unit_system_api
        )
    
    async def _fetch_station_data(self, station: StationConfig) -> Optional[Dict[str, Any]]:
        """Fetch data from a single station."""
        headers = {
            'Accept-Encoding': 'gzip',
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36"
        }
        
        try:
            print(f"  🔍 Testing station {station.pws_id} ({station.name})...")
            
            # Fetch current conditions
            url = self._build_url(self._RESOURCECURRENT, station.pws_id)
            print(f"     URL: {url}")
            
            async with self.session.get(url, headers=headers) as response:
                print(f"     HTTP Status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"     📄 Error response:")
                    print(f"        Status: {response.status}")
                    print(f"        Text: {error_text[:200]}...")
                    raise ValueError(f'HTTP {response.status}: {error_text}')
                
                result_current = await response.json()
                
                if result_current is None:
                    raise ValueError('NO CURRENT RESULT - API returned null')
                
                # Check for API errors
                if 'errors' in result_current and result_current['errors']:
                    errors = '; '.join([e['message'] for e in result_current['errors']])
                    raise ValueError(f'API Error: {errors}')
                
                # Check if observations exist
                if 'observations' not in result_current or not result_current['observations']:
                    raise ValueError('NO OBSERVATIONS DATA - Station may be offline')
                
                print(f"     ✅ Successfully fetched current data")
                
                # Print JSON response for debugging
                print(f"     📄 Current data JSON:")
                print(f"        {json.dumps(result_current, indent=2)[:500]}...")
                
                # Get coordinates from the station
                obs = result_current['observations'][0]
                latitude = obs.get('lat', 0)
                longitude = obs.get('lon', 0)
                
                # Try to fetch forecast (optional)
                try:
                    forecast_url = self._build_url(self._RESOURCEFORECAST, station.pws_id, latitude, longitude)
                    async with self.session.get(forecast_url, headers=headers) as forecast_response:
                        if forecast_response.status == 200:
                            result_forecast = await forecast_response.json()
                            if result_forecast and 'errors' not in result_forecast:
                                result_current.update(result_forecast)
                                print(f"     ✅ Successfully fetched forecast data")
                                print(f"     📄 Forecast data JSON:")
                                print(f"        {json.dumps(result_forecast, indent=2)[:500]}...")
                            else:
                                print(f"     ⚠️  Forecast data not available")
                        else:
                            print(f"     ⚠️  Forecast HTTP {forecast_response.status}")
                except Exception as forecast_err:
                    print(f"     ⚠️  Forecast error: {forecast_err}")
                
                return result_current
                
        except Exception as err:
            print(f"     ❌ Error: {err}")
            return None
    
    async def test_all_stations(self) -> Dict[str, Any]:
        """Test all stations and return results."""
        print(f"🚀 Testing {len(self.stations)} stations...")
        print()
        
        successful_stations = []
        failed_stations = []
        
        # Test each station
        for station in self.stations:
            try:
                data = await self._fetch_station_data(station)
                if data:
                    successful_stations.append((station, data))
                    self.station_data[station.pws_id] = {
                        'data': data,
                        'status': 'online',
                        'error': None
                    }
                else:
                    failed_stations.append(station)
                    self.station_data[station.pws_id] = {
                        'data': None,
                        'status': 'offline',
                        'error': 'No data returned'
                    }
            except Exception as e:
                failed_stations.append(station)
                self.station_data[station.pws_id] = {
                    'data': None,
                    'status': 'error',
                    'error': str(e)
                }
            print()
        
        # Select active station (highest priority working station)
        if successful_stations:
            self.active_station, active_data = successful_stations[0]
            print(f"🎯 Selected active station: {self.active_station.pws_id} ({self.active_station.name})")
            return active_data
        else:
            print("❌ No stations are working!")
            return None
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 STATION STATUS SUMMARY")
        print("="*60)
        
        for station in self.stations:
            station_info = self.station_data.get(station.pws_id, {})
            status = station_info.get('status', 'unknown')
            error = station_info.get('error')
            
            if status == 'online':
                status_icon = "🟢"
            elif status == 'offline':
                status_icon = "🟡"
            else:
                status_icon = "🔴"
            
            active_icon = "⭐" if self.active_station and station.pws_id == self.active_station.pws_id else "  "
            
            print(f"{status_icon} {active_icon} {station.pws_id:<12} ({station.name:<20}) Priority: {station.priority} - {status.upper()}")
            if error and status != 'online':
                print(f"     Error: {error}")
        
        print()
        
        # Show weather data if available
        if self.active_station and self.active_station.pws_id in self.station_data:
            data = self.station_data[self.active_station.pws_id]['data']
            if data and 'observations' in data and data['observations']:
                obs = data['observations'][0]
                print("🌡️  CURRENT WEATHER DATA")
                print("-" * 30)
                
                if self.unit_system_api == 'm' and 'metric' in obs:
                    metric = obs['metric']
                    print(f"Temperature: {metric.get('temp', 'N/A')}°C")
                    print(f"Humidity: {obs.get('humidity', 'N/A')}%")
                    print(f"Pressure: {metric.get('pressure', 'N/A')} mb")
                    print(f"Wind Speed: {metric.get('windSpeed', 'N/A')} km/h")
                elif self.unit_system_api == 'e' and 'imperial' in obs:
                    imperial = obs['imperial']
                    print(f"Temperature: {imperial.get('temp', 'N/A')}°F")
                    print(f"Humidity: {obs.get('humidity', 'N/A')}%")
                    print(f"Pressure: {imperial.get('pressure', 'N/A')} in")
                    print(f"Wind Speed: {imperial.get('windSpeed', 'N/A')} mph")
                
                print(f"Station ID: {obs.get('stationID', 'N/A')}")
                print(f"Observation Time: {obs.get('obsTimeUtc', 'N/A')}")

async def main():
    """Main test function."""
    print("=== WundergroundPWS Standalone API Test ===\n")
    
    # Load environment variables
    load_dotenv()
    
    # Check if .env file exists
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found!")
        print("   1. Copy .env.example to .env")
        print("   2. Fill in your API key and station details")
        print("   3. Run this script again")
        return
    
    # Get configuration from environment
    api_key = os.getenv('WU_API_KEY')
    if not api_key:
        print("❌ Error: WU_API_KEY not found in .env file")
        return
    
    group_name = os.getenv('GROUP_NAME', 'test_group')
    language = os.getenv('LANGUAGE', 'en-US')
    unit_system = os.getenv('UNIT_SYSTEM', 'metric')
    
    # Parse stations from environment
    stations_json = os.getenv('STATIONS', '[]')
    try:
        stations_data = json.loads(stations_json)
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing STATIONS JSON: {e}")
        return
    
    if not stations_data:
        print("❌ Error: No stations configured in .env file")
        return
    
    # Create station configs
    stations = []
    for station_data in stations_data:
        station = StationConfig(
            pws_id=station_data['pws_id'],
            name=station_data['name'],
            priority=station_data['priority']
        )
        stations.append(station)
    
    print(f"🔧 Configuration:")
    print(f"   Group: {group_name}")
    print(f"   Language: {language}")
    print(f"   Unit System: {unit_system}")
    print(f"   Stations: {len(stations)}")
    print()
    
    # Test the stations
    async with StandaloneMultiStationTester(api_key, stations, language, unit_system) as tester:
        data = await tester.test_all_stations()
        tester.print_summary()
        
        if data:
            print("\n🎉 Test completed successfully!")
            print("   At least one station is working correctly.")
        else:
            print("\n💥 Test failed!")
            print("   No stations are working. Check your configuration.")

if __name__ == "__main__":
    # Check required packages
    try:
        import aiohttp
        from dotenv import load_dotenv
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("   Install with: pip install aiohttp python-dotenv")
        sys.exit(1)
    
    asyncio.run(main())
