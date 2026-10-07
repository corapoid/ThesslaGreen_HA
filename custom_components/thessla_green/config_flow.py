import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult

from .const import (DOMAIN, CONF_SLAVE, CONF_DEVICE_TYPE, DEVICE_PARTICLE,
                    DEVICE_REKUPERATOR, DEFAULT_PARTICLE_SLAVE)
from .const import DEVICE_AIRPACK4


class ThesslaGreenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Thessla Green."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is not None:
            self._device_type = user_input[CONF_DEVICE_TYPE]
            return await self.async_step_connection()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_DEVICE_TYPE, default=DEVICE_REKUPERATOR):
                    vol.In({DEVICE_REKUPERATOR: "Rekuperator — profil ogólny",
                            DEVICE_AIRPACK4: "AirPack4 300h", DEVICE_PARTICLE: "Particle+"}),
            }),
        )

    async def async_step_connection(self, user_input=None) -> FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(
                f"{self._device_type}_{user_input[CONF_HOST]}_{user_input[CONF_PORT]}_{user_input[CONF_SLAVE]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title={DEVICE_PARTICLE: "Thessla Green Particle+", DEVICE_AIRPACK4: "Thessla Green AirPack4 300h"}.get(self._device_type, "Thessla Green"),
                data={**user_input, CONF_DEVICE_TYPE: self._device_type},
            )

        return self.async_show_form(
            step_id="connection",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_PORT, default=8899): vol.All(vol.Coerce(int), vol.Range(min=1, max=65535)),
                vol.Required(CONF_SLAVE, default=DEFAULT_PARTICLE_SLAVE if self._device_type == DEVICE_PARTICLE else 10): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
                vol.Optional(CONF_SCAN_INTERVAL, default=30): vol.All(vol.Coerce(int), vol.Range(min=1)),
            })
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        """Link to options flow handler."""
        from .options_flow import ThesslaGreenOptionsFlowHandler
        return ThesslaGreenOptionsFlowHandler(config_entry)
