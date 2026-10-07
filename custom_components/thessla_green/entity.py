"""Coordinator-backed entities and shared command validation."""

from math import isfinite

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .modbus_controller import ControllerException


def integer_setting(value, minimum, maximum):
    """Reject invalid commands rather than truncating or clamping them."""
    try:
        valid = isfinite(value) and minimum <= value <= maximum and value == int(value)
    except (TypeError, ValueError, OverflowError):
        valid = False
    if not valid:
        raise HomeAssistantError(f"Invalid setting: {value}; expected an integer from {minimum} to {maximum}")
    return int(value)


class ModbusEntity(CoordinatorEntity):
    """Use coordinator notifications and propagate device command failures."""

    async def _async_write_register(self, address, value):
        try:
            success = await self.coordinator.controller.write_register(address, value)
        except ControllerException as error:
            raise HomeAssistantError(f"Unable to write register {address}: {error}") from error
        if not success:
            raise HomeAssistantError(f"Device rejected the command for register {address}")
        await self.coordinator.async_request_refresh()

    async def _async_write_registers(self, address, values):
        try:
            success = await self.coordinator.controller.write_registers(address, values)
        except ControllerException as error:
            raise HomeAssistantError(f"Unable to write registers at {address}: {error}") from error
        if not success:
            raise HomeAssistantError(f"Device rejected the register block at {address}")
        await self.coordinator.async_request_refresh()
