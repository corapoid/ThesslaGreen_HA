"""AirPack4 300h entities for the documented 4.89 user interface."""

from datetime import date, timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.button import ButtonEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .airpack4_registers import ALARMS, NUMBER_SETTINGS, SPECIAL_MODES, WORK_MODES
from .const import CONF_FILTER_CONTROL, DEVICE_AIRPACK4, DOMAIN, device_type
from .entity import ModbusEntity, integer_setting


def is_airpack4(entry):
    return device_type(entry) == DEVICE_AIRPACK4


def temperature(raw):
    if raw == 0x8000:
        return None
    return round((raw - 0x10000 if raw > 0x7FFF else raw) / 10, 1)


def filter_date(raw):
    try:
        return date(2000 + (raw >> 9), (raw >> 5) & 15, raw & 31)
    except ValueError:
        return None


def compilation_date(raw):
    return date(2000, 1, 1) + timedelta(days=raw)


def device_information(data):
    """Report measured versions rather than hard-coding the expected firmware."""
    firmware = None
    if (0 in data.input and 1 in data.input
            and 1 <= data.input[0] <= 99 and 0 <= data.input[1] <= 99):
        firmware = f"{data.input[0]}.{data.input[1]:02d}"
        if (patch := data.input.get(4, 0)) and 0 < patch <= 99:
            firmware += f".{patch}"
    tg02 = None
    if (version := data.holding.get(240)) not in (None, 0, 0xFFFF):
        tg02 = f"{version >> 8}.{version & 255:02d}"
    serial_values = [data.input.get(address) for address in range(24, 30)]
    serial = None
    if (all(value is not None and 0 <= value <= 255 for value in serial_values)
            and any(serial_values)):
        serial = "".join(f"{value:02x}" for value in serial_values)
    return {"model": "AirPack4 300h", "firmware": firmware, "tg02": tg02, "serial": serial}


class AirpackEntity(ModbusEntity):
    def __init__(self, coordinator, entry, key, name, address=None, kind="holding", legacy_id=None):
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._address = address
        self._kind = kind
        slave = entry.data.get("slave", 10)
        self._attr_name = f"Rekuperator {name}"
        self._attr_unique_id = legacy_id or f"thessla_airpack4_{slave}_{key}"

    @property
    def device_info(self):
        information = device_information(self.coordinator.safe_data)
        info = {
            "identifiers": {(DOMAIN, str(self._entry.data.get("slave", 10)))},
            "name": "Thessla Green AirPack4 300h",
            "manufacturer": "Thessla Green", "model": information["model"],
        }
        if information["firmware"]:
            info["sw_version"] = information["firmware"]
        if information["tg02"]:
            info["hw_version"] = f"TG-02 {information['tg02']}"
        if information["serial"]:
            info["serial_number"] = information["serial"]
        return info

    @property
    def raw_value(self):
        return getattr(self.coordinator.safe_data, self._kind).get(self._address)

    @property
    def available(self):
        return super().available and (self._address is None or self.raw_value is not None)


class AirpackSensor(AirpackEntity, SensorEntity):
    def __init__(self, coordinator, entry, key, name, address, kind="holding", unit=None,
                 decoder=None, options=None, legacy_id=None, diagnostic=False):
        super().__init__(coordinator, entry, key, name, address, kind, legacy_id)
        self._decoder = decoder
        self._attr_native_unit_of_measurement = unit
        if options:
            self._attr_device_class = "enum"
            self._attr_options = list(options.values())
            self._decoder = options.get
        elif unit:
            self._attr_state_class = "measurement"
            if unit == "°C":
                self._attr_device_class = "temperature"
            elif unit == "m³/h":
                self._attr_device_class = "volume_flow_rate"
            elif unit == "V":
                self._attr_device_class = "voltage"
        if decoder in (filter_date, compilation_date):
            self._attr_device_class = "date"
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        if self._address is None:
            return device_information(self.coordinator.safe_data)[self._key]
        value = self.raw_value
        return None if value is None else self._decoder(value) if self._decoder else value

    @property
    def available(self):
        return super().available and self.native_value is not None

    @property
    def extra_state_attributes(self):
        if self._key == "model":
            return {
                "profile": "AirPack4 300h / controller 4.89 / TG-02 0.30",
                "unsupported_registers": sorted(
                    f"{kind}: {address}" for kind, address in
                    getattr(self.coordinator.controller, "_unsupported_registers", set())
                ),
            }
        return None


