"""Config flow for Liberty Rider integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
import re

from .const import (
    DOMAIN, CONF_LANGUAGE, LANGUAGES, CONF_SHARE_URL, BASE_URL,
    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL
)

class LibertyRiderConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Liberty Rider."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            share_url = user_input[CONF_SHARE_URL]
            language = user_input[CONF_LANGUAGE]
            scan_interval = user_input[CONF_SCAN_INTERVAL]

            # Vérifier le format de l'URL
            if not share_url.startswith(BASE_URL):
                errors["base"] = "invalid_url"
            else:
                # Extraire l'ID du trajet de l'URL
                match = re.search(r'/a/([^/]+)', share_url)
                if not match:
                    errors["base"] = "invalid_url_format"
                else:
                    return self.async_create_entry(
                        title="Liberty Rider",
                        data={
                            CONF_SHARE_URL: share_url,
                            CONF_LANGUAGE: language,
                            CONF_SCAN_INTERVAL: scan_interval,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SHARE_URL): str,
                vol.Required(CONF_LANGUAGE, default="fr"): vol.In(LANGUAGES),
                vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
                ),
            }),
            errors=errors,
        )

    async def async_step_options(self, user_input=None) -> FlowResult:
        """Handle options flow."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        options = {
            vol.Required(CONF_LANGUAGE, default=self.config_entry.data.get(CONF_LANGUAGE, "fr")): vol.In(LANGUAGES),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
            ),
        }

        return self.async_show_form(
            step_id="options",
            data_schema=vol.Schema(options),
        ) 