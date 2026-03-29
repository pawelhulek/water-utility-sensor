"""Tests for Water Utility Sensor integration."""

from datetime import datetime
from unittest.mock import MagicMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.water_utility_sensor.providers import (
    WaterReading,
    AccountBalance,
    ProviderRegistry,
    WaterProvider,
    ProviderInfo,
)
from custom_components.water_utility_sensor.sensor import WaterMeterSensor, AccountBalanceSensor


class MockProvider(WaterProvider):
    """Mock provider for testing."""

    @property
    def info(self) -> ProviderInfo:
        return ProviderInfo(
            id="mock_provider",
            name="Mock Provider",
            description="Mock water provider for testing",
        )

    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def login(self) -> bool:
        return True

    def get_current_reading(self) -> WaterReading | None:
        return WaterReading(
            timestamp=datetime(2024, 3, 15),
            current_reading=150.5,
            previous_reading=140.0,
            consumption=10.5,
            meter_number="WM12345",
        )

    def get_account_balance(self) -> AccountBalance | None:
        return AccountBalance(
            amount=125.50,
            status="niedopłata",
            meter_number="WM12345",
        )


ProviderRegistry.register(MockProvider)


@pytest.mark.asyncio
async def test_water_meter_sensor_updates_state(hass: HomeAssistant):
    """Test that WaterMeterSensor updates its state correctly."""
    sensor = WaterMeterSensor("testuser", "testpass", "mock_provider", "entry_1")
    sensor.hass = hass

    await sensor.async_update()

    assert sensor.native_value == 150.5
    assert sensor.available is True
    attrs = sensor.extra_state_attributes
    assert attrs["previous_reading"] == 140.0
    assert attrs["consumption"] == 10.5
    assert attrs["meter_number"] == "WM12345"


@pytest.mark.asyncio
async def test_account_balance_sensor_updates_state(hass: HomeAssistant):
    """Test that AccountBalanceSensor updates its state correctly."""
    sensor = AccountBalanceSensor("testuser", "testpass", "mock_provider", "entry_1")
    sensor.hass = hass

    await sensor.async_update()

    assert sensor.native_value == 125.50
    assert sensor.available is True
    attrs = sensor.extra_state_attributes
    assert attrs["status"] == "niedopłata"


@pytest.mark.asyncio
async def test_water_meter_sensor_handles_provider_error(hass: HomeAssistant):
    """Test that WaterMeterSensor handles provider errors gracefully."""
    sensor = WaterMeterSensor("testuser", "testpass", "nonexistent_provider", "entry_1")
    sensor.hass = hass

    await sensor.async_update()

    assert sensor.available is False
    assert sensor.native_value is None


def test_provider_registry_registers_providers():
    """Test that ProviderRegistry correctly registers providers."""
    providers = ProviderRegistry.list_providers()
    provider_ids = [p.id for p in providers]

    assert "mock_provider" in provider_ids
    assert "wik_krzeszowice" in provider_ids


def test_provider_registry_get_returns_class():
    """Test that ProviderRegistry.get returns the correct provider class."""
    provider_class = ProviderRegistry.get("mock_provider")
    assert provider_class is not None
    assert provider_class == MockProvider


def test_provider_registry_get_unknown_returns_none():
    """Test that ProviderRegistry.get returns None for unknown providers."""
    provider_class = ProviderRegistry.get("nonexistent_provider")
    assert provider_class is None


def test_water_reading_dataclass():
    """Test WaterReading dataclass initialization."""
    reading = WaterReading(
        timestamp=datetime(2024, 3, 15),
        current_reading=150.5,
        previous_reading=140.0,
        consumption=10.5,
        meter_number="WM12345",
    )

    assert reading.current_reading == 150.5
    assert reading.previous_reading == 140.0
    assert reading.consumption == 10.5
    assert reading.meter_number == "WM12345"


def test_account_balance_dataclass():
    """Test AccountBalance dataclass initialization."""
    balance = AccountBalance(
        amount=125.50,
        status="niedopłata",
        meter_number="WM12345",
    )

    assert balance.amount == 125.50
    assert balance.status == "niedopłata"
    assert balance.meter_number == "WM12345"
