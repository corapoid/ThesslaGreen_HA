from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, CONF_HOST, CONF_PORT, CONF_SLAVE, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .modbus_controller import ThesslaGreenModbusController
from .coordinator import ThesslaGreenCoordinator
from .const import device_type

import logging

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch", "binary_sensor", "select", "number", "time", "button", "text"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up from YAML (not used)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thessla Green integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    slave = entry.data[CONF_SLAVE]
    update_interval = entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

    # Tworzenie kontrolera Modbus
    controller = ThesslaGreenModbusController(
        host=host,
        port=port,
        slave_id=slave,
        update_interval=update_interval,
        device_type=device_type(entry),
    )

    # Tworzenie koordynatora danych
    coordinator = ThesslaGreenCoordinator(
        hass=hass,
        controller=controller,
        scan_interval=update_interval,
        config_entry=entry,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except BaseException:
        await controller.stop()
        raise

    # Zapisywanie instancji w hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "controller": controller,
        "coordinator": coordinator,
        "slave": slave,
        "scan_interval": update_interval,
    }

    # Forward setup dla każdej platformy
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await controller.stop()
        raise

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recreate entities when the configured power sensor changes."""
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Thessla Green integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data:
        controller: ThesslaGreenModbusController = data["controller"]
        await controller.stop()

    return unload_ok
