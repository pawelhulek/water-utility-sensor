"""Config flow for Water Utility Sensor."""
from typing import Optional, Dict, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigEntryState
from homeassistant.const import CONF_USERNAME, CONF_PASSWORD

from .const import DOMAIN
from .providers import ProviderRegistry

AUTH_SCHEMA = vol.Schema({
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
})


class WaterUtilityConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for water utility sensors."""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
        errors: Dict[str, str] = {}
        description_placeholders: Dict[str, str] = {"error_info": ""}

        providers = ProviderRegistry.list_providers()

        if len(providers) == 1:
            return await self.async_step_credentials(
                {"provider": providers[0].id}
            )

        if user_input is not None and "provider" in user_input:
            return await self.async_step_credentials(user_input)

        options = [(p.id, p.name) for p in providers]
        
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("provider"): vol.In(dict(options)),
            }),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_credentials(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle credentials input."""
        errors: Dict[str, str] = {}
        description_placeholders: Dict[str, str] = {"error_info": ""}

        if user_input is not None:
            provider_id = user_input.get("provider")
            username = user_input.get(CONF_USERNAME)
            password = user_input.get(CONF_PASSWORD)

            if not provider_id:
                errors["base"] = "unknown_provider"
            else:
                provider_class = ProviderRegistry.get(provider_id)
                if not provider_class:
                    errors["base"] = "unknown_provider"
                else:
                    try:
                        provider = provider_class(username, password)
                        await self.hass.async_add_executor_job(provider.login)
                        
                        await self.async_set_unique_id(f"water_{provider_id}_{username}")
                        self._abort_if_unique_id_configured()
                        
                        return self.async_create_entry(
                            title=f"{provider_class(username, password).info.name} Water",
                            data={
                                CONF_USERNAME: username,
                                CONF_PASSWORD: password,
                                "provider": provider_id
                            }
                        )
                    except Exception:
                        errors["base"] = "verify_connection_failed"
                        description_placeholders["error_info"] = "Login Failed"

        step_data = {}
        if user_input and "provider" in user_input:
            step_data["provider"] = user_input["provider"]

        schema_dict: Dict[str, Any] = {
            vol.Required(CONF_USERNAME): cv.string,
            vol.Required(CONF_PASSWORD): cv.string,
        }
        if "provider" in step_data:
            schema_dict["provider"] = vol.Hidden()

        return self.async_show_form(
            step_id="credentials",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_reauth(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle reauthentication."""
        errors: Dict[str, str] = {}
        description_placeholders: Dict[str, str] = {"error_info": ""}
        
        entry_id = self.context.get("entry_id")
        
        if user_input is not None and entry_id:
            config_entry = self.hass.config_entries.async_get_entry(entry_id)
            if config_entry:
                provider_id = config_entry.data.get("provider", "wodkan_krzeszowice")
                provider_class = ProviderRegistry.get(provider_id)
                
                if provider_class:
                    try:
                        provider = provider_class(
                            user_input[CONF_USERNAME],
                            user_input[CONF_PASSWORD]
                        )
                        await self.hass.async_add_executor_job(provider.login)
                        
                        if config_entry.state == ConfigEntryState.SETUP_ERROR:
                            self.hass.config_entries.async_update_entry(
                                config_entry,
                                data={**config_entry.data, **user_input},
                            )
                            await self.hass.config_entries.async_reload(entry_id)
                        
                        return self.async_abort(reason="reauth_successful")
                    except Exception:
                        errors["base"] = "verify_connection_failed"
                        description_placeholders["error_info"] = "Login Failed"
        
        return self.async_show_form(
            step_id="reauth",
            data_schema=AUTH_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    async def async_step_reconfigure(self, user_input: Optional[Dict[str, Any]] = None):
        """Handle reconfiguration."""
        errors: Dict[str, str] = {}
        description_placeholders: Dict[str, str] = {"error_info": ""}
        
        entry_id = self.context.get("entry_id")
        config_entry = self.hass.config_entries.async_get_entry(entry_id) if entry_id else None
        
        if config_entry is None:
            return self.async_abort(reason="no_config_entry")
        
        if user_input is not None:
            provider_id = config_entry.data.get("provider", "wodkan_krzeszowice")
            provider_class = ProviderRegistry.get(provider_id)
            
            if provider_class:
                try:
                    provider = provider_class(
                        user_input[CONF_USERNAME],
                        user_input[CONF_PASSWORD]
                    )
                    await self.hass.async_add_executor_job(provider.login)
                    
                    self.hass.config_entries.async_update_entry(
                        config_entry,
                        data={**config_entry.data, **user_input},
                    )
                    await self.hass.config_entries.async_reload(config_entry.entry_id)
                    
                    return self.async_abort(reason="reconfigure_successful")
                except Exception:
                    errors["base"] = "verify_connection_failed"
                    description_placeholders["error_info"] = "Login Failed"
        
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=AUTH_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders,
        )
