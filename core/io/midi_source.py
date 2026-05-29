"""
MidiSource abstract base class and exception hierarchy.

All MIDI adapter implementations (USB, BLE) implement MidiSource.
Upstream code that consumes MIDI events depends only on this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Callable, Optional

from core.models import MidiEvent


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MidiSourceError(RuntimeError):
    """Base exception for all MIDI source errors."""


class DeviceNotFoundError(MidiSourceError):
    """No port or device matching the requested name/address was found."""


class MidiConnectionError(MidiSourceError):
    """Device was found but the connection attempt failed or was refused."""


class PacketParseError(MidiSourceError):
    """BLE-MIDI packet is malformed (caught internally; not propagated to caller)."""


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------

@dataclass
class DeviceInfo:
    """
    Identifies a MIDI device returned by MidiSource.list_devices().

    Attributes:
        name:    Human-readable device name (pass to adapter.connect()).
        address: Transport-level address, e.g. Bluetooth MAC (None for USB).
    """
    name: str
    address: Optional[str] = field(default=None)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class MidiSource(ABC):
    """
    Abstract lifecycle interface for a MIDI event source.

    Subclasses implement one physical transport (USB MIDI, BLE MIDI, etc.).
    All upstream code depends only on this interface.

    Lifecycle::

        adapter = SomeAdapter(...)
        adapter.register_callback(on_event)
        await adapter.connect()
        # ... on_event(MidiEvent) is called for each received message ...
        await adapter.disconnect()

    enumerate_devices() is a convention (classmethod or staticmethod) on each
    concrete adapter, not enforced here because USB is synchronous and BLE is
    asynchronous.
    """

    @abstractmethod
    async def connect(self) -> None:
        """
        Open the device connection and begin delivering events to the callback.

        Raises:
            DeviceNotFoundError: if the requested device is not reachable.
            MidiConnectionError: if a connection attempt was refused or failed.
        """

    @abstractmethod
    async def disconnect(self) -> None:
        """Close the connection. No further callbacks will be invoked."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Return True if the adapter is currently connected."""

    @abstractmethod
    def register_callback(self, callback: Callable[[MidiEvent], None]) -> None:
        """
        Register the function to call for each received MidiEvent.

        Only one callback is supported at a time; calling this again replaces
        the previous callback. The callback is always invoked on the asyncio
        event loop thread and must not block.
        """

    @abstractmethod
    async def list_devices(self) -> list[DeviceInfo]:
        """
        Return available devices for this transport.

        For USB adapters: returns available MIDI port names instantly (no scan).
        For BLE adapters: performs a timed radio scan and returns discovered
        devices that advertise the BLE-MIDI service UUID.

        ``DeviceInfo.name`` can be passed directly to ``connect()`` to select a
        specific device. ``DeviceInfo.address`` is populated for BLE devices;
        ``None`` for USB.
        """
