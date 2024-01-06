"""DataUpdateCoordinator for the Hydrawise integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from pydrawise import HydrawiseBase
from pydrawise.schema import Controller, ControllerWaterUseSummary, Sensor, User, Zone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import DEFAULT_TIME_ZONE

from .const import DOMAIN, LOGGER


@dataclass
class HydrawiseData:
    """Container for data fetched from the Hydrawise API."""

    user: User
    controllers: dict[int, Controller]
    zones: dict[int, Zone]
    sensors: dict[int, Sensor]
    daily_water_use: dict[int, ControllerWaterUseSummary]


class HydrawiseDataUpdateCoordinator(DataUpdateCoordinator[HydrawiseData]):
    """The Hydrawise Data Update Coordinator."""

    api: HydrawiseBase

    def __init__(
        self, hass: HomeAssistant, api: HydrawiseBase, scan_interval: timedelta
    ) -> None:
        """Initialize HydrawiseDataUpdateCoordinator."""
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=scan_interval)
        self.api = api

    async def _async_update_data(self) -> HydrawiseData:
        """Fetch the latest data from Hydrawise."""
        user = await self.api.get_user()
        controllers = {}
        zones = {}
        sensors = {}
        daily_water_use: dict[int, ControllerWaterUseSummary] = {}
        for controller in user.controllers:
            controllers[controller.id] = controller
            for zone in controller.zones:
                zones[zone.id] = zone
            for sensor in controller.sensors:
                sensors[sensor.id] = sensor

            if any(
                "flow meter" in sensor.model.name.lower()
                for sensor in controller.sensors
            ):
                daily_water_use[controller.id] = await self.api.get_water_use_summary(
                    controller,
                    datetime.now(DEFAULT_TIME_ZONE).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    ),
                    datetime.now(DEFAULT_TIME_ZONE),
                )

        return HydrawiseData(
            user=user,
            controllers=controllers,
            zones=zones,
            sensors=sensors,
            daily_water_use=daily_water_use,
        )
