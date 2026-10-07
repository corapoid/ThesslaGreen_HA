"""AirPack4 user-defined controller name."""

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .airpack4 import AirpackEntity, is_airpack4
from .const import DOMAIN

ALLOWED_CHARACTERS = set("0123456789ABCDEFGHIJKLMNOPRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,:-_^&*() ")


class AirpackNameText(AirpackEntity, TextEntity):
    _attr_native_min = 0
    _attr_native_max = 16
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "device_name", "Nazwa w sterowniku", 8144)

    @property
    def available(self):
        return super().available and all(address in self.coordinator.safe_data.holding for address in range(8144, 8152))

    @property
    def native_value(self):
        registers = self.coordinator.safe_data.holding
        if not all(address in registers for address in range(8144, 8152)):
            return None
        data = b"".join(registers[address].to_bytes(2, "big") for address in range(8144, 8152))
        return data.split(b"\0", 1)[0].decode("ascii", errors="replace")

    async def async_set_value(self, value):
        if len(value) > 16 or any(character not in ALLOWED_CHARACTERS for character in value):
            raise HomeAssistantError("Use at most 16 characters supported by the AirPack panel")
        data = value.encode("ascii").ljust(16, b"\0")
        await self._async_write_registers(8144, [int.from_bytes(data[index:index + 2], "big") for index in range(0, 16, 2)])


async def async_setup_entry(hass, entry, async_add_entities):
    if is_airpack4(entry):
        async_add_entities([AirpackNameText(hass.data[DOMAIN][entry.entry_id]["coordinator"], entry)])
