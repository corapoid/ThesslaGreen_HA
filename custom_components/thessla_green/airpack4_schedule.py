"""BCD clocks and packed intensity/temperature fields in AirPack4 schedules."""

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError

from .airpack4 import AirpackEntity, AirpackNumber, AirpackSwitch

DAYS = ("Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela")


def decode_clock(raw):
    if raw is None or raw in (0xA200, 0x2400):
        return None
    digits = [(raw >> shift) & 15 for shift in (12, 8, 4, 0)]
    if any(digit > 9 for digit in digits):
        return None
    try:
        return time(digits[0] * 10 + digits[1], digits[2] * 10 + digits[3])
    except ValueError:
        return None


def encode_clock(value):
    if not isinstance(value, time) or value.second or value.microsecond or value.tzinfo is not None:
        raise HomeAssistantError("The device clock requires a local time with minute precision")
    return ((value.hour // 10) << 12) | ((value.hour % 10) << 8) | ((value.minute // 10) << 4) | (value.minute % 10)


def periods():
    for season_index, season in enumerate(("summer", "winter")):
        label = "Lato" if season == "summer" else "Zima"
        for day, day_name in enumerate(DAYS):
            for slot in range(4):
                offset = day * 4 + slot
                key = f"{season}_{day}_{slot}"
                name = f"{label} — {day_name} — odcinek {slot + 1}"
                yield key, name, 16 + season_index * 28 + offset, 72 + season_index * 28 + offset, slot


class AirpackTime(AirpackEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    @property
    def native_value(self):
        return decode_clock(self.raw_value)

    async def async_set_value(self, value):
        await self._async_write_register(self._address, encode_clock(value))


class ScheduleEnabledSwitch(AirpackSwitch):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator, entry, key, name, address, disabled, default):
        super().__init__(coordinator, entry, key, name, address, off=disabled)
        self._last_clock = encode_clock(default)

    @property
    def is_on(self):
        value = self.raw_value
        if value is None:
            return None
        if decode_clock(value) is not None:
            self._last_clock = value
            return True
        return False

    async def async_turn_on(self, **kwargs):
        value = self.raw_value
        if decode_clock(value) is not None:
            self._last_clock = value
        await self._async_write_register(self._address, self._last_clock)

    async def async_turn_off(self, **kwargs):
        if decode_clock(self.raw_value) is not None:
            self._last_clock = self.raw_value
        await self._async_write_register(self._address, self._off)


def schedule_times(coordinator, entry):
    entities = [AirpackTime(coordinator, entry, f"{key}_start", f"{name} — początek", address)
                for key, name, address, setting, slot in periods()]
    for season_index, season in enumerate(("summer", "winter")):
        for day, day_name in enumerate(DAYS):
            entities.append(AirpackTime(coordinator, entry, f"{season}_{day}_airing_start",
                                        f"Wietrzenie {'lato' if season == 'summer' else 'zima'} — {day_name}",
                                        128 + (season_index * 7 + day) * 4))
    for key, name, address in (
        ("manual_airing_start", "Wietrzenie manualne — początek", 4219),
        ("filter_check_time", "Kontrola filtrów — godzina", 4433),
        ("gwc_winter_start", "GWC zima — początek regeneracji", 4267),
        ("gwc_winter_stop", "GWC zima — koniec regeneracji", 4268),
        ("gwc_summer_start", "GWC lato — początek regeneracji", 4269),
        ("gwc_summer_stop", "GWC lato — koniec regeneracji", 4270),
    ):
        entities.append(AirpackTime(coordinator, entry, key, name, address))
    return entities


def schedule_numbers(coordinator, entry):
    entities = []
    for key, name, start, address, slot in periods():
        entities.extend([
            AirpackNumber(coordinator, entry, f"{key}_intensity", f"{name} — intensywność", address,
                          "%", 10, 100, packed_shift=8),
            AirpackNumber(coordinator, entry, f"{key}_temperature", f"{name} — temperatura", address,
                          "°C", 10, 45, 0.5, packed_shift=0),
        ])
    return entities


def schedule_switches(coordinator, entry):
    entities = []
    for key, name, address, setting, slot in periods():
        hour = (6, 8, 16, 22)[slot]
        if key.startswith("winter_") and slot == 3 and int(key.split("_")[1]) < 5:
            hour = 23
        entities.append(ScheduleEnabledSwitch(coordinator, entry, f"{key}_enabled", f"{name} — aktywny",
                                              address, 0xA200, time(hour)))
    for season_index, season in enumerate(("summer", "winter")):
        for day, day_name in enumerate(DAYS):
            entities.append(ScheduleEnabledSwitch(coordinator, entry, f"{season}_{day}_airing_enabled",
                                                  f"Wietrzenie {'lato' if season == 'summer' else 'zima'} — {day_name} — aktywne",
                                                  128 + (season_index * 7 + day) * 4, 0x2400, time(17, 45)))
    entities.append(ScheduleEnabledSwitch(coordinator, entry, "manual_airing_enabled", "Wietrzenie manualne — aktywne",
                                          4219, 0x2400, time(12)))
    return entities
