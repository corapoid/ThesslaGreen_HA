"""Verify device information is accepted by the real Home Assistant registry."""

from inspect import signature
from types import MappingProxyType, SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from custom_components.thessla_green.airpack4 import airpack4_entities
from custom_components.thessla_green.const import DEVICE_AIRPACK4, DOMAIN
from custom_components.thessla_green.coordinator import ThesslaGreenCoordinator
from custom_components.thessla_green.modbus_controller import ControllerData


@pytest.mark.asyncio
async def test_real_ha_device_registry_shows_model_and_measured_versions(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    values = dict(
        domain=DOMAIN, title="AirPack4 300h", version=1, minor_version=1, source="user",
        data={"device_type": DEVICE_AIRPACK4, "host": "gateway", "port": 502, "slave": 10},
        options={}, unique_id=None, discovery_keys=MappingProxyType({}), subentries_data=[],
        state=ConfigEntryState.SETUP_IN_PROGRESS,
    )
    entry = ConfigEntry(**{key: value for key, value in values.items() if key in signature(ConfigEntry).parameters})
    hass.config_entries = SimpleNamespace(async_get_entry=lambda _: entry)
    data = ControllerData(input={0: 4, 1: 89, 4: 0, 24: 0x1A, 25: 0x2B, 26: 0x3C, 27: 0x4D, 28: 0x5E, 29: 0x6F},
                          holding={240: 30})
    controller = SimpleNamespace(fetch_data=AsyncMock(return_value=data))
    coordinator = ThesslaGreenCoordinator(hass, controller, 30, config_entry=entry)
    try:
        await coordinator.async_config_entry_first_refresh()
        sensors = airpack4_entities("sensor", coordinator, entry)
        model = next(sensor for sensor in sensors if getattr(sensor, "_key", None) == "model")
        if hasattr(device_registry, "async_setup"):
            device_registry.async_setup(hass)
        await device_registry.async_load(hass)
        registry = device_registry.async_get(hass)
        device = registry.async_get_or_create(config_entry_id=entry.entry_id, **model.device_info)
        assert device.model == "AirPack4 300h"
        assert device.manufacturer == "Thessla Green"
        assert device.sw_version == "4.89"
        assert device.hw_version == "TG-02 0.30"
        assert device.serial_number == "1a2b3c4d5e6f"
        assert device.identifiers == {(DOMAIN, "10")}
    finally:
        await entry._async_process_on_unload(hass)
        await hass.async_stop()
