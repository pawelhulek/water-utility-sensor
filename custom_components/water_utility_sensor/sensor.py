"""Platform for sensor integration."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD, UnitOfVolume, EntityCategory
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .providers import ProviderRegistry, WaterReading, AccountBalance

if TYPE_CHECKING:
    pass

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(hours=8)


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities,
):
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]
    provider_id = config_entry.data.get("provider", "wodkan_krzeszowice")

    async_add_entities(
        [
            WaterMeterSensor(username, password, provider_id, config_entry.entry_id),
            AccountBalanceSensor(username, password, provider_id, config_entry.entry_id),
        ],
        update_before_add=False
    )


class WaterMeterSensor(SensorEntity):
    """Water meter sensor."""
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, username: str, password: str, provider_id: str, entry_id: str) -> None:
        self._attr_unique_id = f"water_meter_{provider_id}_{username}"
        self._attr_translation_key = "water_meter_reading"
        self._state: WaterReading | None = None
        self.username = username
        self.password = password
        self.provider_id = provider_id
        self.entry_id = entry_id

    @property
    def name(self) -> str:
        return "Water Meter Reading"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self.provider_id}_{self.username}")},
            "name": f"Water Meter {self.username}",
            "manufacturer": "Water Utility",
        }

    @property
    def available(self) -> bool:
        return self._state is not None

    @property
    def native_value(self):
        if self._state is None:
            return None
        return self._state.current_reading

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._state is not None:
            attrs["meter_number"] = self._state.meter_number
            attrs["previous_reading"] = self._state.previous_reading
            attrs["consumption"] = self._state.consumption
            attrs["last_update"] = self._state.timestamp.isoformat()
        return attrs

    async def async_update(self) -> None:
        try:
            _LOGGER.debug(f"WaterMeterSensor async_update called for {self.username}")

            provider_class = ProviderRegistry.get(self.provider_id)
            if not provider_class:
                _LOGGER.error(f"Unknown provider: {self.provider_id}")
                return

            provider = provider_class(self.username, self.password)
            reading = await self.hass.async_add_executor_job(provider.get_current_reading)

            _LOGGER.debug(f"WaterMeterSensor got reading: {reading}")
            self._state = reading

        except Exception as e:
            _LOGGER.error(f"Error updating WaterMeterSensor: {e}")


class AccountBalanceSensor(SensorEntity):
    """Account balance sensor."""
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = "PLN"
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, username: str, password: str, provider_id: str, entry_id: str) -> None:
        self._attr_unique_id = f"water_balance_{provider_id}_{username}"
        self._attr_translation_key = "account_balance"
        self._state: AccountBalance | None = None
        self.username = username
        self.password = password
        self.provider_id = provider_id
        self.entry_id = entry_id

    @property
    def name(self) -> str:
        return "Account Balance"

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self.provider_id}_{self.username}")},
            "name": f"Water Meter {self.username}",
            "manufacturer": "Water Utility",
        }

    @property
    def available(self) -> bool:
        return self._state is not None

    @property
    def native_value(self):
        if self._state is None:
            return None
        return self._state.amount

    @property
    def extra_state_attributes(self):
        attrs = {}
        if self._state is not None:
            attrs["status"] = self._state.status
        return attrs

    async def async_update(self) -> None:
        try:
            _LOGGER.debug(f"AccountBalanceSensor async_update called for {self.username}")

            provider_class = ProviderRegistry.get(self.provider_id)
            if not provider_class:
                _LOGGER.error(f"Unknown provider: {self.provider_id}")
                return

            provider = provider_class(self.username, self.password)
            balance = await self.hass.async_add_executor_job(provider.get_account_balance)

            _LOGGER.debug(f"AccountBalanceSensor got balance: {balance}")
            self._state = balance

        except Exception as e:
            _LOGGER.error(f"Error updating AccountBalanceSensor: {e}")
