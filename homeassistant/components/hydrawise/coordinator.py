"""DataUpdateCoordinator for the Hydrawise integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from pydrawise import HydrawiseBase
from pydrawise.schema import Controller, LocalizedValueType, Sensor, User, Zone

from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util.dt import DEFAULT_TIME_ZONE
from homeassistant.util.unit_conversion import VolumeConverter

from .const import DOMAIN, LOGGER


@dataclass
class DailyWaterUse:
    """Container for daily water use data."""

    active: float
    non_active: float


@dataclass
class HydrawiseData:
    """Container for data fetched from the Hydrawise API."""

    user: User
    controllers: dict[int, Controller]
    zones: dict[int, Zone]
    sensors: dict[int, Sensor]
    daily_water_use: dict[int, DailyWaterUse]


class HydrawiseDataUpdateCoordinator(DataUpdateCoordinator[HydrawiseData]):
    """The Hydrawise Data Update Coordinator."""

    api: HydrawiseBase

    def __init__(
        self, hass: HomeAssistant, api: HydrawiseBase, scan_interval: timedelta
    ) -> None:
        """Initialize HydrawiseDataUpdateCoordinator."""
        super().__init__(hass, LOGGER, name=DOMAIN, update_interval=scan_interval)
        self.api = api

    def _to_gallons(self, value: LocalizedValueType) -> float:
        return VolumeConverter.convert(
            value.value,
            value.unit,
            UnitOfVolume.GALLONS,
        )

    async def _async_update_daily_water_use(
        self,
        controller: Controller,
        sensor: Sensor,
        daily_water_use: dict[int, DailyWaterUse],
    ) -> None:
        """Update the daily water use."""
        start_time = datetime.now(DEFAULT_TIME_ZONE).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        end_time = datetime.now(DEFAULT_TIME_ZONE)

        # fetch the watering report with info per zone
        watering_report = await self.api.get_watering_report(
            controller,
            start_time,
            end_time,
        )
        total_active_use = 0.0
        for entry in watering_report:
            if (
                entry.run_event is not None
                and entry.run_event.zone is not None
                and entry.run_event.reported_water_usage is not None
            ):
                active_use = self._to_gallons(entry.run_event.reported_water_usage)
                total_active_use += active_use
                daily_water_use.setdefault(
                    entry.run_event.zone.id, DailyWaterUse(0.0, 0.0)
                )
                daily_water_use[entry.run_event.zone.id].active += active_use

        # Fetch the total water summary.
        water_flow_summary = await self.api.get_water_flow_summary(
            controller,
            sensor,
            start_time,
            end_time,
        )
        total_use = self._to_gallons(water_flow_summary.total_water_volume)
        daily_water_use[controller.id] = DailyWaterUse(
            total_use if total_use > total_active_use else total_active_use,
            total_use - total_active_use if total_use > total_active_use else 0.0,
        )

    async def _async_update_data(self) -> HydrawiseData:
        """Fetch the latest data from Hydrawise."""
        user = await self.api.get_user()
        controllers = {}
        zones = {}
        sensors = {}
        daily_water_use: dict[int, DailyWaterUse] = {}
        for controller in user.controllers:
            controllers[controller.id] = controller
            for zone in controller.zones:
                zones[zone.id] = zone
            for sensor in controller.sensors:
                sensors[sensor.id] = sensor
                if "flow meter" in sensor.model.name.lower():
                    await self._async_update_daily_water_use(
                        controller, sensor, daily_water_use
                    )
        return HydrawiseData(
            user=user,
            controllers=controllers,
            zones=zones,
            sensors=sensors,
            daily_water_use=daily_water_use,
        )
