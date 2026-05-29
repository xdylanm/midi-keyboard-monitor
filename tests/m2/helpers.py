"""
Shared mock helpers for M2 automated tests.

These classes replace python-rtmidi and bleak with controllable fakes so
that all adapter tests can run without physical hardware.
"""

from __future__ import annotations

from typing import Callable, Optional


# ---------------------------------------------------------------------------
# USB MIDI fakes (replaces python-rtmidi)
# ---------------------------------------------------------------------------

class FakeRtMidiIn:
    """
    Drop-in replacement for rtmidi.MidiIn in unit tests.

    The test controls which ports are "available" and can inject messages
    by calling inject_message(), which synchronously fires the stored callback.
    """

    def __init__(self, ports: list[str] | None = None) -> None:
        self._ports: list[str] = list(ports or [])
        self._callback: Optional[Callable] = None
        self._open_port_idx: Optional[int] = None

    # --- rtmidi.MidiIn API ---

    def get_ports(self) -> list[str]:
        return list(self._ports)

    def open_port(self, idx: int) -> None:
        self._open_port_idx = idx

    def set_callback(self, callback: Callable) -> None:
        self._callback = callback

    def cancel_callback(self) -> None:
        self._callback = None

    def close_port(self) -> None:
        self._open_port_idx = None

    # --- Test helpers ---

    def inject_message(self, bytes_: list[int], delta_time: float = 0.0) -> None:
        """Synchronously fire the stored rtmidi callback with the given bytes."""
        if self._callback is not None:
            self._callback((list(bytes_), delta_time), None)


class FakeRtMidiModule:
    """
    Replaces the ``rtmidi`` module in usb_midi_adapter.

    ``FakeRtMidiModule.MidiIn()`` always returns the same ``FakeRtMidiIn``
    instance so both ``enumerate_devices`` and ``connect`` share it.
    """

    def __init__(self, midi_in: FakeRtMidiIn) -> None:
        self._instance = midi_in

    def MidiIn(self) -> FakeRtMidiIn:  # noqa: N802
        return self._instance


# ---------------------------------------------------------------------------
# BLE fakes (replaces bleak)
# ---------------------------------------------------------------------------

class FakeBLEDevice:
    """Minimal stand-in for a bleak BLEDevice."""

    def __init__(
        self,
        name: str,
        address: str = "AA:BB:CC:DD:EE:FF",
        include_midi_uuid: bool = True,
    ) -> None:
        self.name = name
        self.address = address
        # Simulate the BLE-MIDI service UUID in the advertisement metadata.
        self.metadata = {
            "uuids": ["03b80e5a-ede8-4b33-a751-6ce34ec4c700"] if include_midi_uuid else []
        }


class FakeBleakScanner:
    """
    Replaces ``BleakScanner`` in ble_adapter module.

    Set ``FakeBleakScanner._devices`` before the test to control what
    ``discover()`` returns, or use ``with_devices()``.

    Note: this is used as a *class* replacement, so ``discover`` is an
    instance method called via the monkeypatched module attribute — Python
    resolves it on the instance, which is fine.
    """

    def __init__(self, devices: list[FakeBLEDevice] | None = None) -> None:
        self._devices: list[FakeBLEDevice] = list(devices or [])

    async def discover(self, timeout: float = 5.0, **kwargs) -> list[FakeBLEDevice]:
        return list(self._devices)


class FakeBleakClient:
    """
    Replaces ``BleakClient`` instances in ble_adapter tests.

    Usage in tests::

        fake_client = FakeBleakClient()
        factory = make_fake_ble_client_factory(fake_client)
        monkeypatch.setattr(ble_module, "BleakClient", factory)

        await adapter.connect()

        # Inject a BLE-MIDI notification:
        from core.io.ble_adapter import MIDI_CHAR_UUID
        fake_client.inject_notification(MIDI_CHAR_UUID, bytearray([0xC0, 0x80, 0x90, 60, 80]))
    """

    def __init__(self) -> None:
        self._connected = False
        self._notify_handlers: dict[str, Callable] = {}
        self._disconnected_callback: Optional[Callable] = None

    # --- bleak.BleakClient async API ---

    async def connect(self, timeout: float = 10.0, **kwargs) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def start_notify(self, char_uuid, handler: Callable) -> None:
        self._notify_handlers[str(char_uuid).lower()] = handler

    async def stop_notify(self, char_uuid) -> None:
        self._notify_handlers.pop(str(char_uuid).lower(), None)

    @property
    def is_connected(self) -> bool:
        return self._connected

    # --- Test helpers ---

    def inject_notification(self, char_uuid, data: bytearray) -> None:
        """Synchronously fire the stored notification handler."""
        handler = self._notify_handlers.get(str(char_uuid).lower())
        if handler is not None:
            handler(None, data)

    def simulate_disconnect(self) -> None:
        """Trigger the disconnected_callback as bleak would on unexpected disconnect."""
        self._connected = False
        if self._disconnected_callback is not None:
            self._disconnected_callback(self)


def make_fake_ble_client_factory(fake_client: FakeBleakClient) -> Callable:
    """
    Return a callable that can replace ``BleakClient`` in the adapter module.

    When the adapter calls ``BleakClient(device, disconnected_callback=cb)``,
    this factory captures the callback on ``fake_client`` and returns it.
    """
    def _factory(device, disconnected_callback=None, **kwargs):
        fake_client._disconnected_callback = disconnected_callback
        return fake_client

    return _factory