class AirpackBinarySensor(AirpackEntity, BinarySensorEntity):
    def __init__(self, coordinator, entry, key, name, address, kind="holding", on_values=(1,),
                 legacy_id=None, problem=False):
        super().__init__(coordinator, entry, key, name, address, kind, legacy_id)
        self._on_values = on_values
        if problem:
            self._attr_device_class = "problem"
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def is_on(self):
        return None if self.raw_value is None else self.raw_value in self._on_values


class FilterReplacementSensor(AirpackBinarySensor):
    def __init__(self, coordinator, entry):
        slave = entry.data.get("slave", 10)
        super().__init__(coordinator, entry, "filter_replacement", "Wymiana filtrów", 8192,
                         legacy_id=f"thessla_binary_sensor_{slave}_8444", problem=True)

    @property
    def is_on(self):
        registers = self.coordinator.safe_data.holding
        addresses = (8338, 8339, 8340, 8341, 8342, 8343, 8348, 8349)
        if not any(address in registers for address in addresses):
            return None
        return any(registers.get(address, 0) == 1 for address in addresses)

    @property
    def available(self):
        return super().available and self.is_on is not None


class AirpackSwitch(AirpackEntity, SwitchEntity):
    def __init__(self, coordinator, entry, key, name, address, on=1, off=0, legacy_id=None):
        super().__init__(coordinator, entry, key, name, address, legacy_id=legacy_id)
        self._on = on
        self._off = off

    @property
    def is_on(self):
        return None if self.raw_value is None else self.raw_value == self._on

    async def async_turn_on(self, **kwargs):
        await self._async_write_register(self._address, self._on)

    async def async_turn_off(self, **kwargs):
        await self._async_write_register(self._address, self._off)


class FollowModeSwitch(AirpackSwitch):
    """Switch between a documented automatic sentinel and a numeric setting."""

    def __init__(self, coordinator, entry, key, name, address, sentinel):
        super().__init__(coordinator, entry, key, name, address, on=sentinel)
        self._manual = 50
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_turn_on(self, **kwargs):
        if self.raw_value is not None and self.raw_value != self._on:
            self._manual = self.raw_value
        await super().async_turn_on(**kwargs)

    async def async_turn_off(self, **kwargs):
        upper = 100 if self._address == 4239 else 150
        maximum = self.coordinator.safe_data.input.get(277, upper)
        maximum = min(upper, maximum) if 10 <= maximum <= 150 else upper
        if self._address == 4333:
            address = 4118 if self.coordinator.safe_data.holding.get(4263) in (1, 2) else 4117
            calibration = self.coordinator.safe_data.holding.get(address)
            if calibration is not None and 100 <= calibration <= 150:
                maximum = min(maximum, calibration)
        minimum = self.coordinator.safe_data.input.get(276, 10)
        minimum = minimum if 10 <= minimum <= maximum else 10
        await self._async_write_register(self._address, max(minimum, min(self._manual, maximum)))


