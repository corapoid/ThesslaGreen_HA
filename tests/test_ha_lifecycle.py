"""Exercise real Home Assistant entries, coordinators and state-change events."""

from inspect import signature
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

import custom_components.thessla_green as integration
from custom_components.thessla_green.const import DOMAIN
from custom_components.thessla_green.coordinator import ThesslaGreenCoordinator
from custom_components.thessla_green.modbus_controller import ControllerData, ControllerException
from custom_components.thessla_green.sensor import ModbusGenericSensor, RekuCOPSensor


def make_entry():
    values = dict(
        domain=DOMAIN, title="Recuperator", version=1, minor_version=1, source="user",
        data={"host": "gateway", "port": 502, "slave": 10}, options={"sensor_power": "sensor.power"},
        unique_id=None, discovery_keys=MappingProxyType({}), subentries_data=[],
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    # Constructor fields differ between the minimum and current HA releases.
    return ConfigEntry(**{key: value for key, value in values.items() if key in signature(ConfigEntry).parameters})


@pytest.mark.asyncio
async def test_real_coordinator_not_ready_then_recovers(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    entry = make_entry()
    controller = SimpleNamespace(fetch_data=AsyncMock(side_effect=ControllerException("offline")))
    coordinator = ThesslaGreenCoordinator(hass, controller, 30, config_entry=entry)
    try:
        with pytest.raises(ConfigEntryNotReady):
            await coordinator.async_config_entry_first_refresh()
        assert not coordinator.last_update_success
        controller.fetch_data.side_effect = None
        controller.fetch_data.return_value = ControllerData(input={16: 123})
        await coordinator.async_config_entry_first_refresh()
        assert coordinator.last_update_success
        assert coordinator.safe_data.input[16] == 123
    finally:
        await entry._async_process_on_unload(hass)
        await hass.async_stop()


@pytest.mark.asyncio
async def test_real_setup_unload_and_options_listener(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    entry = make_entry()
    controller = SimpleNamespace(fetch_data=AsyncMock(return_value=ControllerData()), stop=AsyncMock())
    hass.config_entries = SimpleNamespace(
        async_forward_entry_setups=AsyncMock(), async_unload_platforms=AsyncMock(return_value=True),
        async_reload=AsyncMock(),
    )
    try:
        with patch.object(integration, "ThesslaGreenModbusController", return_value=controller):
            assert await integration.async_setup_entry(hass, entry)
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert isinstance(coordinator, ThesslaGreenCoordinator)
        assert coordinator.config_entry is entry
        assert len(entry.update_listeners) == 1
        await entry.update_listeners[0](hass, entry)
        hass.config_entries.async_reload.assert_awaited_once_with(entry.entry_id)
        assert await integration.async_unload_entry(hass, entry)
        await entry._async_process_on_unload(hass)
        assert not entry.update_listeners
        controller.stop.assert_awaited_once()
    finally:
        await entry._async_process_on_unload(hass)
        await hass.async_stop()


@pytest.mark.asyncio
async def test_entity_notifications_and_cop_power_events(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    entry = make_entry()
    controller = SimpleNamespace(fetch_data=AsyncMock(return_value=ControllerData(
        input={16: 0, 17: 180, 18: 220}, holding={256: 300},
    )))
    coordinator = ThesslaGreenCoordinator(hass, controller, 30, config_entry=entry)
    await coordinator.async_config_entry_first_refresh()
    hass.states.async_set("sensor.power", "100", {"unit_of_measurement": "W"})
    cop = RekuCOPSensor(coordinator, 10, "sensor.power")
    temperature = ModbusGenericSensor(coordinator, "Temperature", 17, input_type="input", scale=0.1, slave=10)
    entities = (cop, temperature)
    try:
        for entity in entities:
            entity.hass = hass
            entity.async_write_ha_state = MagicMock()
            await entity.async_added_to_hass()
        assert cop.native_value == 18.09
        assert not temperature.should_poll
        hass.states.async_set("sensor.power", "200", {"unit_of_measurement": "W"})
        await hass.async_block_till_done()
        assert cop.native_value == 9.04
        coordinator.async_set_updated_data(ControllerData(input={16: 0, 17: 200, 18: 220}, holding={256: 300}))
        assert temperature.native_value == 20
        assert cop.native_value == 10.05
        temperature.async_write_ha_state.assert_called()
        controller.fetch_data.side_effect = ControllerException("offline")
        await coordinator.async_refresh()
        assert not temperature.available
        assert not cop.available
        controller.fetch_data.side_effect = None
        await coordinator.async_refresh()
        assert temperature.available
        assert cop.available
    finally:
        for entity in entities:
            await entity.async_internal_will_remove_from_hass()
        await entry._async_process_on_unload(hass)
        await hass.async_stop()
