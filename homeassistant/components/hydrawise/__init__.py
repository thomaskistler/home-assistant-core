"""Support for Hydrawise cloud."""


from pydrawise import client
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    CONF_ACCESS_TOKEN,
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, LOGGER, SCAN_INTERVAL
from .coordinator import HydrawiseDataUpdateCoordinator

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_ACCESS_TOKEN): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hunter Hydrawise component."""
    if DOMAIN not in config:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={CONF_API_KEY: config[DOMAIN][CONF_ACCESS_TOKEN]},
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Hydrawise from a config entry."""

    if config_entry.data[CONF_USERNAME] == "" or config_entry.data[CONF_PASSWORD] == "":
        # In order to move to the new GraphQL API, users need to re-authenticate
        # using the username/password instead of the API key.
        raise ConfigEntryAuthFailed

    hydrawise = client.Hydrawise(
        client.Auth(config_entry.data[CONF_USERNAME], config_entry.data[CONF_PASSWORD])
    )

    coordinator = HydrawiseDataUpdateCoordinator(hass, hydrawise, SCAN_INTERVAL)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    if config_entry.version == 1:
        LOGGER.debug("Migrating from version %s", config_entry.version)
        new = {**config_entry.data}
        # Add the new username and password fields.
        new.pop(CONF_API_KEY, None)
        new[CONF_USERNAME] = ""
        new[CONF_PASSWORD] = ""

        config_entry.version = 2
        hass.config_entries.async_update_entry(config_entry, data=new)

        LOGGER.debug("Migration to version %s successful", config_entry.version)

    return True