class AirpackSelect(AirpackEntity, SelectEntity):
    def __init__(self, coordinator, entry, key, name, address, options, legacy_id=None):
        super().__init__(coordinator, entry, key, name, address, legacy_id=legacy_id)
        self._options = options
        self._attr_options = list(options)

    @property
    def current_option(self):
        return next((name for name, value in self._options.items() if value == self.raw_value), None)

    async def async_select_option(self, option):
        if option not in self._options:
            raise HomeAssistantError(f"Unknown option: {option}")
        value = self._options[option]
        if self._address == 4208 and value == 2:
            speed = integer_setting(self.coordinator.safe_data.holding.get(4211), 10, 100)
            await self._async_write_registers(4400, [2, speed, 1])
        else:
            await self._async_write_register(self._address, value)


class AirpackNumber(AirpackEntity, NumberEntity):
    def __init__(self, coordinator, entry, key, name, address, unit, minimum, maximum, scale=1,
                 legacy_id=None, packed_shift=None):
        super().__init__(coordinator, entry, key, name, address, legacy_id=legacy_id)
        self._attr_native_unit_of_measurement = unit
        self._attr_native_min_value = minimum
        self._attr_native_max_value = maximum
        self._attr_native_step = scale
        self._scale = scale
        self._packed_shift = packed_shift
        if address != 4210:
            self._attr_entity_category = EntityCategory.CONFIG
        if packed_shift is not None:
            self._attr_entity_registry_enabled_default = False

    @property
    def native_min_value(self):
        minimum = self._attr_native_min_value
        if self._address in (4232, 4239, 4333):
            limit = self.coordinator.safe_data.input.get(276)
            if limit is not None and minimum <= limit <= self.native_max_value:
                minimum = limit
        return minimum

    @property
    def native_max_value(self):
        maximum = self._attr_native_max_value
        if self._address in (4226, 4227, 4229, 4230, 4231, 4238, 4239, 4333):
            limit = self.coordinator.safe_data.input.get(277)
            if limit is not None and self._attr_native_min_value <= limit <= 150:
                maximum = min(maximum, limit)
            if self._address in (4226, 4227, 4333):
                calibration_address = 4119 if self._address == 4227 else 4117
                if self.coordinator.safe_data.holding.get(4263) in (1, 2):
                    calibration_address += 1
                calibration = self.coordinator.safe_data.holding.get(calibration_address)
                if calibration is not None and 100 <= calibration <= 150:
                    maximum = min(maximum, calibration)
        return maximum

    @property
    def native_value(self):
        raw = self.raw_value
        if raw is None:
            return None
        if self._packed_shift is not None:
            raw = (raw >> self._packed_shift) & 255
        if (self._address == 4239 and raw == 101) or (self._address == 4333 and raw == 151):
            return None
        return raw * self._scale

    async def async_set_native_value(self, value):
        try:
            raw_value = value / self._scale
        except (TypeError, ValueError):
            raise HomeAssistantError(f"Invalid numeric setting: {value}") from None
        raw = integer_setting(raw_value, self.native_min_value / self._scale,
                              self.native_max_value / self._scale)
        if self._packed_shift is not None:
            try:
                success = await self.coordinator.controller.update_register(
                    self._address, 255 << self._packed_shift, raw << self._packed_shift,
                )
            except Exception as error:
                raise HomeAssistantError(f"Unable to update schedule: {error}") from error
            if not success:
                raise HomeAssistantError("Schedule update rejected")
            await self.coordinator.async_request_refresh()
        elif self._address == 4211:
            await self._async_write_registers(4400, [2, raw, 1])
        elif self._address == 4213:
            await self._async_write_registers(4403, [2, raw, 1])
        else:
            await self._async_write_register(self._address, raw)


class AirpackButton(AirpackEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator, entry, key, name, address, value, filter_side=None):
        super().__init__(coordinator, entry, key, name, address)
        self._value = value
        self._filter_side = filter_side

    @property
    def available(self):
        control = self._entry.options.get(CONF_FILTER_CONTROL, "unknown")
        applicable = self._filter_side is None or control == "timer" or (
            self._filter_side == "supply" and control == "afc_exhaust"
        ) or (self._filter_side == "exhaust" and control == "afc_supply")
        return super().available and applicable

    async def async_press(self):
        if not self.available:
            raise HomeAssistantError("This command is unavailable for the configured filter system")
        await self._async_write_register(self._address, self._value)


