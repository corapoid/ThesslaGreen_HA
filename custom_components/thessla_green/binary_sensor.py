from __future__ import annotations
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

from . import DOMAIN
from .coordinator import ThesslaGreenCoordinator
from .particle import is_particle, particle_entities
from .entity import ModbusEntity
from .airpack4 import is_airpack4, airpack4_entities

_LOGGER = logging.getLogger(__name__)

BINARY_SENSORS = [
    # Odczyt z COILS
    {"name": "Rekuperator Silownik bypassu", "address": 9, "input_type": "coil", "icon_on": "mdi:valve-open", "icon_off": "mdi:valve-closed"},
    {"name": "Rekuperator Zasilanie wentylatorów", "address": 11, "input_type": "coil", "icon_on": "mdi:power-plug", "icon_off": "mdi:power-plug-off"},

    # Odczyt z HOLDING REGISTERS
    {"name": "Rekuperator Alarm", "address": 8192, "input_type": "holding", "device_class": "problem"},
    {"name": "Rekuperator Awaria CF Nawiewu", "address": 8330, "input_type": "holding", "device_class": "problem"},
    {"name": "Rekuperator Awaria CF Wywiewu", "address": 8331, "input_type": "holding", "device_class": "problem"},
    {"name": "Rekuperator Awaria Wentylatora Nawiewu", "address": 8222, "input_type": "holding", "device_class": "problem"},
    {"name": "Rekuperator Awaria Wentylatora Wywiewu", "address": 8223, "input_type": "holding", "device_class": "problem"},

    {"name": "Rekuperator Automatyka bypassu", "address": 4320, "input_type": "holding", "on_value": 0, "icon_on": "mdi:autorenew", "icon_off": "mdi:cancel"},

    {"name": "Rekuperator Error", "address": 8193, "input_type": "holding", "device_class": "problem"},
    {"name": "Rekuperator fpx flaga", "address": 4192, "input_type": "holding", "icon_on": "mdi:flag", "icon_off": "mdi:flag-outline"},
    {"name": "Rekuperator FPX aktywny", "address": 4198, "input_type": "holding", "on_values": (1, 2), "icon_on": "mdi:fan-alert", "icon_off": "mdi:fan"},
    {"name": "Rekuperator FPX zabezpieczenie termiczne", "address": 8208, "input_type": "holding", "device_class": "safety"},
    {"name": "Rekuperator lato zima", "address": 4209, "input_type": "holding", "icon_on": "mdi:sun-thermometer", "icon_off": "mdi:snowflake"},
    {"name": "Rekuperator Wymiana Filtrów", "address": 8444, "input_type": "holding", "icon_on": "mdi:air-filter", "icon_off": "mdi:fan-alert"},
    {"name": "Rekuperator Status ERV", "address": 4704, "input_type": "holding", "on_value": 1, "icon_on": "mdi:radiator", "icon_off": "mdi:radiator-off"},
]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    modbus_data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ThesslaGreenCoordinator = modbus_data["coordinator"]
    slave = modbus_data["slave"]
    if is_airpack4(entry):
        async_add_entities(airpack4_entities("binary_sensor", coordinator, entry))
        return
    if is_particle(entry):
        async_add_entities(particle_entities("binary_sensor", coordinator, entry))
        return

    entities = [
        ModbusBinarySensor(coordinator=coordinator, slave=slave, **sensor)
        for sensor in BINARY_SENSORS
    ]

    async_add_entities(entities)


class ModbusBinarySensor(ModbusEntity, BinarySensorEntity):
    """Representation of a Modbus binary sensor."""

    def __init__(
        self,
        coordinator: ThesslaGreenCoordinator,
        name: str,
        address: int,
        input_type: str = "coil",
        slave: int = 1,
        device_class: str | None = None,
        icon_on: str | None = None,
        icon_off: str | None = None,
        on_value: int | None = None,
        on_values: tuple[int, ...] | None = None,
    ):
        super().__init__(coordinator)
        self._attr_name = name
        self._address = address
        self._input_type = input_type
        self._slave = slave
        self._icon_on = icon_on
        self._icon_off = icon_off

        # Jeśli nie podano, przyjmij standard: 1 = ON
        self._on_value = 1 if on_value is None else on_value
        self._on_values = on_values

        self._attr_unique_id = f"thessla_binary_sensor_{slave}_{address}"
        self._attr_device_class = device_class

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
        """Return true if the binary sensor is on."""
        if self._input_type == "coil":
            val = self.coordinator.safe_data.coil.get(self._address)
            if val is None:
                return None
            return int(bool(val)) == self._on_value

        elif self._input_type == "holding":
            value = self.coordinator.safe_data.holding.get(self._address)
            if value is None:
                return None
            return value in self._on_values if self._on_values is not None else value == self._on_value

        _LOGGER.error("Unknown input_type '%s' for %s", self._input_type, self._attr_name)
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon to use."""
        if self.is_on is None:
            return None
        return self._icon_on if self.is_on else self._icon_off
