"""
M2 Test Group A + B: UsbMidiAdapter unit and lifecycle tests.

Group A — _parse_message byte parsing (synchronous, no hardware)
Group B — Lifecycle: connect, disconnect, callback gating (async, mocked rtmidi)
"""

from __future__ import annotations

import asyncio

import pytest

import core.io.usb_midi_adapter as usb_module
from core.io.midi_source import DeviceInfo, DeviceNotFoundError
from core.io.usb_midi_adapter import UsbMidiAdapter
from tests.m2.helpers import FakeRtMidiIn, FakeRtMidiModule


# ===========================================================================
# Group A: _parse_message — pure byte-parsing (synchronous)
# ===========================================================================

class TestParseMidiMessage:
    """Test the internal _parse_message helper directly — no hardware needed."""

    def _parse(self, bytes_: list[int], ts: float = 0.0):
        adapter = UsbMidiAdapter()
        return adapter._parse_message(bytes_, ts)

    def test_note_on(self):
        event = self._parse([0x90, 60, 80])
        assert event is not None
        assert event.type == "note_on"
        assert event.channel == 0
        assert event.note == 60
        assert event.velocity == 80

    def test_note_off_explicit(self):
        event = self._parse([0x80, 62, 0])
        assert event is not None
        assert event.type == "note_off"
        assert event.channel == 0
        assert event.note == 62
        assert event.velocity == 0

    def test_note_on_velocity_zero_is_note_off(self):
        event = self._parse([0x90, 64, 0])
        assert event is not None
        assert event.type == "note_off"
        assert event.note == 64
        assert event.velocity == 0

    def test_control_change(self):
        event = self._parse([0xB0, 7, 100])
        assert event is not None
        assert event.type == "control_change"
        assert event.channel == 0
        assert event.note is None
        assert event.velocity is None

    def test_pitch_bend(self):
        event = self._parse([0xE0, 0, 64])
        assert event is not None
        assert event.type == "pitch_bend"
        assert event.note is None
        assert event.velocity is None

    def test_channel_3_note_on(self):
        """Status 0x93 → Note On on channel 3."""
        event = self._parse([0x93, 48, 64])
        assert event is not None
        assert event.type == "note_on"
        assert event.channel == 3
        assert event.note == 48
        assert event.velocity == 64

    def test_program_change(self):
        event = self._parse([0xC0, 42])
        assert event is not None
        assert event.type == "program_change"
        assert event.channel == 0

    def test_unknown_status_falls_through_to_other(self):
        event = self._parse([0xF0, 0x00])
        assert event is not None
        assert event.type == "other"

    def test_empty_message_returns_none(self):
        assert self._parse([]) is None

    def test_timestamp_ms_is_preserved(self):
        event = self._parse([0x90, 60, 80], ts=1234.5)
        assert event is not None
        assert event.timestamp_ms == pytest.approx(1234.5)

    def test_timestamp_ticks_is_zero(self):
        """Real-time events have no tick context."""
        event = self._parse([0x90, 60, 80])
        assert event is not None
        assert event.timestamp_ticks == 0


# ===========================================================================
# Group B: UsbMidiAdapter lifecycle (async, mocked rtmidi)
# ===========================================================================

class TestUsbAdapterLifecycle:
    """Lifecycle tests using FakeRtMidiIn instead of real hardware."""

    def _make_adapter(self, port_name: str | None, fake_midi: FakeRtMidiIn, monkeypatch):
        """Wire up the adapter with a fake rtmidi module."""
        monkeypatch.setattr(usb_module, "rtmidi", FakeRtMidiModule(fake_midi))
        return UsbMidiAdapter(port_name=port_name)

    # --- Enumeration ---

    def test_enumerate_devices_returns_port_names(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["Keyboard A", "Keyboard B"])
        monkeypatch.setattr(usb_module, "rtmidi", FakeRtMidiModule(fake))
        ports = UsbMidiAdapter.enumerate_devices()
        assert ports == ["Keyboard A", "Keyboard B"]

    def test_enumerate_devices_empty(self, monkeypatch):
        fake = FakeRtMidiIn(ports=[])
        monkeypatch.setattr(usb_module, "rtmidi", FakeRtMidiModule(fake))
        assert UsbMidiAdapter.enumerate_devices() == []

    # --- Connection ---

    async def test_connect_named_port_sets_connected(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["My Keyboard"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()

    async def test_connect_missing_port_raises_device_not_found(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["Other Device"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        with pytest.raises(DeviceNotFoundError):
            await adapter.connect()

    async def test_connect_no_ports_raises_device_not_found(self, monkeypatch):
        fake = FakeRtMidiIn(ports=[])
        adapter = self._make_adapter(None, fake, monkeypatch)
        with pytest.raises(DeviceNotFoundError):
            await adapter.connect()

    async def test_connect_none_selects_first_port(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["First", "Second"])
        adapter = self._make_adapter(None, fake, monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()
        assert fake._open_port_idx == 0
        await adapter.disconnect()

    # --- Disconnect ---

    async def test_is_connected_false_after_disconnect(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["My Keyboard"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()
        assert not adapter.is_connected()

    # --- Callback firing ---

    async def test_callback_fires_after_connect(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["My Keyboard"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        received = []
        adapter.register_callback(received.append)
        await adapter.connect()

        fake.inject_message([0x90, 60, 80])
        await asyncio.sleep(0.05)  # let the drain task process the queue

        assert len(received) == 1
        assert received[0].type == "note_on"
        assert received[0].note == 60
        assert received[0].velocity == 80
        await adapter.disconnect()

    async def test_callback_not_fired_before_connect(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["My Keyboard"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        received = []
        adapter.register_callback(received.append)
        # Inject before connect — no queue exists, so nothing should happen.
        fake.inject_message([0x90, 60, 80])
        assert received == []

    async def test_callback_not_fired_after_disconnect(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["My Keyboard"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        received = []
        adapter.register_callback(received.append)
        await adapter.connect()
        await adapter.disconnect()

        # The drain task is cancelled; inject should not deliver.
        # We put directly on the (now-orphaned) queue to simulate a race.
        count_before = len(received)
        fake.inject_message([0x90, 62, 64])
        await asyncio.sleep(0.05)
        assert len(received) == count_before

    async def test_multiple_messages_delivered_in_order(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["My Keyboard"])
        adapter = self._make_adapter("My Keyboard", fake, monkeypatch)
        received = []
        adapter.register_callback(received.append)
        await adapter.connect()

        notes = [60, 62, 64, 65, 67]
        for n in notes:
            fake.inject_message([0x90, n, 80])
        await asyncio.sleep(0.05)

        received_notes = [e.note for e in received if e.type == "note_on"]
        assert received_notes == notes
        await adapter.disconnect()

    # --- list_devices ---

    async def test_list_devices_returns_device_infos(self, monkeypatch):
        fake = FakeRtMidiIn(ports=["Keyboard A", "Keyboard B"])
        monkeypatch.setattr(usb_module, "rtmidi", FakeRtMidiModule(fake))
        adapter = UsbMidiAdapter()
        devices = await adapter.list_devices()
        assert len(devices) == 2
        assert all(isinstance(d, DeviceInfo) for d in devices)
        assert devices[0].name == "Keyboard A"
        assert devices[0].address is None
        assert devices[1].name == "Keyboard B"
        assert devices[1].address is None
