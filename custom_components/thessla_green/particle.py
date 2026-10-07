"""Particle+ entities using MODBUS_USER_Particle_08.2021.01 registers."""

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .const import CONF_DEVICE_TYPE, DEVICE_PARTICLE, DOMAIN
from .const import PARTICLE_FIRMWARE_REGISTER, PARTICLE_EXTENDED_ALARMS_VERSION
from .entity import ModbusEntity, integer_setting


def is_particle(entry):
    """Entries created before device profiles remain recuperators."""
    return entry.data.get(CONF_DEVICE_TYPE) == DEVICE_PARTICLE


class ParticleEntity(ModbusEntity):
    """Share identity, register access and write error handling."""

    def __init__(self, coordinator, entry, key, name, address):
        super().__init__(coordinator)
        self._address = address
        self._attr_name = f"Particle+ {name}"
        self._attr_unique_id = f"thessla_particle_{entry.entry_id}_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"particle_{entry.entry_id}")},
            "name": "Thessla Green Particle+",
            "manufacturer": "Thessla Green",
            "model": "Particle+500",
        }

    @property
    def available(self):
        return super().available and self.raw_value is not None

    @property
    def raw_value(self):
        return self.coordinator.safe_data.holding.get(self._address)

    async def _write(self, value):
        await self._async_write_register(self._address, value)


class ParticleSensor(ParticleEntity, SensorEntity):
    """Read numeric measurements, including signed differential pressures."""

    _attr_state_class = "measurement"

    def __init__(self, coordinator, entry, key, name, address, unit, signed=False, device_class=None):
        super().__init__(coordinator, entry, key, name, address)
        self._signed = signed
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if address in (4114, 4115):
            self._attr_icon = "mdi:air-filter"
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        value = self.raw_value
        if value is not None and self._signed and value > 0x7FFF:
            return value - 0x10000
        return value

    @property
    def extra_state_attributes(self):
        if self._address in (50, 51):
            return {"particle_type": {0: "PM10", 1: "PM2.5"}.get(
                self.coordinator.safe_data.holding.get(48)
            )}
        return None


class ParticleBinarySensor(ParticleEntity, BinarySensorEntity):
    """Read a status flag or an alarm bit mask."""

    _attr_device_class = "problem"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry, key, name, address, mask=1):
        super().__init__(coordinator, entry, key, name, address)
        self._mask = mask

    @property
    def is_on(self):
        value = self.raw_value
        return None if value is None else bool(value & self._mask)


class ParticleAlarmSensor(ParticleBinarySensor):
    """Combine the original and firmware-dependent alarm tables."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "alarm", "Alarm", 96, 0xFFFF)

    @property
    def available(self):
        firmware = self.coordinator.safe_data.holding.get(PARTICLE_FIRMWARE_REGISTER, 0)
        return super().available and (
            firmware < PARTICLE_EXTENDED_ALARMS_VERSION
            or self.coordinator.safe_data.holding.get(98) is not None
        )

    @property
    def is_on(self):
        if self.raw_value is None:
            return None
        extended = self.coordinator.safe_data.holding.get(98, 0)
        return bool(self.raw_value or extended)


class ParticlePowerSwitch(ParticleEntity, SwitchEntity):
    """Control the documented power register."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "power", "Zasilanie", 16)

    @property
    def is_on(self):
        return None if self.raw_value is None else self.raw_value == 1

    async def async_turn_on(self, **kwargs):
        await self._write(1)

    async def async_turn_off(self, **kwargs):
        await self._write(0)


class ParticleSelect(ParticleEntity, SelectEntity):
    """Control a register with a fixed set of documented values."""

    def __init__(self, coordinator, entry, key, name, address, options):
        super().__init__(coordinator, entry, key, name, address)
        self._options = options
        self._attr_options = list(options)

    @property
    def current_option(self):
        return next((name for name, value in self._options.items() if value == self.raw_value), None)

    async def async_select_option(self, option):
        if option not in self._options:
            raise HomeAssistantError(f"Unknown Particle+ option: {option}")
        await self._write(self._options[option])


