from __future__ import annotations
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from . import DOMAIN
from .coordinator import ThesslaGreenCoordinator
from .particle import is_particle, particle_entities
from .entity import ModbusEntity
from .airpack4 import is_airpack4, airpack4_entities

_LOGGER = logging.getLogger(__name__)

SWITCHES = [
    {"name": "Rekuperator bypass", "address": 4320, "command_on": 0, "command_off": 1, "verify": True},
    {"name": "Rekuperator ON/OFF", "address": 4387, "command_on": 1, "command_off": 0, "verify": True},
    {"name": "Rekuperator mode", "address": 4208, "command_on": 0, "command_off": 1, "verify": True},
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switches."""
    modbus_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ThesslaGreenCoordinator = modbus_data["coordinator"]
    slave = modbus_data["slave"]
    if is_airpack4(entry):
        async_add_entities(airpack4_entities("switch", coordinator, entry))
        return
    if is_particle(entry):
        async_add_entities(particle_entities("switch", coordinator, entry))
        return

    entities = [
        ModbusSwitch(coordinator=coordinator, slave=slave, **sw)
        for sw in SWITCHES
    ]

    async_add_entities(entities)

class ModbusSwitch(ModbusEntity, SwitchEntity):
    """Representation of a Modbus-based switch."""

    def __init__(
        self,
        coordinator: ThesslaGreenCoordinator,
        name: str,
        address: int,
        command_on: int,
        command_off: int,
        verify: bool = False,
        slave: int = 1,
    ):
        super().__init__(coordinator)
        self._address = address
        self._command_on = command_on
        self._command_off = command_off
        self._verify = verify
        self._slave = slave

        self._attr_name = name
        self._attr_unique_id = f"thessla_switch_{slave}_{address}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{slave}")},
            "name": "Rekuperator Thessla",
            "manufacturer": "Thessla Green",
            "model": "Modbus Rekuperator",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        value = self.coordinator.safe_data.holding.get(self._address)
        if value is None:
            return None
        return value == self._command_on

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_write_register(self._address, self._command_on)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_write_register(self._address, self._command_off)
