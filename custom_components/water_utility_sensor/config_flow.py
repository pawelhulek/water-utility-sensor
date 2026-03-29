"""Config flow for Water Utility Sensor."""
import logging
from typing import Optional, Dict, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, OptionsFlow
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN
from .providers import ProviderRegistry

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL_OPTIONS = [
    (1, "1 hour"),
    (4, "4 hours"),
    (8, "8 hours"),
    (12, "12 hours"),
    (24, "24 hours"),
]


class WaterUtilityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for water utility sensors."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle user input - show credentials directly since there's only one provider."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            provider_id = "wik_krzeszowice"

            if username and password:
                provider_class = ProviderRegistry.get(provider_id)
                if provider_class:
                    try:
                        _LOGGER.info("Attempting login for user: %s", username)
                        provider = provider_class(username, password)
                        login_result = await self.hass.async_add_executor_job(provider.login)
                        _LOGGER.info("Login result: %s", login_result)
                        
                        if not login_result:
                            errors["base"] = "verify_connection_failed"
                        else:
                            await self.async_set_unique_id(f"water_{provider_id}_{username}")
                            self._abort_if_unique_id_configured()
                            
                            return self.async_create_entry(
                                title=f"WODKAN Krzeszowice Water",
                                data={
                                    CONF_USERNAME: username,
                                    CONF_PASSWORD: password,
                                    "provider": provider_id
                                },
                                options={
                                    "update_interval_hours": 8,
                                }
                            )
                    except Exception as e:
                        _LOGGER.exception("Error during config flow: %s", e)
                        errors["base"] = "verify_connection_failed"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
            }),
            errors=errors,
            description_placeholders={"error_info": ""},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return WaterUtilityOptionsFlow(config_entry)


class WaterUtilityOptionsFlow(OptionsFlow):
    """Options flow for water utility sensor."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get("update_interval_hours", 8)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "update_interval_hours",
                    default=current_interval
                ): vol.In({hours: name for hours, name in UPDATE_INTERVAL_OPTIONS}),
            }),
        )
