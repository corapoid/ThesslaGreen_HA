"""Configure the optional recuperator power sensor."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.selector import selector

from .particle import is_particle
from .const import CONF_RECUPERATOR_MODEL, CONF_FILTER_CONTROL, DEVICE_AIRPACK4, DEVICE_REKUPERATOR, FILTER_CONTROLS, device_type

DISPLAY_KEY = "Sensor poboru mocy (W lub kW)"
POWER_SENSOR = "sensor_power"
ACCEPTED_UNITS = {"w", "watt", "kw"}


class ThesslaGreenOptionsFlowHandler(config_entries.OptionsFlow):
    """Options flow for Thessla Green integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        if is_particle(self._entry):
            if user_input is not None:
                return self.async_create_entry(title="", data={})
            return self.async_show_form(step_id="init", data_schema=vol.Schema({}))

        errors = {}
        if user_input is not None:
            entity_id = user_input.get(POWER_SENSOR, user_input.get(DISPLAY_KEY))
            if entity_id:
                state = self.hass.states.get(entity_id)
                if state is None:
                    errors[POWER_SENSOR] = "entity_not_found"
                elif (state.attributes.get("unit_of_measurement") or "").strip().lower() not in ACCEPTED_UNITS:
                    errors[POWER_SENSOR] = "invalid_power_unit"
            if not errors:
                options = dict(self._entry.options)
                options.pop(POWER_SENSOR, None)
                if entity_id:
                    options[POWER_SENSOR] = entity_id
                for key in (CONF_RECUPERATOR_MODEL, CONF_FILTER_CONTROL):
                    if key in user_input:
                        options[key] = user_input[key]
                return self.async_create_entry(title="", data=options)

        defaults = {}
        if entity_id := self._entry.options.get(POWER_SENSOR):
            defaults["default"] = entity_id
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_RECUPERATOR_MODEL, default=device_type(self._entry)):
                    vol.In({DEVICE_REKUPERATOR: "Rekuperator — profil ogólny", DEVICE_AIRPACK4: "AirPack4 300h"}),
                vol.Optional(CONF_FILTER_CONTROL, default=self._entry.options.get(CONF_FILTER_CONTROL, "unknown")):
                    vol.In(FILTER_CONTROLS),
                vol.Optional(POWER_SENSOR, **defaults): selector({
                    "entity": {"domain": "sensor", "device_class": "power"},
                }),
            }),
            errors=errors,
        )
