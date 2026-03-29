"""Platform for sensor integration."""
from datetime import timedelta
import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, UnitOfVolume, EntityCategory
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import WaterUtilityCoordinator
from .providers import WaterReading, AccountBalance as AccountBalanceData

_LOGGER = logging.getLogger(__name__)

DEFAULT_SCAN_INTERVAL = timedelta(hours=8)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities,
):
    """Set up water utility sensor platform."""
    _LOGGER.info("Setting up water utility sensor platform")

    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    provider_id = config_entry.data.get("provider", "wik_krzeszowice")

    # Get update interval from options or use default
    update_interval = timedelta(
        hours=config_entry.options.get("update_interval_hours", DEFAULT_SCAN_INTERVAL.total_seconds() / 3600)
    )

    coordinator = WaterUtilityCoordinator(
        hass,
        username,
        password,
        provider_id,
        update_interval=update_interval,
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    entities = []

    # Create a sensor for each meter
    for meter_number in coordinator.data.readings:
        entities.append(
            WaterMeterSensor(
                coordinator,
                meter_number,
                config_entry.entry_id,
            )
        )

    # Create balance sensor
    entities.append(
        AccountBalanceSensor(
            coordinator,
            config_entry.entry_id,
        )
    )

    async_add_entities(entities, update_before_add=True)
    _LOGGER.info(f"Created {len(entities)} water utility sensor entities")


class WaterMeterSensor(SensorEntity):
    """Water meter sensor."""

    def __init__(
        self,
        coordinator: WaterUtilityCoordinator,
        meter_number: str,
        entry_id: str,
    ) -> None:
        self.coordinator = coordinator
        self.meter_number = meter_number
        self.entry_id = entry_id

        self._attr_unique_id = f"water_meter_{meter_number}"
        self._attr_name = f"Water Meter {meter_number}"
        self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.entry_id)},
            "name": "Water Utility",
            "manufacturer": "WODKAN Krzeszowice",
            "model": "Water Meter",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        reading = self.coordinator.data.readings.get(self.meter_number)
        if reading is None:
            return None
        return reading.current_reading

    @property
    def extra_state_attributes(self):
        reading = self.coordinator.data.readings.get(self.meter_number)
        attrs = {}
        if reading:
            attrs["meter_number"] = reading.meter_number
            attrs["previous_reading"] = reading.previous_reading
            attrs["consumption"] = reading.consumption
            attrs["last_update"] = reading.timestamp.isoformat()
        return attrs


class AccountBalanceSensor(SensorEntity):
    """Water account balance sensor."""

    def __init__(
        self,
        coordinator: WaterUtilityCoordinator,
        entry_id: str,
    ) -> None:
        self.coordinator = coordinator
        self.entry_id = entry_id

        self._attr_unique_id = f"water_balance"
        self._attr_name = "Water Account Balance"
        self._attr_native_unit_of_measurement = "PLN"
        self._attr_device_class = SensorDeviceClass.MONETARY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.entry_id)},
            "name": "Water Utility",
            "manufacturer": "WODKAN Krzeszowice",
            "model": "Account",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def native_value(self):
        balance = self.coordinator.data.balance
        if balance is None:
            return None
        return balance.amount

    @property
    def extra_state_attributes(self):
        balance = self.coordinator.data.balance
        attrs = {}
        if balance:
            attrs["status"] = balance.status
            attrs["currency"] = "PLN"
        return attrs
