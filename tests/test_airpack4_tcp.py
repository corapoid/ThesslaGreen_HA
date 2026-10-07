"""Run the AirPack4 profile against a strict, stateful local Modbus TCP server."""

import asyncio
import struct

import pytest

from custom_components.thessla_green.const import DEVICE_AIRPACK4
from custom_components.thessla_green.modbus_controller import ControllerException, ThesslaGreenModbusController


@pytest.mark.asyncio
async def test_strict_profile_atomic_writes_cache_and_optional_registers():
    # Independently enumerate the protocol addresses accepted by this controller.
    holding_addresses = {
        13, 240, 241, 256, 257, 4192, 4198, 4208, 4209, 4210, 4211, 4212, 4213,
        4224, 4304, 4305, 4320, 4330, 4331, 4354, 4355, 4384, 4387, 4432, 4433,
        4482, 4483, 4660, 4662, 4704, 4711, 8190, 8191, 8192, 8193,
    } | set(range(16, 128)) | {128 + day * 4 for day in range(14)} | set(range(4400, 4406)) | set(range(8144, 8152))
    holding = {address: 0 for address in holding_addresses}
    holding.update({240: 30, 256: 210, 257: 210, 4210: 30, 4211: 40, 4212: 40, 4213: 44,
                    16: 0x0630, 72: 0x1E2C, 4387: 1, 8191: 4})
    inputs = {address: 0 for address in set(range(5)) | set(range(14, 23)) | set(range(24, 30)) | set(range(271, 278))}
    inputs.update({0: 4, 1: 89, 16: 100, 17: 180, 18: 220, 19: 0x8000, 276: 10, 277: 120})
    coils = {address: False for address in (5, 9, 10, 11, 12, 13, 14, 15)}
    discrete = {address: False for address in (0, 1, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 18, 19, 21)}
    requests = []
    handlers = set()
    fail_optional = False

    async def gateway(reader, writer):
        task = asyncio.current_task()
        handlers.add(task)
        try:
            while True:
                transaction, protocol, length, slave = struct.unpack(">HHHB", await reader.readexactly(7))
                pdu = await reader.readexactly(length - 1)
                function = pdu[0]
                address, count_or_value = struct.unpack(">HH", pdu[1:5])
                requests.append((function, address, count_or_value, slave))
                error = 0
                if function in (1, 2, 3, 4):
                    count = count_or_value
                    assert 1 <= count <= 16
                    source = {1: coils, 2: discrete, 3: holding, 4: inputs}[function]
                    if fail_optional and function == 3 and address == 240:
                        error = 4
                    elif any(index not in source for index in range(address, address + count)):
                        error = 2
                    elif function in (1, 2):
                        values = bytearray((count + 7) // 8)
                        for index in range(count):
                            if source[address + index]:
                                values[index // 8] |= 1 << (index % 8)
                        payload = bytes([function, len(values)]) + values
                    else:
                        payload = bytes([function, count * 2]) + b"".join(
                            struct.pack(">H", source[index]) for index in range(address, address + count)
                        )
                elif function == 6:
                    if address not in holding:
                        error = 2
                    else:
                        holding[address] = count_or_value
                        payload = pdu
                elif function == 16:
                    values = list(struct.unpack(f">{count_or_value}H", pdu[6:]))
                    if any(index not in holding for index in range(address, address + len(values))):
                        error = 2
                    else:
                        holding.update({address + index: value for index, value in enumerate(values)})
                        if address == 4400 and values[2] == 1:
                            holding[4208], holding[4211] = values[:2]
                        if address == 4403 and values[2] == 1:
                            holding[4208], holding[4213] = values[:2]
                        payload = struct.pack(">BHH", function, address, count_or_value)
                else:
                    error = 1
                if error:
                    payload = bytes([function | 0x80, error])
                writer.write(struct.pack(">HHHB", transaction, protocol, len(payload) + 1, slave) + payload)
                await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            handlers.discard(task)

    server = await asyncio.start_server(gateway, "127.0.0.1", 0)
    controller = ThesslaGreenModbusController("127.0.0.1", server.sockets[0].getsockname()[1], 10,
                                            device_type=DEVICE_AIRPACK4)
    try:
        data = await controller.fetch_data()
        assert data.input[1] == 89
        assert data.holding[240] == 30
        assert 4193 not in data.holding and 8444 not in data.holding
        assert 4322 not in data.holding  # Optional, explicitly rejected by the device.
        assert data.holding[4331] == 0  # Neighbouring supported register still read.
        assert data.coil.keys() == coils.keys()
        assert data.discrete.keys() == discrete.keys()
        requests.clear()
        await controller.fetch_data()
        assert not any(function == 3 and 16 <= address <= 180 for function, address, count, slave in requests)
        assert not any(function == 3 and address == 4322 for function, address, count, slave in requests)
        await controller.write_register(16, 0x0745)
        assert (await controller.fetch_data()).holding[16] == 0x0745
        await asyncio.gather(controller.update_register(72, 0xFF00, 40 << 8),
                             controller.update_register(72, 0x00FF, 46))
        assert holding[72] == 0x282E
        await controller.write_registers(4400, [2, 55, 1])
        data = await controller.fetch_data()
        assert data.holding[4208] == 2 and data.holding[4211] == 55
        await controller.write_registers(4403, [2, 43, 1])
        assert holding[4213] == 43
        assert all(slave == 10 for function, address, count, slave in requests)
        fail_optional = True
        with pytest.raises(ControllerException):
            await controller.fetch_data()  # Device failures must not be treated as missing features.
    finally:
        await controller.stop()
        server.close()
        await server.wait_closed()
        if handlers:
            await asyncio.gather(*handlers)
