"""
UsbMidiAdapter — real-time USB MIDI input via python-rtmidi.

Implements MidiSource over a class-compliant USB MIDI device.
rtmidi fires its callback on a background thread; this adapter bridges
events to the asyncio event loop via an internal queue.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from core.models import MidiEvent
from core.io.midi_source import MidiSource, DeviceNotFoundError, DeviceInfo

try:
    import rtmidi
except ImportError:  # pragma: no cover
    rtmidi = None  # type: ignore[assignment]

log = logging.getLogger(__name__)


class UsbMidiAdapter(MidiSource):
    """
    Receive MIDI events from a USB MIDI device using python-rtmidi.

    Usage::

        adapter = UsbMidiAdapter(port_name="My Keyboard")
        adapter.register_callback(on_event)
        await adapter.connect()
        ...
        await adapter.disconnect()

    If port_name is None, the first available port is used.
    """

    def __init__(self, port_name: Optional[str] = None) -> None:
        self._port_name = port_name
        self._callback: Optional[Callable[[MidiEvent], None]] = None
        self._midi_in = None
        self._connected = False
        self._queue: Optional[asyncio.Queue] = None
        self._drain_task_handle: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ------------------------------------------------------------------
    # Device enumeration
    # ------------------------------------------------------------------

    @staticmethod
    def enumerate_devices() -> list[str]:
        """
        Return the list of available USB MIDI input port names.

        An empty list indicates no devices are connected or no driver is
        available.  Raises RuntimeError if python-rtmidi is not installed.
        """
        if rtmidi is None:
            raise RuntimeError("python-rtmidi is not installed")
        m = rtmidi.MidiIn()
        ports = list(m.get_ports())
        del m
        return ports

    # ------------------------------------------------------------------
    # MidiSource interface
    # ------------------------------------------------------------------

    def register_callback(self, callback: Callable[[MidiEvent], None]) -> None:
        self._callback = callback

    async def list_devices(self) -> list[DeviceInfo]:
        """Return available USB MIDI ports as DeviceInfo objects (address is None for USB)."""
        return [DeviceInfo(name=p) for p in self.enumerate_devices()]

    async def connect(self) -> None:
        """
        Open the USB MIDI port and start delivering events.

        Raises:
            RuntimeError: if python-rtmidi is not installed.
            DeviceNotFoundError: if no matching port is found.
        """
        if rtmidi is None:
            raise RuntimeError("python-rtmidi is not installed")

        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()

        ports = self.enumerate_devices()
        if self._port_name is None:
            if not ports:
                raise DeviceNotFoundError("No USB MIDI devices found")
            port_idx = 0
        else:
            try:
                port_idx = ports.index(self._port_name)
            except ValueError:
                raise DeviceNotFoundError(
                    f"No USB MIDI device named {self._port_name!r}. "
                    f"Available: {ports}"
                )

        self._midi_in = rtmidi.MidiIn()
        self._midi_in.set_callback(self._rtmidi_callback)
        self._midi_in.open_port(port_idx)
        self._connected = True
        self._drain_task_handle = asyncio.create_task(self._drain_task())
        log.info("UsbMidiAdapter: connected to port %r (index %d)", self._port_name or ports[0], port_idx)

    async def disconnect(self) -> None:
        """Close the port and stop delivering events."""
        self._connected = False
        if self._drain_task_handle:
            self._drain_task_handle.cancel()
            try:
                await self._drain_task_handle
            except asyncio.CancelledError:
                pass
            self._drain_task_handle = None
        if self._midi_in is not None:
            self._midi_in.close_port()
            del self._midi_in
            self._midi_in = None
        log.info("UsbMidiAdapter: disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Internal: rtmidi thread → asyncio bridge
    # ------------------------------------------------------------------

    def _rtmidi_callback(self, message_and_delta, data=None) -> None:
        """Called by rtmidi on its background thread for each received message."""
        message, _delta_time = message_and_delta
        ts_ms = time.monotonic() * 1000.0
        # Bridge to the asyncio event loop safely from any thread.
        if self._loop is not None and self._queue is not None:
            self._loop.call_soon_threadsafe(self._queue.put_nowait, (list(message), ts_ms))

    async def _drain_task(self) -> None:
        """Drain the internal queue and fire the user callback on the event loop."""
        try:
            while True:
                message, ts_ms = await self._queue.get()
                event = self._parse_message(message, ts_ms)
                if event is not None and self._callback is not None:
                    self._callback(event)
        except asyncio.CancelledError:
            pass

    # ------------------------------------------------------------------
    # Internal: MIDI byte parsing
    # ------------------------------------------------------------------

    def _parse_message(self, message_bytes: list[int], timestamp_ms: float) -> Optional[MidiEvent]:
        """Convert raw MIDI bytes to a MidiEvent. Returns None for empty messages."""
        if not message_bytes:
            return None

        status = message_bytes[0]
        msg_type = status & 0xF0
        channel = status & 0x0F

        def _note() -> int:
            return message_bytes[1] if len(message_bytes) > 1 else 0

        def _vel() -> int:
            return message_bytes[2] if len(message_bytes) > 2 else 0

        def _event(ev_type: str, note=None, velocity=None) -> MidiEvent:
            return MidiEvent(
                type=ev_type,
                channel=channel,
                note=note,
                velocity=velocity,
                timestamp_ticks=0,
                timestamp_ms=timestamp_ms,
            )

        if msg_type == 0x80:  # Note Off
            return _event("note_off", note=_note(), velocity=_vel())
        if msg_type == 0x90:  # Note On (velocity 0 → note_off)
            vel = _vel()
            return _event("note_on" if vel > 0 else "note_off", note=_note(), velocity=vel)
        if msg_type == 0xB0:  # Control Change
            return _event("control_change")
        if msg_type == 0xC0:  # Program Change
            return _event("program_change")
        if msg_type == 0xE0:  # Pitch Bend
            return _event("pitch_bend")

        return _event("other")