class ActiveAlarmsSensor(AirpackSensor):
    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "active_alarms", "Aktywne alarmy", 8192, diagnostic=True)

    @property
    def native_value(self):
        active = [code for address, code, name, resettable in ALARMS
                  if self.coordinator.safe_data.holding.get(address) == 1]
        return ", ".join(active) if active else "Brak" if not (
            self.coordinator.safe_data.holding.get(8192) or self.coordinator.safe_data.holding.get(8193)
        ) else "Alarm bez odczytanego kodu"

    @property
    def extra_state_attributes(self):
        return {"alarm_descriptions": {
            code: name for address, code, name, resettable in ALARMS
            if self.coordinator.safe_data.holding.get(address) == 1
        }}


def airpack4_entities(platform, coordinator, entry):
    """Build the model-specific entities while retaining legacy identities."""
    slave = entry.data.get("slave", 10)
    if platform == "sensor":
        entities = [AirpackSensor(coordinator, entry, key, name, None, diagnostic=True)
                    for key, name in (("model", "Model"), ("firmware", "Wersja sterownika"),
                                      ("tg02", "Wersja TG-02"), ("serial", "Numer seryjny"))]
        for key, name, address in (
            ("temperature_outside", "Temperatura czerpni", 16),
            ("temperature_supply", "Temperatura nawiewu", 17),
            ("temperature_exhaust", "Temperatura wywiewu", 18),
            ("temperature_fpx", "Temperatura za FPX", 19),
            ("temperature_duct", "Temperatura kanałowa", 20),
            ("temperature_gwc", "Temperatura GWC", 21),
            ("temperature_ambient", "Temperatura otoczenia centrali", 22),
        ):
            entities.append(AirpackSensor(coordinator, entry, key, name, address, "input", "°C",
                                          temperature, legacy_id=f"thessla_sensor_{slave}_{address}"))
        for key, name, address in (("supply_flow", "Strumień nawiewu", 256), ("exhaust_flow", "Strumień wywiewu", 257)):
            entities.append(AirpackSensor(coordinator, entry, key, name, address, unit="m³/h",
                                          decoder=lambda raw: None if raw == 65535 else raw,
                                          legacy_id=f"thessla_sensor_{slave}_{address}"))
        for key, name, address, options in (
            ("work_mode", "Tryb pracy", 4208, {value: name for name, value in WORK_MODES.items()}),
            ("special_mode", "Funkcja specjalna", 4224, SPECIAL_MODES),
            ("fpx_stage", "Etap FPX", 4198, {0: "OFF", 1: "FPX1", 2: "FPX2"}),
            ("bypass_mode", "Status bypassu", 4330, {0: "Nieaktywny", 1: "Freeheating", 2: "Freecooling"}),
            ("comfort_status", "Status KOMFORT", 4305, {0: "Nieaktywny", 1: "Grzanie", 2: "Chłodzenie"}),
            ("gwc_status", "Status GWC", 4263, {0: "Nieaktywny", 1: "Zima", 2: "Lato"}),
        ):
            entities.append(AirpackSensor(coordinator, entry, key, name, address, options=options))
        entities.append(AirpackSensor(coordinator, entry, "work_mode_code", "Kod trybu pracy", 4208,
                                      legacy_id=f"thessla_sensor_{slave}_4208"))
        for key, name, address, kind, unit in (
            ("manual_speed_state", "Nastawa manualna", 4210, "holding", "%"),
            ("supply_intensity", "Aktualna intensywność nawiewu", 272, "input", "%"),
            ("exhaust_intensity", "Aktualna intensywność wywiewu", 273, "input", "%"),
            ("minimum_intensity", "Minimalna intensywność", 276, "input", "%"),
            ("maximum_intensity", "Maksymalna intensywność", 277, "input", "%"),
            ("supply_filter_wear", "Zużycie filtra nawiewnego", 4482, "holding", "%"),
            ("exhaust_filter_wear", "Zużycie filtra wywiewnego", 4483, "holding", "%"),
            ("stopping_alarm", "Kod alarmu zatrzymującego centralę", 4384, "holding", None),
            ("nominal_supply_flow", "Nominalny strumień nawiewu", 4354, "holding", "m³/h"),
            ("nominal_exhaust_flow", "Nominalny strumień wywiewu", 4355, "holding", "m³/h"),
            ("nominal_supply_flow_gwc", "Nominalny strumień nawiewu GWC", 4356, "holding", "m³/h"),
            ("nominal_exhaust_flow_gwc", "Nominalny strumień wywiewu GWC", 4357, "holding", "m³/h"),
            ("supply_flow_cf", "Strumień nawiewu — TG-02", 274, "input", "m³/h"),
            ("exhaust_flow_cf", "Strumień wywiewu — TG-02", 275, "input", "m³/h"),
        ):
            entities.append(AirpackSensor(coordinator, entry, key, name, address, kind, unit,
                                          legacy_id=f"thessla_sensor_{slave}_4210" if address == 4210 else None))
        entities.extend([
            AirpackSensor(coordinator, entry, "schedule_day", "Dzień harmonogramu", 2, "input",
                          options={index: name for index, name in enumerate(("Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"))}),
            AirpackSensor(coordinator, entry, "schedule_period", "Odcinek harmonogramu", 3, "input",
                          options={index: str(index + 1) for index in range(4)}),
            AirpackSensor(coordinator, entry, "comfort_target", "Aktualna temperatura zadana KOMFORT", 8190,
                          unit="°C", decoder=lambda raw: raw * 0.5 if 20 <= raw <= 90 else None),
            ActiveAlarmsSensor(coordinator, entry),
            AirpackSensor(coordinator, entry, "compiled_date", "Data kompilacji sterownika", 14, "input",
                          decoder=compilation_date, diagnostic=True),
            AirpackSensor(coordinator, entry, "expansion_firmware", "Wersja Expansion", 241,
                          decoder=lambda raw: f"{raw >> 8}.{raw & 255:02d}" if raw not in (0, 0xFFFF) else None,
                          diagnostic=True),
        ])
        for address, key, name in (
            (1280, "supply_voltage", "Napięcie sterowania nawiewem"),
            (1281, "exhaust_voltage", "Napięcie sterowania wywiewem"),
            (1282, "heater_voltage", "Napięcie sterowania nagrzewnicą kanałową"),
            (1283, "cooler_voltage", "Napięcie sterowania chłodnicą kanałową"),
        ):
            entities.append(AirpackSensor(coordinator, entry, key, name, address, unit="V",
                                          decoder=lambda raw: round(raw * 10 / 4095, 2) if raw <= 4095 else None,
                                          diagnostic=True))
        for key, name, address in (("supply_filter_date", "Termin wymiany filtra nawiewnego", 4660),
                                   ("exhaust_filter_date", "Termin wymiany filtra wywiewnego", 4662)):
            entities.append(AirpackSensor(coordinator, entry, key, name, address, decoder=filter_date, diagnostic=True))
        from .sensor import RekuEfficiencySensor, RekuRecoveryPowerSensor, RekuCOPSensor, ModbusUpdateIntervalSensor
        computed = [RekuEfficiencySensor(coordinator, slave), RekuRecoveryPowerSensor(coordinator, slave),
                    RekuCOPSensor(coordinator, slave, entry.options.get("sensor_power")),
                    ModbusUpdateIntervalSensor(coordinator, slave)]
        for entity in computed:
            entity._attr_device_info = entities[0].device_info
            if not isinstance(entity, ModbusUpdateIntervalSensor):
                entity._attr_state_class = "measurement"
        return entities + computed
    if platform == "number":
        entities = [AirpackNumber(coordinator, entry, *row,
                                 legacy_id=f"thessla_number_{slave}_4210" if row[2] == 4210 else None)
                    for row in NUMBER_SETTINGS]
        from .airpack4_schedule import schedule_numbers
        return entities + schedule_numbers(coordinator, entry)
    if platform == "select":
        definitions = (
            ("mode", "Tryb pracy — wybór", 4208, WORK_MODES, None),
            ("special", "Tryb specjalny — wybór", 4224,
             {"Brak trybu": 0, "Wietrzenie": 7, "Pusty Dom": 11, "Kominek": 2, "Okna": 10}, "thessla_select"),
            ("season", "Sezon", 4209, {"Lato": 0, "Zima": 1}, "thessla_sezon_select"),
            ("comfort", "EKO/KOMFORT", 4304, {"EKO": 0, "KOMFORT": 1}, "thessla_komfort_select"),
            ("erv", "ERV — tryb", 4711, {"ERV nieaktywny": 0, "ERV tryb 1": 1, "ERV tryb 2": 2}, "thessla_erv_select"),
            ("bypass", "Bypass — sposób działania", 4331,
             {"Przepustnica": 1, "Różnicowanie strumieni": 2, "Wyłączenie wywiewu": 3}, None),
            ("gwc_regeneration", "GWC — regeneracja", 4262, {"Wyłączona": 0, "Dobowa": 1, "Temperaturowa": 2}, None),
            ("filter_check_day", "Kontrola filtrów — dzień", 4432,
             {day: index for index, day in enumerate(("Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"))}, None),
            ("panel_language", "Język panelu Air++", 4399,
             {"Polski": 0, "English": 1, "Русский": 2, "Українська": 3, "Slovenčina": 4}, None),
        )
        return [AirpackSelect(coordinator, entry, key, name, address, options,
                              f"{prefix}_{slave}_{address}" if prefix else None)
                for key, name, address, options, prefix in definitions]
    if platform == "switch":
        entities = [AirpackSwitch(coordinator, entry, key, name, address, on, off,
                                  f"thessla_switch_{slave}_{address}" if address != 4256 else None)
                    for key, name, address, on, off in (
                        ("power", "Zasilanie", 4387, 1, 0),
                        ("bypass_automatic", "Automatyka bypassu", 4320, 0, 1),
                        ("automatic_mode", "Tryb automatyczny", 4208, 0, 1),
                        ("gwc_enabled", "GWC — zezwolenie", 4256, 0, 1),
                    )]
        entities.extend([
            FollowModeSwitch(coordinator, entry, "window_follow_mode", "Otwarte okna — intensywność z trybu pracy", 4239, 101),
            FollowModeSwitch(coordinator, entry, "bypass_follow_mode", "Bypass — intensywność z trybu pracy", 4333, 151),
        ])
        from .airpack4_schedule import schedule_switches
        return entities + schedule_switches(coordinator, entry)
    if platform == "binary_sensor":
        definitions = (
            ("bypass_actuator", "Siłownik bypassu", 9, "coil", (True,), f"thessla_binary_sensor_{slave}_9"),
            ("work_confirmation", "Potwierdzenie pracy O1", 10, "coil", (True,), None),
            ("fan_power", "Zasilanie wentylatorów", 11, "coil", (True,), f"thessla_binary_sensor_{slave}_11"),
            ("fpx_active", "FPX aktywny", 4198, "holding", (1, 2), f"thessla_binary_sensor_{slave}_4198"),
            ("fpx_flag", "FPX flaga", 4192, "holding", (1,), f"thessla_binary_sensor_{slave}_4192"),
            ("erv_active", "ERV aktywny", 4704, "holding", (1,), f"thessla_binary_sensor_{slave}_4704"),
            ("bypass_active", "Bypass aktywny", 4330, "holding", (1, 2), None),
            ("bypass_permission", "Automatyka bypassu aktywna", 4320, "holding", (0,), f"thessla_binary_sensor_{slave}_4320"),
            ("winter_schedule", "Harmonogram zimowy", 4209, "holding", (1,), f"thessla_binary_sensor_{slave}_4209"),
            ("constant_flow", "Constant Flow aktywny", 271, "input", (1,), None),
            ("gwc_regenerating", "GWC regeneracja aktywna", 4271, "holding", (1,), None),
            ("warnings", "Ostrzeżenia E", 8192, "holding", (1,), f"thessla_binary_sensor_{slave}_8192"),
            ("errors", "Błędy S", 8193, "holding", (1,), f"thessla_binary_sensor_{slave}_8193"),
        )
        entities = [AirpackBinarySensor(coordinator, entry, *row, problem=row[0] in ("warnings", "errors"))
                    for row in definitions]
        for address, key, name in (
            (5, "heater_pump", "Pompa nagrzewnicy kanałowej"),
            (12, "heating_cable", "Kabel grzejny"), (13, "expansion_work", "Potwierdzenie pracy Expansion"),
            (14, "gwc_output", "Wyjście GWC"), (15, "hood_damper", "Przepustnica okapu"),
        ):
            entities.append(AirpackBinarySensor(coordinator, entry, key, name, address, "coil"))
        entities.append(FilterReplacementSensor(coordinator, entry))
        for address, code, name, resettable in ALARMS:
            entity = AirpackBinarySensor(coordinator, entry, f"alarm_{code}", f"{code} — {name}", address,
                                         legacy_id=f"thessla_binary_sensor_{slave}_{address}" if address in (8208, 8222, 8223, 8330, 8331) else None,
                                         problem=True)
            entity._attr_entity_registry_enabled_default = address in (8208, 8222, 8223, 8330, 8331)
            entities.append(entity)
        for address, name in ((0, "Zabezpieczenie nagrzewnicy kanałowej"), (1, "Komunikacja Expansion"),
                              (3, "Presostat filtra kanałowego"), (4, "Wejście okapu"), (5, "Wejście jakości powietrza"),
                              (6, "Wejście higrostatu"), (7, "Wejście wietrzenia"), (10, "AirS wietrzenie"),
                              (11, "AirS bieg 3"), (12, "AirS bieg 2"), (13, "AirS bieg 1"),
                              (14, "Wejście kominka"), (15, "Wejście alarmu pożarowego"),
                              (18, "Presostat filtrów centrali"), (19, "Zabezpieczenie FPX — wejście"), (21, "Wejście pustego domu")):
            entity = AirpackBinarySensor(coordinator, entry, f"input_{address}", name, address, "discrete")
            entity._attr_entity_category = EntityCategory.DIAGNOSTIC
            entity._attr_entity_registry_enabled_default = False
            entities.append(entity)
        return entities
    if platform == "button":
        entities = [AirpackButton(coordinator, entry, *row) for row in (
            ("replace_supply_filter", "Potwierdź wymianę filtra nawiewnego", 8191, 17, "supply"),
            ("replace_exhaust_filter", "Potwierdź wymianę filtra wywiewnego", 8191, 33, "exhaust"),
            ("check_filters", "Uruchom kontrolę filtrów", 13, 65),
            ("stop_filter_check", "Zakończ kontrolę filtrów", 13, 0),
        )]
        for address, code, name, resettable in ALARMS:
            if resettable:
                button = AirpackButton(coordinator, entry, f"reset_{code}", f"Skasuj {code} — {name}", address, 0)
                button._attr_entity_registry_enabled_default = False
                entities.append(button)
        return entities
    if platform == "time":
        from .airpack4_schedule import schedule_times
        return schedule_times(coordinator, entry)
    raise ValueError(f"Unknown AirPack4 platform: {platform}")
