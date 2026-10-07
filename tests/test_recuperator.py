"""Regression tests for recuperator commands, coordinator updates and COP."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.thessla_green.binary_sensor import ModbusBinarySensor
from custom_components.thessla_green.modbus_controller import ControllerData, ControllerException
from custom_components.thessla_green.number import RekuperatorPredkoscNumber
from custom_components.thessla_green.select import (
    RekuperatorTrybSelect, RekuperatorSezonSelect, RekuperatorErvTrybSelect, RekuperatorKomfortSelect,
)
from custom_components.thessla_green.sensor import ModbusGenericSensor, ModbusUpdateIntervalSensor, RekuCOPSensor
from custom_components.thessla_green.switch import ModbusSwitch


@pytest.fixture
def coordinator():
    return SimpleNamespace(
        last_update_success=True,
        safe_data=ControllerData(input={16: 0, 17: 180, 18: 220}, holding={256: 300}),
        controller=SimpleNamespace(write_register=AsyncMock(return_value=True)),
        async_request_refresh=AsyncMock(),
    )


def test_entities_are_not_polled_and_keep_ids(coordinator):
    entities = [
        ModbusGenericSensor(coordinator, "Temperature", 16, input_type="input", slave=10),
        ModbusUpdateIntervalSensor(coordinator, 10),
        ModbusBinarySensor(coordinator, "Alarm", 8192, slave=10),
        ModbusSwitch(coordinator, "Power", 4387, 1, 0, slave=10),
        RekuperatorPredkoscNumber(coordinator, 10),
        RekuperatorTrybSelect(coordinator, 10),
        RekuperatorSezonSelect(coordinator, 10),
        RekuperatorErvTrybSelect(coordinator, 10),
        RekuperatorKomfortSelect(coordinator, 10),
    ]
    assert [e.unique_id for e in entities] == [
        "thessla_sensor_10_16", "thessla_update_interval_10", "thessla_binary_sensor_10_8192",
        "thessla_switch_10_4387", "thessla_number_10_4210", "thessla_select_10_4224",
        "thessla_sezon_select_10_4209", "thessla_erv_select_10_4711", "thessla_komfort_select_10_4304",
    ]
    assert all(not e.should_poll for e in entities)


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_class,option,address,value", [
    (RekuperatorTrybSelect, "Kominek", 4224, 2),
    (RekuperatorSezonSelect, "Zima", 4209, 1),
    (RekuperatorErvTrybSelect, "ERV tryb 2", 4711, 2),
    (RekuperatorKomfortSelect, "KOMFORT", 4304, 1),
])
async def test_select_commands_and_errors(coordinator, entity_class, option, address, value):
    entity = entity_class(coordinator, 10)
    await entity.async_select_option(option)
    coordinator.controller.write_register.assert_awaited_with(address, value)
    with pytest.raises(HomeAssistantError):
        await entity.async_select_option("invalid")
    coordinator.controller.write_register.side_effect = ControllerException("offline")
    with pytest.raises(HomeAssistantError, match="offline"):
        await entity.async_select_option(option)


@pytest.mark.asyncio
async def test_switch_write_failure_is_reported(coordinator):
    entity = ModbusSwitch(coordinator, "Power", 4387, 1, 0, verify=True, slave=10)
    coordinator.controller.write_register.side_effect = ControllerException("offline")
    with pytest.raises(HomeAssistantError, match="offline"):
        await entity.async_turn_on()
    coordinator.async_request_refresh.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [-1, 0, 9, 101, 40.5, float("nan"), float("inf")])
async def test_invalid_speed_never_written(coordinator, value):
    with pytest.raises(HomeAssistantError):
        await RekuperatorPredkoscNumber(coordinator, 10).async_set_native_value(value)
    coordinator.controller.write_register.assert_not_awaited()


@pytest.mark.parametrize("state,unit,expected", [
    ("100", "W", 18.09), ("0.1", "kW", 18.09),
    ("nan", "W", None), ("inf", "W", None), ("0", "W", None),
    ("-100", "W", None), ("unavailable", "W", None),
    ("100", "MW", None), ("100", "", None), ("100", "Wh", None),
])
def test_cop_requires_finite_power_and_known_unit(coordinator, state, unit, expected):
    sensor = RekuCOPSensor(coordinator, 10, "sensor.power")
    sensor.hass = SimpleNamespace(states=SimpleNamespace(get=lambda _: SimpleNamespace(
        state=state, attributes={"unit_of_measurement": unit},
    )))
    sensor._recalc()
    assert sensor.native_value == expected
    assert sensor.available == (expected is not None)


def test_missing_temperature_and_cf_sentinels(coordinator):
    from custom_components.thessla_green.sensor import RekuEfficiencySensor
    coordinator.safe_data.input[16] = 0x8000
    coordinator.safe_data.holding[256] = 0xFFFF
    assert ModbusGenericSensor(coordinator, "Temperature", 16, "input", 0.1).native_value is None
    assert ModbusGenericSensor(coordinator, "Flow", 256).native_value is None
    efficiency = RekuEfficiencySensor(coordinator, 10)
    efficiency._recalc()
    assert efficiency.native_value is None