class ParticleNumber(ParticleEntity, NumberEntity):
    """Control bounded numeric settings without rounding invalid commands."""

    _attr_native_step = 1

    def __init__(self, coordinator, entry, key, name, address, unit, minimum, maximum):
        super().__init__(coordinator, entry, key, name, address)
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum

    @property
    def native_value(self):
        return self.raw_value

    async def async_set_native_value(self, value):
        await self._write(integer_setting(value, self._attr_native_min_value, self._attr_native_max_value))


def particle_entities(platform, coordinator, entry):
    """Build only entities supported by the Particle+ register map."""
    if platform == "sensor":
        return [ParticleSensor(coordinator, entry, *definition) for definition in (
            ("dust_out", "Stężenie pyłu OUT", 50, "µg/m³"),
            ("dust_in", "Stężenie pyłu IN", 51, "µg/m³"),
            ("pressure_prefilter", "Spadek ciśnienia filtra wstępnego", 33, "Pa", True, "pressure"),
            ("pressure_hepa", "Spadek ciśnienia filtra HEPA", 36, "Pa", True, "pressure"),
            ("automatic_intensity", "Intensywność filtracji automatycznej", 64, "%"),
            ("target", "Obliczona nastawa stężenia pyłu", 56, "µg/m³"),
            ("prefilter_wear", "Zużycie filtra wstępnego", 4114, "%"),
            ("hepa_wear", "Zużycie filtra HEPA", 4115, "%"),
        )]
    if platform == "binary_sensor":
        entities = [ParticleBinarySensor(coordinator, entry, *definition) for definition in (
            ("blocked", "Filtracja wstrzymana", 41),
            ("fan_fault", "Awaria wentylatora", 96, 0x0001),
            ("out_sensor_fault", "Awaria PmSensor OUT", 96, 0x0002),
            ("in_sensor_fault", "Awaria PmSensor IN", 96, 0x0004),
            ("hepa_replace", "Wymiana filtra HEPA", 96, 0x01A0),
            ("prefilter_replace", "Wymiana filtra wstępnego", 96, 0x1A00),
        )]
        entities.insert(1, ParticleAlarmSensor(coordinator, entry))
        if coordinator.safe_data.holding.get(PARTICLE_FIRMWARE_REGISTER, 0) >= PARTICLE_EXTENDED_ALARMS_VERSION:
            entities.extend(ParticleBinarySensor(coordinator, entry, *definition) for definition in (
                ("permission_missing", "Brak zezwolenia na pracę", 98, 0x0001),
                ("prefilter_missing", "Brak filtra wstępnego", 98, 0x0002),
                ("hepa_missing", "Brak filtra HEPA", 98, 0x0004),
            ))
        return entities
    if platform == "switch":
        return [ParticlePowerSwitch(coordinator, entry)]
    if platform == "select":
        return [ParticleSelect(coordinator, entry, *definition) for definition in (
            ("mode", "Tryb pracy", 17, {"Manualny": 0, "Automatyczny": 1}),
            ("particle_type", "Rodzaj pyłu", 48, {"PM10": 0, "PM2.5": 1}),
            ("regulation", "Sposób regulacji", 53, {"Bezwzględny": 0, "Względny": 1}),
        )]
    if platform == "number":
        return [ParticleNumber(coordinator, entry, *definition) for definition in (
            ("manual_intensity", "Intensywność filtracji manualnej", 65, "%", 10, 100),
            ("absolute_target", "Nastawa bezwzględna stężenia pyłu", 54, "µg/m³", 0, 200),
            ("pm10_reference", "Stężenie odniesienia PM10", 52, "µg/m³", 10, 300),
            ("pm25_reference", "Stężenie odniesienia PM2.5", 57, "µg/m³", 10, 300),
        )]
    raise ValueError(f"Unknown Particle+ platform: {platform}")
