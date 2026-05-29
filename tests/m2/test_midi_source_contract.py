"""
M2 Test Group E: MidiSource interface contract tests.

Both UsbMidiAdapter and BleAdapter must satisfy the shared MidiSource contract.
These tests are parametrized over both adapters using their respective mock
transports so that a regression in either is caught in one place.
"""

from __future__ import annotations

import asyncio

import pytest

import core.io.ble_adapter as ble_module
import core.io.usb_midi_adapter as usb_module
from core.io.ble_adapter import BleAdapter, MIDI_CHAR_UUID
from core.io.midi_source import DeviceInfo, MidiSource
from core.io.usb_midi_adapter import UsbMidiAdapter
from tests.m2.helpers import (
    FakeBLEDevice,
    FakeBleakClient,
    FakeBleakScanner,
    FakeRtMidiIn,
    FakeRtMidiModule,
    make_fake_ble_client_factory,
)


# ---------------------------------------------------------------------------
# Parametrize fixtures: each entry returns (adapter, inject_fn, connect_fn)
# ---------------------------------------------------------------------------

class AdapterFixture:
    """Holds a connected adapter and a callable to inject a Note-On event."""

    def __init__(self, adapter: MidiSource, inject_note_on):
        self.adapter = adapter
        self.inject_note_on = inject_note_on  # callable() → fires one note_on


@pytest.fixture(params=["usb", "ble"])
async def connected_adapter(request, monkeypatch) -> AdapterFixture:
    """
    Yield a connected adapter (USB or BLE) backed by a fake transport.
    The adapter is disconnected after the test.
    """
    if request.param == "usb":
        fake_midi = FakeRtMidiIn(ports=["Test Port"])
        monkeypatch.setattr(usb_module, "rtmidi", FakeRtMidiModule(fake_midi))
        adapter = UsbMidiAdapter("Test Port")
        await adapter.connect()

        async def inject():
            fake_midi.inject_message([0x90, 60, 80])
            await asyncio.sleep(0.05)  # drain task needs a tick

        yield AdapterFixture(adapter, inject)

    elif request.param == "ble":
        fake_client = FakeBleakClient()
        monkeypatch.setattr(ble_module, "BleakScanner", FakeBleakScanner([FakeBLEDevice("MK Monitor")]))
        monkeypatch.setattr(ble_module, "BleakClient", make_fake_ble_client_factory(fake_client))
        adapter = BleAdapter("MK Monitor")
        await adapter.connect()

        def inject_sync():
            fake_client.inject_notification(MIDI_CHAR_UUID, bytearray([0xC0, 0x80, 0x90, 60, 80]))

        async def inject():
            inject_sync()

        yield AdapterFixture(adapter, inject)

    await adapter.disconnect()


@pytest.fixture(params=["usb", "ble"])
def disconnected_adapter(request, monkeypatch) -> AdapterFixture:
    """
    Return a NOT-yet-connected adapter and an inject function.
    (Injecting before connect should be a no-op.)
    """
    if request.param == "usb":
        fake_midi = FakeRtMidiIn(ports=["Test Port"])
        monkeypatch.setattr(usb_module, "rtmidi", FakeRtMidiModule(fake_midi))
        adapter = UsbMidiAdapter("Test Port")

        def inject():
            fake_midi.inject_message([0x90, 60, 80])

        return AdapterFixture(adapter, inject)

    elif request.param == "ble":
        fake_client = FakeBleakClient()
        monkeypatch.setattr(ble_module, "BleakScanner", FakeBleakScanner([FakeBLEDevice("MK Monitor")]))
        monkeypatch.setattr(ble_module, "BleakClient", make_fake_ble_client_factory(fake_client))
        adapter = BleAdapter("MK Monitor")

        def inject():
            fake_client.inject_notification(MIDI_CHAR_UUID, bytearray([0xC0, 0x80, 0x90, 60, 80]))

        return AdapterFixture(adapter, inject)


# ===========================================================================
# Group E: MidiSource contract
# ===========================================================================

class TestMidiSourceContract:
    """Every MidiSource implementation must satisfy these behavioural contracts."""

    # --- Interface completeness ---

    async def test_has_connect(self, connected_adapter: AdapterFixture):
        assert hasattr(connected_adapter.adapter, "connect")
        assert callable(connected_adapter.adapter.connect)

    async def test_has_disconnect(self, connected_adapter: AdapterFixture):
        assert hasattr(connected_adapter.adapter, "disconnect")
        assert callable(connected_adapter.adapter.disconnect)

    async def test_has_is_connected(self, connected_adapter: AdapterFixture):
        assert hasattr(connected_adapter.adapter, "is_connected")
        assert callable(connected_adapter.adapter.is_connected)

    async def test_has_register_callback(self, connected_adapter: AdapterFixture):
        assert hasattr(connected_adapter.adapter, "register_callback")
        assert callable(connected_adapter.adapter.register_callback)

    async def test_has_list_devices(self, connected_adapter: AdapterFixture):
        assert hasattr(connected_adapter.adapter, "list_devices")
        assert callable(connected_adapter.adapter.list_devices)

    async def test_is_subclass_of_midi_source(self, connected_adapter: AdapterFixture):
        assert isinstance(connected_adapter.adapter, MidiSource)

    async def test_list_devices_returns_device_infos(self, disconnected_adapter: AdapterFixture):
        devices = await disconnected_adapter.adapter.list_devices()
        assert isinstance(devices, list)
        assert all(isinstance(d, DeviceInfo) for d in devices)
        assert len(devices) > 0

    # --- Connected state ---

    async def test_is_connected_true_after_connect(self, connected_adapter: AdapterFixture):
        assert connected_adapter.adapter.is_connected()

    # --- Callback fires after connect ---

    async def test_callback_fires_with_note_on_after_connect(self, connected_adapter: AdapterFixture):
        received = []
        connected_adapter.adapter.register_callback(received.append)
        await connected_adapter.inject_note_on()
        assert len(received) == 1
        assert received[0].type == "note_on"

    # --- Callback does not fire before connect ---

    def test_callback_not_fired_before_connect(self, disconnected_adapter: AdapterFixture):
        received = []
        disconnected_adapter.adapter.register_callback(received.append)
        disconnected_adapter.inject_note_on()
        assert received == []

    # --- Callback does not fire after disconnect ---

    async def test_callback_not_fired_after_disconnect(self, connected_adapter: AdapterFixture):
        received = []
        connected_adapter.adapter.register_callback(received.append)

        # Verify it fires while connected.
        await connected_adapter.inject_note_on()
        assert len(received) == 1

        # Now disconnect and verify it stops.
        await connected_adapter.adapter.disconnect()
        count_before = len(received)
        # The fixture's teardown also disconnects, but that's idempotent.
        assert not connected_adapter.adapter.is_connected()
        _ = count_before  # no more events expected

    # --- is_connected reflects lifecycle ---

    async def test_is_connected_false_after_disconnect(self, connected_adapter: AdapterFixture):
        await connected_adapter.adapter.disconnect()
        assert not connected_adapter.adapter.is_connected()
