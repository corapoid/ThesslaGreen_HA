"""Modbus mode selectors."""

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import ThesslaGreenCoordinator
from .entity import ModbusEntity
from .particle import is_particle, particle_entities
from .airpack4 import is_airpack4, airpack4_entities

MODES = {"Brak trybu": 0, "Wietrzenie": 7, "Pusty Dom": 11, "Kominek": 2, "Okna": 10}
SEASONS = {"Lato": 0, "Zima": 1}
ERV_MODES = {"ERV nieaktywny": 0, "ERV tryb 1": 1, "ERV tryb 2": 2}
COMFORT_MODES = {"EKO": 0, "KOMFORT": 1}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    if is_airpack4(entry):
        async_add_entities(airpack4_entities("select", coordinator, entry))
        return
    if is_particle(entry):
        async_add_entities(particle_entities("select", coordinator, entry))
        return
    async_add_entities([
        entity_class(coordinator, data["slave"])
        for entity_class in (RekuperatorTrybSelect, RekuperatorSezonSelect,
                             RekuperatorErvTrybSelect, RekuperatorKomfortSelect)
    ])


class _RecuperatorSelect(ModbusEntity, SelectEntity):
    """Share selector logic while retaining existing entity identities."""

    def __init__(self, coordinator, slave, address, name, options, unique_id_prefix):
        super().__init__(coordinator)
        self._address = address
        self._reverse_map = options
        self._value_map = {value: label for label, value in options.items()}
        self._attr_name = name
        self._attr_options = list(options)
        self._attr_unique_id = f"{unique_id_prefix}_{slave}_{address}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{slave}")},
            "name": "Rekuperator Thessla",
            "manufacturer": "Thessla Green",
            "model": "Modbus Rekuperator",
        }

    @property
    def current_option(self):
        return self._value_map.get(self.coordinator.safe_data.holding.get(self._address))

    async def async_select_option(self, option):
        if option not in self._reverse_map:
            raise HomeAssistantError(f"Unknown option: {option}")
        await self._async_write_register(self._address, self._reverse_map[option])


class RekuperatorTrybSelect(_RecuperatorSelect):
    def __init__(self, coordinator: ThesslaGreenCoordinator, slave: int):
        super().__init__(coordinator, slave, 4224, "Rekuperator Tryb", MODES, "thessla_select")


class RekuperatorSezonSelect(_RecuperatorSelect):
    def __init__(self, coordinator: ThesslaGreenCoordinator, slave: int):
        super().__init__(coordinator, slave, 4209, "Rekuperator Sezon", SEASONS, "thessla_sezon_select")


class RekuperatorErvTrybSelect(_RecuperatorSelect):
    def __init__(self, coordinator: ThesslaGreenCoordinator, slave: int):
        super().__init__(coordinator, slave, 4711, "Rekuperator ERV tryb", ERV_MODES, "thessla_erv_select")


class RekuperatorKomfortSelect(_RecuperatorSelect):
    def __init__(self, coordinator: ThesslaGreenCoordinator, slave: int):
        super().__init__(coordinator, slave, 4304, "Rekuperator ECO/KOMFORT", COMFORT_MODES, "thessla_komfort_select")
