"""Run the real pymodbus client against a local Modbus TCP gateway."""

import asyncio
import struct

import pytest

from custom_components.thessla_green.modbus_controller import ThesslaGreenModbusController


@pytest.mark.asyncio
async def test_read_write_over_tcp():
    registers = {16: 0, 17: 1, 33: 65526, 48: 1, 50: 123, 51: 4, 65: 30, 96: 0x20}
    requests = []
    handlers = set()

    async def gateway(reader, writer):
        task = asyncio.current_task()
        handlers.add(task)
        try:
            while True:
                header = await reader.readexactly(7)
                transaction, protocol, length, slave = struct.unpack(">HHHB", header)
                function, address, value = struct.unpack(">BHH", await reader.readexactly(length - 1))
                requests.append((slave, function, address, value))
                if function == 3:
                    payload = struct.pack(">BB", 3, value * 2) + b"".join(
                        struct.pack(">H", registers.get(index, 0))
                        for index in range(address, address + value)
                    )
                elif function == 6:
                    registers[address] = value
                    payload = struct.pack(">BHH", 6, address, value)
                else:
                    payload = bytes([function | 0x80, 1])
                writer.write(struct.pack(">HHHB", transaction, protocol, len(payload) + 1, slave) + payload)
                await writer.drain()
        except asyncio.IncompleteReadError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()
            handlers.discard(task)

    server = await asyncio.start_server(gateway, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    controller = ThesslaGreenModbusController("127.0.0.1", port, 30, device_type="particle")
    try:
        data = await controller.fetch_data()
        assert data.holding[33] == 65526
        assert data.holding[50] == 123
        assert data.holding[96] == 0x20
        assert await controller.write_register(65, 80)
        assert (await controller.fetch_data()).holding[65] == 80
        assert all(slave == 30 and function in (3, 6) for slave, function, _, _ in requests)
        assert all(count <= 16 for _, function, _, count in requests if function == 3)
    finally:
        await controller.stop()
        server.close()
        await server.wait_closed()
        if handlers:
            await asyncio.gather(*handlers)
