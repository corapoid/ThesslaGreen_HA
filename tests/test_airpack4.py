"""Protocol-level regressions for AirPack4 300h / firmware 4.89."""

from datetime import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.thessla_green.airpack4 import airpack4_entities, is_airpack4
from custom_components.thessla_green.const import DEVICE_AIRPACK4
from custom_components.thessla_green.modbus_controller import ControllerData
from custom_components.thessla_green.airpack4_schedule import decode_clock


@pytest.fixture
def entry():
    return SimpleNamespace(entry_id="airpack", data={"device_type": DEVICE_AIRPACK4, "slave": 10},
                           options={"filter_control": "timer"})


@pytest.fixture
def coordinator():
    return SimpleNamespace(last_update_success=True, safe_data=ControllerData(
        input={0: 4, 1: 89, 4: 0, 16: 100, 17: 180, 18: 220, 19: 32768, 22: 200,
               24: 0x1A, 25: 0x2B, 26: 0x3C, 27: 0x4D, 28: 0x5E, 29: 0x6F, 276: 10, 277: 120},
        holding={16: 0x0630, 72: 0x1E2C, 240: 0x001E, 256: 65535, 257: 300,
                 4192: 1, 4198: 2, 4208: 1, 4209: 0, 4210: 30, 4211: 40, 4212: 40,
                 4213: 44, 4224: 8, 4320: 0, 4330: 0, 4387: 1, 4704: 1, 4711: 2,
                 8192: 0, 8193: 0, 8191: 4, 8338: 1, 4660: 0x2D62},
        coil={9: False, 10: True, 11: True}, discrete={4: True},
    ), controller=SimpleNamespace(
        write_register=AsyncMock(return_value=True), write_registers=AsyncMock(return_value=True),
        update_register=AsyncMock(return_value=True),
    ), async_request_refresh=AsyncMock())


def entities(platform, coordinator, entry):
    return {entity._key: entity for entity in airpack4_entities(platform, coordinator, entry)
            if hasattr(entity, "_key")}


def test_real_device_information(coordinator, entry):
    sensors = entities("sensor", coordinator, entry)
    assert sensors["model"].native_value == "AirPack4 300h"
    assert sensors["firmware"].native_value == "4.89"
    assert sensors["tg02"].native_value == "0.30"
    assert sensors["serial"].native_value == "1a2b3c4d5e6f"
    info = sensors["model"].device_info
    assert info["model"] == "AirPack4 300h"
    assert info["sw_version"] == "4.89"
    assert info["hw_version"] == "TG-02 0.30"
    assert info["identifiers"] == {("thessla_green", "10")}


def test_temperature_flow_and_states(coordinator, entry):
    sensors = entities("sensor", coordinator, entry)
    assert sensors["temperature_fpx"].native_value is None
    assert not sensors["temperature_fpx"].available
    assert sensors["supply_flow"].native_value is None
    assert sensors["fpx_stage"].native_value == "FPX2"
    assert sensors["special_mode"].native_value == "Wietrzenie — harmonogram automatyczny"
    assert str(sensors["supply_filter_date"].native_value) == "2022-11-02"
    binary = entities("binary_sensor", coordinator, entry)
    assert binary["erv_active"].is_on
    assert binary["fpx_active"].is_on
    assert not binary["bypass_active"].is_on
    assert binary["work_confirmation"].is_on
    assert binary["filter_replacement"].is_on


@pytest.mark.asyncio
async def test_temporary_commands_are_atomic(coordinator, entry):
    numbers = entities("number", coordinator, entry)
    await numbers["temporary_speed"].async_set_native_value(55)
    coordinator.controller.write_registers.assert_awaited_with(4400, [2, 55, 1])
    await numbers["temporary_temperature"].async_set_native_value(21.5)
    coordinator.controller.write_registers.assert_awaited_with(4403, [2, 43, 1])
    with pytest.raises(HomeAssistantError):
        await numbers["manual_speed"].async_set_native_value(0)
    with pytest.raises(HomeAssistantError):
        await numbers["manual_temperature"].async_set_native_value(20.25)


