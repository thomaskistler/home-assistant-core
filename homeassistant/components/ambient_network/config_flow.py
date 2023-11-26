"""Config flow for the Ambient Weather Network integration."""
from __future__ import annotations

import logging
import re
from typing import Any

from aioambient import OpenAPI
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    LocationSelector,
    LocationSelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    API_STATION_INFO,
    API_STATION_MAC_ADDRESS,
    API_STATION_NAME,
    CONFIG_LOCATION,
    CONFIG_LOCATION_LATITUDE,
    CONFIG_LOCATION_LONGITUDE,
    CONFIG_LOCATION_RADIUS,
    CONFIG_LOCATION_RADIUS_DEFAULT,
    CONFIG_MNEMONIC,
    CONFIG_STATION,
    CONFIG_STEP_MNEMONIC,
    CONFIG_STEP_STATION,
    CONFIG_STEP_USER,
    DOMAIN,
    ENTITY_MAC_ADDRESS,
    ENTITY_MNEMONIC,
    ENTITY_NAME,
    METERS_TO_MILES,
    MILES_TO_METERS,
)

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow for the Ambient Weather Network integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Construct the config flow."""
        super().__init__()
        self._longitude: float = 0.0
        self._latitude: float = 0.0
        self._radius: float = 0.0
        self._mac_address: str = "00:00:00:00:00:00:00:00"
        self._name: str = "Unknown"
        self._mnemonic: str = "UKNW"

    def create_mnemonic(self, text: str) -> str:
        """Create a four-letter mnemonic from a text string.

        Args:
            text: string to create the mnemonic for

        Returns:
            Four letter mnemonic
        """
        # Split the text by spaces
        words: list[str] = text.split()

        # Process each word
        mnemonic: str = ""
        for word in words:
            # Use regular expression to split the word between uppercase and lowercase letters
            parts: list[str] = re.findall(
                r"[a-z][a-z0-9\-]+|[A-Z][a-z0-9\-]+|[A-Z][A-Z0-9\-]+", word
            )

            for part in parts:
                match: re.Match | None = re.match(r"([a-zA-Z]+)[\-0-9]", part)
                if match is not None:
                    # Take all the letters preceding the dash or numbers
                    mnemonic += match.group(1).upper()
                else:
                    # Take the first letter from each part
                    mnemonic += part[0].upper()

        # Ensure the mnemonic is exactly four letters long
        mnemonic = mnemonic[:4]

        return mnemonic

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step to select the location.

        Args:
            user_input: Step input

        Returns:
            Flow result
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            self._latitude = user_input[CONFIG_LOCATION][CONFIG_LOCATION_LATITUDE]
            self._longitude = user_input[CONFIG_LOCATION][CONFIG_LOCATION_LONGITUDE]
            self._radius = (
                user_input[CONFIG_LOCATION][CONFIG_LOCATION_RADIUS] * METERS_TO_MILES
            )
            return await self.async_step_station()

        schema: vol.Schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required(
                        CONFIG_LOCATION,
                    ): LocationSelector(LocationSelectorConfig(radius=True)),
                }
            ),
            {
                CONFIG_LOCATION: {
                    CONFIG_LOCATION_LATITUDE: self.hass.config.latitude,
                    CONFIG_LOCATION_LONGITUDE: self.hass.config.longitude,
                    CONFIG_LOCATION_RADIUS: CONFIG_LOCATION_RADIUS_DEFAULT
                    * MILES_TO_METERS,
                }
            },
        )

        return self.async_show_form(
            step_id=CONFIG_STEP_USER,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_station(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the second step to select the station.

        Args:
            user_input: Step input

        Returns:
            Flow result
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            (
                self._mac_address,
                self._mnemonic,
                self._name,
            ) = user_input[
                CONFIG_STATION
            ].split(",")
            await self.async_set_unique_id(self._mac_address)
            self._abort_if_unique_id_configured()
            return await self.async_step_mnemonic()

        client: OpenAPI = OpenAPI()
        stations: list[dict[str, Any]] = await client.get_devices_by_location(
            self._latitude, self._longitude, radius=self._radius
        )

        if len(stations) == 0:
            return self.async_abort(reason="no_stations_found")

        options: list[SelectOptionDict] = list[SelectOptionDict]()
        for station in stations:
            name: str = station[API_STATION_INFO][API_STATION_NAME]
            mnemonic: str = self.create_mnemonic(name)
            option: SelectOptionDict = SelectOptionDict(
                label=f"{name} ({mnemonic})",
                value=f"{station[API_STATION_MAC_ADDRESS]},{mnemonic},{name}",
            )
            options.append(option)

        schema: vol.Schema = vol.Schema(
            {
                vol.Required(CONFIG_STATION): SelectSelector(
                    SelectSelectorConfig(
                        options=options,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

        return self.async_show_form(
            step_id=CONFIG_STEP_STATION,
            data_schema=schema,
            errors=errors,
        )

    async def async_step_mnemonic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the third step to assign a mnemonic.

        Args:
            user_input: Step input

        Returns:
            Flow result
        """
        errors: dict[str, str] = {}
        if user_input is not None:
            return self.async_create_entry(
                title=f"{self._name} ({user_input[CONFIG_MNEMONIC]})",
                data={
                    ENTITY_NAME: self._name,
                    ENTITY_MAC_ADDRESS: self._mac_address,
                    ENTITY_MNEMONIC: user_input[CONFIG_MNEMONIC],
                },
            )

        schema: vol.Schema = vol.Schema(
            {vol.Required(CONFIG_MNEMONIC, default=self._mnemonic): str}
        )

        return self.async_show_form(
            step_id=CONFIG_STEP_MNEMONIC,
            data_schema=schema,
            errors=errors,
        )
