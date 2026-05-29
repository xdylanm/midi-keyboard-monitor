"""
BleAdapter — real-time BLE-MIDI input via bleak.

Implements MidiSource over the project's BLE dongle (Raspberry Pi Pico W)
or any device advertising the standard BLE-MIDI GATT service.

BLE-MIDI 1.0 packet format
---------------------------
Byte 0  - Header:     [ 1 1 ts5 ts4 ts3 ts2 ts1 ts0 ]  (bits 7:6 always 11)
Per event:
  Byte N  - Timestamp: [ 1 0 ts6 ts5 ts4 ts3 ts2 ts1 ts0 ] (bits 7:6 always 10)
  Byte N+1 - MIDI Status (optional under running status)
  Byte N+2+ - MIDI data bytes

13-bit timestamp = (header & 0x3F) << 7 | (timestamp_byte & 0x7F)
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

from core.models import MidiEvent
from core.io.midi_source import MidiSource, DeviceNotFoundError, PacketParseError, DeviceInfo

try:
    from bleak import BleakScanner, BleakClient
except ImportError:  # pragma: no cover
    BleakScanner = None  # type: ignore[assignment,misc]
    BleakClient = None   # type: ignore[assignment,misc]

log = logging.getLogger(__name__)

BLE_MIDI_SERVICE_UUID = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"
MIDI_CHAR_UUID = "7772e5db-3868-4112-a1a9-f2669d106bf3"

# Number of MIDI data bytes per channel message type (high nibble).
_DATA_BYTES: dict[int, int] = {
    0x80: 2,  # Note Off
    0x90: 2,  # Note On
    0xA0: 2,  # Aftertouch
    0xB0: 2,  # Control Change
    0xC0: 1,  # Program Change
    0xD0: 1,  # Channel Pressure
    0xE0: 2,  # Pitch Bend
}


class BleAdapter(MidiSource):
    """
    Receive MIDI events from a BLE-MIDI device using bleak.

    Usage::

        adapter = BleAdapter(device_name="MK Monitor")
        adapter.register_callback(on_event)
        await adapter.connect()
        ...
        await adapter.disconnect()

    If device_name is None, the first discovered BLE-MIDI device is used.
    """

    def __init__(
        self,
        device_name: Optional[str] = None,
        scan_timeout_s: float = 5.0,
        require_midi_service: bool = True,
    ) -> None:
        self._device_name = device_name
        self._scan_timeout_s = scan_timeout_s
        self._require_midi_service = require_midi_service
        self._callback: Optional[Callable[[MidiEvent], None]] = None
        self._disconnect_callback: Optional[Callable[[], None]] = None
        self._client = None
        self._connected = False
        # Populated by list_devices(); reused by connect() to avoid a second scan.
        self._ble_device_cache: dict[str, object] = {}  # address -> BLEDevice

    # ------------------------------------------------------------------
    # Device enumeration
    # ------------------------------------------------------------------

    @staticmethod
    async def enumerate_devices(timeout_s: float = 5.0) -> list[str]:
        """
        Scan for BLE-MIDI devices and return their advertisement names.

        Only devices advertising the BLE-MIDI service UUID are included.
        Raises RuntimeError if bleak is not installed.
        """
        if BleakScanner is None:
            raise RuntimeError("bleak is not installed")
        discovered = await BleakScanner.discover(timeout=timeout_s, return_adv=True)
        results = []
        for d, adv in discovered.values():
            if BLE_MIDI_SERVICE_UUID in [u.lower() for u in adv.service_uuids] and d.name:
                results.append(d.name)
        return results

    async def list_devices(self) -> list[DeviceInfo]:
        """
        Scan for BLE-MIDI devices and return them as DeviceInfo objects.

        Only devices advertising the BLE-MIDI service UUID are included.
        Both name and address (Bluetooth MAC) are populated in each DeviceInfo.
        Raises RuntimeError if bleak is not installed.
        """
        if BleakScanner is None:
            raise RuntimeError("bleak is not installed")
        discovered = await BleakScanner.discover(timeout=self._scan_timeout_s, return_adv=True)
        self._ble_device_cache.clear()
        results = []
        for d, adv in discovered.values():
            if BLE_MIDI_SERVICE_UUID in [u.lower() for u in adv.service_uuids] and d.name:
                self._ble_device_cache[str(d.address)] = d
                results.append(DeviceInfo(name=d.name, address=str(d.address)))
        return results

    # ------------------------------------------------------------------
    # MidiSource interface
    # ------------------------------------------------------------------

    def register_callback(self, callback: Callable[[MidiEvent], None]) -> None:
        self._callback = callback

    def register_disconnect_callback(self, callback: Callable[[], None]) -> None:
        """Register an optional callback invoked when the device disconnects unexpectedly."""
        self._disconnect_callback = callback

    async def connect(self, timeout_s: float = 10.0) -> None:
        """
        Establish a BLE connection.

        If list_devices() was called on this instance first, the BLEDevice
        object from that scan is reused directly — no second scan is needed.
        This is important on Windows where connecting by address string alone
        is unreliable; bleak requires the BLEDevice object from a recent scan.

        Raises:
            RuntimeError: if bleak is not installed.
            DeviceNotFoundError: if no matching device is found during the scan.
        """
        if BleakScanner is None or BleakClient is None:
            raise RuntimeError("bleak is not installed")

        # Prefer a BLEDevice object from a prior list_devices() scan on this
        # instance — avoids a second scan and the Windows address-string issue.
        target = None
        for cached_device in self._ble_device_cache.values():
            if self._device_name is None or getattr(cached_device, "name", None) == self._device_name:
                target = cached_device
                break

        if target is None:
            # No cache hit — run a fresh callback-based scan.
            found_event = asyncio.Event()

            def _detection_callback(device, adv) -> None:
                nonlocal target
                if target is not None:
                    return
                if self._require_midi_service:
                    if BLE_MIDI_SERVICE_UUID not in [u.lower() for u in adv.service_uuids]:
                        return
                if self._device_name is None or device.name == self._device_name:
                    target = device
                    found_event.set()

            scanner = BleakScanner(detection_callback=_detection_callback)
            await scanner.start()
            try:
                await asyncio.wait_for(found_event.wait(), timeout=self._scan_timeout_s)
            except asyncio.TimeoutError:
                pass
            finally:
                await scanner.stop()

        if target is None:
            suffix = f" named {self._device_name!r}" if self._device_name else ""
            raise DeviceNotFoundError(f"No BLE-MIDI device found{suffix}")

        self._client = BleakClient(target, disconnected_callback=self._on_disconnect)
        await self._client.connect(timeout=timeout_s)
        await self._client.start_notify(MIDI_CHAR_UUID, self._notification_handler)
        self._connected = True
        log.info("BleAdapter: connected to %r", target.name)

    async def disconnect(self) -> None:
        """Unsubscribe notifications and close the BLE connection."""
        self._connected = False
        if self._client is not None:
            try:
                await self._client.stop_notify(MIDI_CHAR_UUID)
            except Exception:  # noqa: BLE001
                pass
            try:
                await self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._client = None
        log.info("BleAdapter: disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Internal: BLE notification → MidiEvent
    # ------------------------------------------------------------------

    def _on_disconnect(self, client) -> None:
        """Called by bleak when the device disconnects unexpectedly."""
        self._connected = False
        log.warning("BleAdapter: device disconnected unexpectedly")
        if self._disconnect_callback is not None:
            self._disconnect_callback()

    def _notification_handler(self, handle, data: bytearray) -> None:
        """Called by bleak on the asyncio event loop for each GATT notification."""
        base_ts_ms = time.monotonic() * 1000.0
        try:
            events = self._parse_ble_midi_packet(data, base_ts_ms)
        except PacketParseError as exc:
            log.warning("BleAdapter: %s", exc)
            return
        if self._callback is not None:
            for event in events:
                self._callback(event)

    def _parse_ble_midi_packet(
        self, data: bytearray, base_timestamp_ms: float
    ) -> list[MidiEvent]:
        """
        Parse a BLE-MIDI 1.0 notification payload into a list of MidiEvents.

        Malformed bytes are logged and discarded; parsing continues from the
        next recoverable position.  No exception is raised to the caller.
        """
        events: list[MidiEvent] = []
        if len(data) < 2:
            log.debug("BleAdapter: packet too short (%d bytes), skipping", len(data))
            return events

        header = data[0]
        if not ((header & 0x80) and (header & 0x40)):
            log.warning("BleAdapter: invalid header byte 0x%02X (bits 7:6 must be 11)", header)
            return events

        timestamp_high = header & 0x3F
        running_status: Optional[int] = None
        i = 1

        while i < len(data):
            # ---- Expect timestamp byte (bit 7=1, bit 6=0) ----
            b = data[i]
            if not (b & 0x80):
                log.warning("BleAdapter: expected timestamp at offset %d, got 0x%02X", i, b)
                break
            if b & 0x40:
                log.warning("BleAdapter: unexpected second header at offset %d", i)
                break

            timestamp_low = b & 0x7F
            _ts_13bit = (timestamp_high << 7) | timestamp_low  # noqa: F841 (intra-packet ordering)
            i += 1

            if i >= len(data):
                break

            # ---- MIDI status or running-status data ----
            b = data[i]
            if b & 0x80:
                # New MIDI status byte
                running_status = b
                i += 1
            # else: bit 7=0 → data byte; running status from previous message applies

            if running_status is None:
                log.warning("BleAdapter: data byte at offset %d with no running status", i)
                break

            # ---- Collect data bytes ----
            msg_type = running_status & 0xF0
            n_data = _DATA_BYTES.get(msg_type, 0)
            if running_status >= 0xF0:
                # System messages: only SysEx (0xF0) is variable-length; skip all for now
                n_data = 0

            data_bytes: list[int] = []
            for _ in range(n_data):
                if i < len(data) and not (data[i] & 0x80):
                    data_bytes.append(data[i])
                    i += 1
                else:
                    log.warning("BleAdapter: truncated MIDI message (need %d data bytes)", n_data)
                    break

            event = self._build_event(msg_type, running_status, data_bytes, base_timestamp_ms)
            if event is not None:
                events.append(event)

        return events

    def _build_event(
        self,
        msg_type: int,
        status_byte: int,
        data_bytes: list[int],
        timestamp_ms: float,
    ) -> Optional[MidiEvent]:
        channel = status_byte & 0x0F
        note = data_bytes[0] if len(data_bytes) > 0 else None
        vel = data_bytes[1] if len(data_bytes) > 1 else None

        def _e(ev_type: str, n=None, v=None) -> MidiEvent:
            return MidiEvent(
                type=ev_type,
                channel=channel,
                note=n,
                velocity=v,
                timestamp_ticks=0,
                timestamp_ms=timestamp_ms,
            )

        if msg_type == 0x80:  # Note Off
            return _e("note_off", n=note, v=vel if vel is not None else 0)
        if msg_type == 0x90:  # Note On (vel=0 → note_off)
            v = vel if vel is not None else 0
            return _e("note_on" if v > 0 else "note_off", n=note, v=v)
        if msg_type == 0xB0:  # Control Change
            return _e("control_change")
        if msg_type == 0xC0:  # Program Change
            return _e("program_change")
        if msg_type == 0xE0:  # Pitch Bend
            return _e("pitch_bend")
        # Anything else (0xA0, 0xD0, system messages, etc.)
        return _e("other")
