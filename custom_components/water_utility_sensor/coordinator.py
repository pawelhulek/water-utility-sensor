"""Data coordinator for water utility sensors."""
from datetime import timedelta
import logging
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .providers import ProviderRegistry, WaterReading, AccountBalance

_LOGGER = logging.getLogger(__name__)


class WaterUtilityData:
    """Data container for water utility."""

    def __init__(self):
        self.readings: Dict[str, WaterReading] = {}
        self.balance: Optional[AccountBalance] = None
        self.meters: list = []


class WaterUtilityCoordinator(DataUpdateCoordinator[WaterUtilityData]):
    """Coordinator for water utility data."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        provider_id: str,
        update_interval: timedelta = timedelta(hours=8),
    ):
        self.username = username
        self.password = password
        self.provider_id = provider_id
        
        super().__init__(
            hass,
            _LOGGER,
            name="water_utility",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> WaterUtilityData:
        """Fetch data from the provider."""
        data = WaterUtilityData()
        
        try:
            provider_class = ProviderRegistry.get(self.provider_id)
            if not provider_class:
                raise UpdateFailed(f"Unknown provider: {self.provider_id}")

            # Run in executor to avoid blocking
            def fetch_data():
                provider = provider_class(self.username, self.password)
                
                # Get meter IDs
                meters = provider._get_meter_ids()
                data.meters = meters
                
                # Get readings for each meter
                for meter_id, meter_number in meters:
                    reading = provider.get_current_reading_for_meter(meter_id)
                    if reading:
                        data.readings[meter_number] = reading
                
                # Get account balance
                data.balance = provider.get_account_balance()
                
                return data

            result = await self.hass.async_add_executor_job(fetch_data)
            return result

        except Exception as e:
            raise UpdateFailed(f"Failed to fetch water utility data: {e}") from e