@pytest.mark.asyncio
async def test_schedule_bcd_and_packed_fields(coordinator, entry):
    times = entities("time", coordinator, entry)
    assert times["summer_0_0_start"].native_value == time(6, 30)
    await times["summer_0_0_start"].async_set_value(time(7, 45))
    coordinator.controller.write_register.assert_awaited_with(16, 0x0745)
    with pytest.raises(HomeAssistantError):
        await times["summer_0_0_start"].async_set_value(time(7, 45, 1))
    numbers = entities("number", coordinator, entry)
    await numbers["summer_0_0_intensity"].async_set_native_value(40)
    coordinator.controller.update_register.assert_awaited_with(72, 0xFF00, 40 << 8)
    await numbers["summer_0_0_temperature"].async_set_native_value(23)
    coordinator.controller.update_register.assert_awaited_with(72, 0x00FF, 46)


@pytest.mark.asyncio
async def test_filter_commands_follow_installed_system(coordinator, entry):
    buttons = entities("button", coordinator, entry)
    await buttons["replace_supply_filter"].async_press()
    coordinator.controller.write_register.assert_awaited_with(8191, 17)
    entry.options["filter_control"] = "afc_both"
    buttons = entities("button", coordinator, entry)
    assert not buttons["replace_supply_filter"].available
    with pytest.raises(HomeAssistantError):
        await buttons["replace_supply_filter"].async_press()


def test_existing_entry_can_select_model():
    assert is_airpack4(SimpleNamespace(data={}, options={"recuperator_model": DEVICE_AIRPACK4}))


@pytest.mark.parametrize("raw", [0xA200, 0x2400, 0xFFFF, 0x1260, 0x1A30])
def test_invalid_and_disabled_clocks(raw):
    assert decode_clock(raw) is None


@pytest.mark.asyncio
async def test_follow_mode_sentinels_and_limits(coordinator, entry):
    switches = entities("switch", coordinator, entry)
    await switches["window_follow_mode"].async_turn_on()
    coordinator.controller.write_register.assert_awaited_with(4239, 101)
    await switches["bypass_follow_mode"].async_turn_on()
    coordinator.controller.write_register.assert_awaited_with(4333, 151)
    coordinator.safe_data.input.update({276: 20, 277: 110})
    numbers = entities("number", coordinator, entry)
    assert numbers["bypass_intensity"].native_min_value == 20
    assert numbers["bypass_intensity"].native_max_value == 110
    with pytest.raises(HomeAssistantError):
        await numbers["bypass_intensity"].async_set_native_value(120)
    with pytest.raises(HomeAssistantError):
        await numbers["empty_house_intensity"].async_set_native_value(10)


@pytest.mark.asyncio
async def test_schedule_enable_disable(coordinator, entry):
    switches = entities("switch", coordinator, entry)
    schedule = switches["summer_0_0_enabled"]
    assert schedule.is_on
    await schedule.async_turn_off()
    coordinator.controller.write_register.assert_awaited_with(16, 0xA200)
    coordinator.safe_data.holding[16] = 0xA200
    assert not schedule.is_on
    await schedule.async_turn_on()
    coordinator.controller.write_register.assert_awaited_with(16, 0x0630)
    await switches["summer_0_airing_enabled"].async_turn_off()
    coordinator.controller.write_register.assert_awaited_with(128, 0x2400)


def test_factory_has_unique_identities_and_actual_modes(coordinator, entry):
    for platform in ("sensor", "binary_sensor", "switch", "select", "number", "time", "button"):
        items = airpack4_entities(platform, coordinator, entry)
        assert len({item.unique_id for item in items}) == len(items)
        assert all(not item.should_poll for item in items)
    selectors = entities("select", coordinator, entry)
    assert selectors["mode"].options == ["Automatyczny", "Manualny", "Chwilowy"]
    sensors = entities("sensor", coordinator, entry)
    assert sensors["work_mode_code"].unique_id == "thessla_sensor_10_4208"
    assert sensors["work_mode_code"].native_value == 1
    assert sensors["active_alarms"].native_value == "F146"


@pytest.mark.asyncio
async def test_controller_name_uses_one_ascii_block(coordinator, entry):
    from custom_components.thessla_green.text import AirpackNameText
    text = AirpackNameText(coordinator, entry)
    await text.async_set_value("AirPack 300h")
    call = coordinator.controller.write_registers.await_args
    assert call.args[0] == 8144 and len(call.args[1]) == 8
    encoded = b"".join(value.to_bytes(2, "big") for value in call.args[1])
    assert encoded.rstrip(b"\0") == b"AirPack 300h"
    with pytest.raises(HomeAssistantError):
        await text.async_set_value("Rekuperator Łódź")
    with pytest.raises(HomeAssistantError):
        await text.async_set_value("This name is too long")
