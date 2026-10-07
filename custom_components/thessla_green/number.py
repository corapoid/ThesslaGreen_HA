from __future__ import annotations
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from . import DOMAIN
from .coordinator import ThesslaGreenCoordinator
from .particle import is_particle, particle_entities
from .entity import ModbusEntity, integer_setting
from .airpack4 import is_airpack4, airpack4_entities

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    modbus_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ThesslaGreenCoordinator = modbus_data["coordinator"]
    slave = modbus_data["slave"]
    if is_airpack4(entry):
        async_add_entities(airpack4_entities("number", coordinator, entry))
        return
    if is_particle(entry):
        async_add_entities(particle_entities("number", coordinator, entry))
        return

    async_add_entities([
        RekuperatorPredkoscNumber(coordinator=coordinator, slave=slave)
    ])


class RekuperatorPredkoscNumber(ModbusEntity, NumberEntity):
    """Representation of Rekuperator Prędkość as NumberEntity."""

    def __init__(self, coordinator: ThesslaGreenCoordinator, slave: int):
        super().__init__(coordinator)
        self._address = 4210
        self._slave = slave
        self._attr_name = "Rekuperator Prędkość"
        self._attr_native_unit_of_measurement = "%"
        self._attr_native_min_value = 10
        self._attr_native_max_value = 100
        self._attr_native_step = 1
        self._attr_unique_id = f"thessla_number_{slave}_{self._address}"

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
    def native_value(self) -> float | None:
        """Return the current speed value."""
        return self.coordinator.safe_data.holding.get(self._address)

    async def async_set_native_value(self, value: float) -> None:
        """Write speed value to the device."""
        await self._async_write_register(self._address, integer_setting(value, 10, 100))
