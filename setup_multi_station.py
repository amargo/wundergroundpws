#!/usr/bin/env python3
"""
Setup script for Multi-Station WundergroundPWS integration.
This script helps configure multiple weather stations with fallback support.
"""

import json
import os
import sys
from pathlib import Path

def create_multi_station_config():
    """Create a multi-station configuration."""
    print("=== Multi-Station WundergroundPWS Setup ===")
    print()
    
    # Get API key
    api_key = input("Enter your Weather Underground API key: ").strip()
    if not api_key:
        print("API key is required!")
        return False
    
    # Get group name
    group_name = input("Enter group name (e.g., 'velence'): ").strip()
    if not group_name:
        print("Group name is required!")
        return False
    
    # Get coordinates (optional)
    latitude = input("Enter latitude (optional, will be auto-detected): ").strip()
    longitude = input("Enter longitude (optional, will be auto-detected): ").strip()
    
    stations = []
    print("\nNow add your weather stations:")
    
    while True:
        print(f"\n--- Station {len(stations) + 1} ---")
        pws_id = input("Enter PWS Station ID (e.g., IKPOLN1): ").strip()
        if not pws_id:
            if len(stations) == 0:
                print("At least one station is required!")
                continue
            break
        
        station_name = input(f"Enter friendly name for {pws_id}: ").strip()
        if not station_name:
            station_name = pws_id
        
        while True:
            try:
                priority = int(input(f"Enter priority for {pws_id} (1=highest, 10=lowest): ").strip())
                if 1 <= priority <= 10:
                    break
                print("Priority must be between 1 and 10!")
            except ValueError:
                print("Please enter a valid number!")
        
        stations.append({
            "pws_id": pws_id,
            "name": station_name,
            "priority": priority
        })
        
        add_more = input("\nAdd another station? (y/N): ").strip().lower()
        if add_more not in ['y', 'yes']:
            break
    
    if not stations:
        print("No stations configured!")
        return False
    
    # Create configuration
    config = {
        "api_key": api_key,
        "group_name": group_name,
        "latitude": latitude if latitude else None,
        "longitude": longitude if longitude else None,
        "stations": stations
    }
    
    # Save configuration
    config_file = f"multi_station_{group_name}.json"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\nConfiguration saved to: {config_file}")
    print("\nNext steps:")
    print("1. Copy the custom_components/wundergroundpws folder to your Home Assistant config/custom_components/")
    print("2. Restart Home Assistant")
    print("3. Go to Settings -> Devices & Services -> Add Integration")
    print("4. Search for 'WundergroundPWS Multi-Station'")
    print("5. Use the configuration values from the saved file")
    
    return True

def print_example_lovelace():
    """Print example Lovelace configuration."""
    print("\n=== Example Lovelace Configuration ===")
    print("""
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
        entity: weather.velence  # Your group name
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
""")

if __name__ == "__main__":
    if create_multi_station_config():
        print_example_lovelace()
    else:
        print("Setup failed!")
        sys.exit(1)
