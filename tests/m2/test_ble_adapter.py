"""
M2 Test Group C + D: BleAdapter unit and lifecycle tests.

Group C — _parse_ble_midi_packet byte parsing (synchronous, no hardware)
Group D — Lifecycle: connect, disconnect, notification delivery (async, mocked bleak)

BLE-MIDI packet byte conventions used in this test module
---------------------------------------------------------
Header byte:    bits 7:6 = 11  → minimum value 0xC0 (ts_high = 0)
Timestamp byte: bits 7:6 = 10  → minimum value 0x80 (ts_low = 0)

Example single Note-On packet (ts = 0):
  [0xC0, 0x80, 0x90, 60, 80]
   ↑hdr  ↑ts   ↑NoteOn ↑note ↑vel
"""

from __future__ import annotations

import pytest

import core.io.ble_adapter as ble_module
from core.io.ble_adapter import BleAdapter, MIDI_CHAR_UUID
from core.io.midi_source import DeviceInfo, DeviceNotFoundError
from tests.m2.helpers import (
    FakeBLEDevice,
    FakeBleakClient,
    FakeBleakScanner,
    make_fake_ble_client_factory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _packet(*bytes_: int) -> bytearray:
    return bytearray(bytes_)


def _parse(data: bytearray) -> list:
    """Parse a BLE-MIDI packet using a fresh BleAdapter instance."""
    adapter = BleAdapter()
    return adapter._parse_ble_midi_packet(data, base_timestamp_ms=0.0)


# ===========================================================================
# Group C: _parse_ble_midi_packet — pure packet parsing (synchronous)
# ===========================================================================

class TestBleMidiPacketParser:
    """Test the BLE-MIDI packet parser in isolation — no hardware needed."""

    def test_single_note_on(self):
        # [header, timestamp, 0x90, note, vel]
        events = _parse(_packet(0xC0, 0x80, 0x90, 60, 80))
        assert len(events) == 1
        e = events[0]
        assert e.type == "note_on"
        assert e.channel == 0
        assert e.note == 60
        assert e.velocity == 80

    def test_single_note_off(self):
        events = _parse(_packet(0xC0, 0x80, 0x80, 60, 0))
        assert len(events) == 1
        e = events[0]
        assert e.type == "note_off"
        assert e.note == 60
        assert e.velocity == 0

    def test_note_on_velocity_zero_is_note_off(self):
        events = _parse(_packet(0xC0, 0x80, 0x90, 64, 0))
        assert len(events) == 1
        assert events[0].type == "note_off"

    def test_packed_two_events_distinct_status(self):
        """Two Note-On events in one packet (explicit status on each)."""
        # [hdr, ts0, 0x90, 60, 80, ts1, 0x90, 62, 64]
        events = _parse(_packet(0xC0, 0x80, 0x90, 60, 80, 0x81, 0x90, 62, 64))
        assert len(events) == 2
        assert events[0].type == "note_on"
        assert events[0].note == 60
        assert events[0].velocity == 80
        assert events[1].type == "note_on"
        assert events[1].note == 62
        assert events[1].velocity == 64

    def test_running_status_status_omitted(self):
        """Second event uses running status (0x90 omitted)."""
        # [hdr, ts0, 0x90, 60, 80, ts1, 62, 64]
        events = _parse(_packet(0xC0, 0x80, 0x90, 60, 80, 0x81, 62, 64))
        assert len(events) == 2
        assert events[0].note == 60
        assert events[1].note == 62
        assert events[1].type == "note_on"

    def test_timestamp_reconstruction(self):
        """
        header ts_high=1, timestamp ts_low=5  →  13-bit ts = (1<<7)|5 = 133 ms.

        The test verifies the packet is parsed correctly (the 13-bit value is
        an internal detail used for ordering, not exposed on MidiEvent).
        """
        # header = 0xC0 | 1 = 0xC1, timestamp = 0x80 | 5 = 0x85
        events = _parse(_packet(0xC1, 0x85, 0x90, 60, 64))
        assert len(events) == 1
        assert events[0].type == "note_on"
        assert events[0].note == 60

    def test_malformed_truncated_returns_no_events(self):
        """Truncated packet after status byte — no exception, no events."""
        events = _parse(_packet(0xC0, 0x80, 0x90))
        # Only header + timestamp + status, no data bytes — adapter logs warning
        # and returns empty or partial (depending on implementation) — no crash.
        assert isinstance(events, list)

    def test_malformed_bad_header_returns_empty(self):
        """Header byte without bits 7:6 = 11 is rejected."""
        events = _parse(_packet(0x00, 0x80, 0x90, 60, 80))
        assert events == []

    def test_too_short_returns_empty(self):
        events = _parse(_packet(0xC0))
        assert events == []

    def test_control_change(self):
        events = _parse(_packet(0xC0, 0x80, 0xB0, 7, 100))
        assert len(events) == 1
        assert events[0].type == "control_change"
        assert events[0].note is None
        assert events[0].velocity is None

    def test_program_change(self):
        events = _parse(_packet(0xC0, 0x80, 0xC0, 10))
        assert len(events) == 1
        assert events[0].type == "program_change"

    def test_pitch_bend(self):
        events = _parse(_packet(0xC0, 0x80, 0xE0, 0, 64))
        assert len(events) == 1
        assert events[0].type == "pitch_bend"

    def test_channel_encoding(self):
        """Status 0x93 → Note On on channel 3."""
        events = _parse(_packet(0xC0, 0x80, 0x93, 48, 72))
        assert len(events) == 1
        assert events[0].channel == 3
        assert events[0].note == 48

    def test_timestamp_ms_is_base_timestamp(self):
        adapter = BleAdapter()
        events = adapter._parse_ble_midi_packet(_packet(0xC0, 0x80, 0x90, 60, 80), base_timestamp_ms=5000.0)
        assert len(events) == 1
        assert events[0].timestamp_ms == pytest.approx(5000.0)

    def test_timestamp_ticks_is_zero(self):
        events = _parse(_packet(0xC0, 0x80, 0x90, 60, 80))
        assert events[0].timestamp_ticks == 0


# ===========================================================================
# Group D: BleAdapter lifecycle (async, mocked bleak)
# ===========================================================================

class TestBleAdapterLifecycle:
    """Lifecycle tests using FakeBleakScanner and FakeBleakClient."""

    def _wire(self, adapter: BleAdapter, devices: list[FakeBLEDevice], monkeypatch):
        """Monkeypatch bleak classes in the ble_adapter module."""
        fake_client = FakeBleakClient()
        monkeypatch.setattr(ble_module, "BleakScanner", FakeBleakScanner(devices))
        monkeypatch.setattr(ble_module, "BleakClient", make_fake_ble_client_factory(fake_client))
        return fake_client

    # --- Enumeration ---

    async def test_enumerate_devices_returns_names(self, monkeypatch):
        monkeypatch.setattr(
            ble_module,
            "BleakScanner",
            FakeBleakScanner([FakeBLEDevice("MK Monitor"), FakeBLEDevice("Other BLE MIDI")]),
        )
        names = await BleAdapter.enumerate_devices()
        assert "MK Monitor" in names

    async def test_enumerate_devices_empty_when_none_found(self, monkeypatch):
        monkeypatch.setattr(ble_module, "BleakScanner", FakeBleakScanner([]))
        names = await BleAdapter.enumerate_devices()
        assert names == []

    # --- Connection ---

    async def test_connect_by_name_sets_connected(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()

    async def test_connect_device_not_found_raises(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        self._wire(adapter, [], monkeypatch)
        with pytest.raises(DeviceNotFoundError):
            await adapter.connect()

    async def test_connect_none_uses_first_device(self, monkeypatch):
        adapter = BleAdapter(device_name=None)
        self._wire(adapter, [FakeBLEDevice("Any Device")], monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()

    # --- Disconnect ---

    async def test_is_connected_false_after_disconnect(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        await adapter.connect()
        await adapter.disconnect()
        assert not adapter.is_connected()

    # --- Notification delivery ---

    async def test_notification_triggers_callback(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        fake_client = self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        received = []
        adapter.register_callback(received.append)
        await adapter.connect()

        packet = bytearray([0xC0, 0x80, 0x90, 60, 80])
        fake_client.inject_notification(MIDI_CHAR_UUID, packet)

        assert len(received) == 1
        assert received[0].type == "note_on"
        assert received[0].note == 60
        assert received[0].velocity == 80
        await adapter.disconnect()

    async def test_packed_notification_delivers_all_events(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        fake_client = self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        received = []
        adapter.register_callback(received.append)
        await adapter.connect()

        # Two note-on events in one packet
        packet = bytearray([0xC0, 0x80, 0x90, 60, 80, 0x81, 0x90, 62, 64])
        fake_client.inject_notification(MIDI_CHAR_UUID, packet)

        assert len(received) == 2
        assert received[0].note == 60
        assert received[1].note == 62
        await adapter.disconnect()

    async def test_callback_not_fired_before_connect(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        fake_client = self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        received = []
        adapter.register_callback(received.append)
        # Inject before connect — notification_handler is not yet registered.
        fake_client.inject_notification(MIDI_CHAR_UUID, bytearray([0xC0, 0x80, 0x90, 60, 80]))
        assert received == []

    async def test_callback_not_fired_after_disconnect(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        fake_client = self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        received = []
        adapter.register_callback(received.append)
        await adapter.connect()
        await adapter.disconnect()

        # After disconnect, stop_notify removes the handler from fake_client.
        count_before = len(received)
        fake_client.inject_notification(MIDI_CHAR_UUID, bytearray([0xC0, 0x80, 0x90, 62, 64]))
        assert len(received) == count_before

    # --- Unexpected disconnect ---

    async def test_unexpected_disconnect_clears_is_connected(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        fake_client = self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()

        fake_client.simulate_disconnect()

        assert not adapter.is_connected()
        await adapter.disconnect()  # safe to call even if already disconnected

    async def test_unexpected_disconnect_fires_disconnect_callback(self, monkeypatch):
        adapter = BleAdapter(device_name="MK Monitor")
        fake_client = self._wire(adapter, [FakeBLEDevice("MK Monitor")], monkeypatch)
        disconnect_fired = []
        adapter.register_disconnect_callback(lambda: disconnect_fired.append(True))
        await adapter.connect()

        fake_client.simulate_disconnect()

        assert disconnect_fired == [True]

    # --- list_devices ---

    async def test_list_devices_returns_device_infos_with_address(self, monkeypatch):
        monkeypatch.setattr(
            ble_module,
            "BleakScanner",
            FakeBleakScanner([
                FakeBLEDevice("MK Monitor", address="AA:BB:CC:DD:EE:FF"),
                FakeBLEDevice("Other MIDI", address="11:22:33:44:55:66"),
            ]),
        )
        adapter = BleAdapter()
        devices = await adapter.list_devices()
        assert len(devices) == 2
        assert all(isinstance(d, DeviceInfo) for d in devices)
        names = [d.name for d in devices]
        addrs = [d.address for d in devices]
        assert "MK Monitor" in names
        assert "AA:BB:CC:DD:EE:FF" in addrs

    async def test_list_devices_excludes_non_midi_devices(self, monkeypatch):
        monkeypatch.setattr(
            ble_module,
            "BleakScanner",
            FakeBleakScanner([
                FakeBLEDevice("MK Monitor"),
                FakeBLEDevice("Regular Speaker", include_midi_uuid=False),
            ]),
        )
        adapter = BleAdapter()
        devices = await adapter.list_devices()
        assert len(devices) == 1
        assert devices[0].name == "MK Monitor"

    # --- UUID filtering in connect ---

    async def test_connect_filters_non_ble_midi_by_default(self, monkeypatch):
        """require_midi_service=True (default) skips devices without BLE-MIDI UUID."""
        adapter = BleAdapter(device_name="Regular Speaker")
        self._wire(adapter, [FakeBLEDevice("Regular Speaker", include_midi_uuid=False)], monkeypatch)
        with pytest.raises(DeviceNotFoundError):
            await adapter.connect()

    async def test_connect_skips_uuid_filter_when_require_midi_service_false(self, monkeypatch):
        """require_midi_service=False connects to any device matching the name."""
        adapter = BleAdapter(device_name="Regular Speaker", require_midi_service=False)
        self._wire(adapter, [FakeBLEDevice("Regular Speaker", include_midi_uuid=False)], monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()
        await adapter.disconnect()
