"""Constants for the local_weather integration."""

DOMAIN = "ambient_network"

CONFIG_USER = "user"

CONFIG_STEP_USER = "user"
CONFIG_STEP_STATION = "station"
CONFIG_STEP_MNEMONIC = "mnemonic"

CONFIG_LOCATION = "location"
CONFIG_LOCATION_LATITUDE = "latitude"
CONFIG_LOCATION_LONGITUDE = "longitude"
CONFIG_LOCATION_RADIUS = "radius"
CONFIG_LOCATION_RADIUS_DEFAULT = 0.5  # in miles

CONFIG_STATION = "station"

CONFIG_MNEMONIC = "mnemonic"

METERS_TO_MILES = 0.000621
MILES_TO_METERS = 1.0 / METERS_TO_MILES

ENTITY_NAME = "name"
ENTITY_MAC_ADDRESS = "mac_address"
ENTITY_MNEMONIC = "mnemonic"

API_STATION_INFO = "info"
API_STATION_NAME = "name"
API_STATION_MAC_ADDRESS = "macAddress"
