#!/usr/bin/env python3
"""
Manual Test 2 — BLE MIDI Input (Dongle)

Connects to the project BLE dongle ("MK Monitor") and prints each received
MidiEvent.  Run this script to validate BleAdapter against real hardware.

Usage:
    python test/m2/ble_input_test.py
    python test/m2/ble_input_test.py "MK Monitor"

Press Ctrl+C to stop.

Evidence to paste in PR notes: the first ~20 lines of event output alongside
the USB test output, to confirm note-for-note equivalence.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from the repo root or from test/m2/.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.io.ble_adapter import BleAdapter


def on_event(event):
    note_name = ""
    if event.note is not None:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (event.note // 12) - 1
        note_name = f" ({names[event.note % 12]}{octave})"
    print(
        f"  {event.type:<12}  ch={event.channel}"
        f"  note={event.note}{note_name}"
        f"  vel={event.velocity}"
        f"  ts={event.timestamp_ms:.1f} ms"
    )


def on_disconnect():
    print("\n[BleAdapter] Device disconnected unexpectedly.")


async def main():
    device_name = sys.argv[1] if len(sys.argv) > 1 else "MK Monitor"

    print(f"Scanning for BLE-MIDI devices (5 s)...")
    found = await BleAdapter.enumerate_devices(timeout_s=5.0)
    if not found:
        print("  (none found — is the BLE dongle powered on and advertising?)")
        return
    print("Discovered BLE-MIDI devices:")
    for name in found:
        print(f"  • {name}")

    print(f"\nConnecting to: {device_name!r}")
    adapter = BleAdapter(device_name=device_name)
    adapter.register_callback(on_event)
    adapter.register_disconnect_callback(on_disconnect)

    try:
        await adapter.connect()
        print(f"Connected. Play notes on your keyboard (Ctrl+C to stop).\n")
        while adapter.is_connected():
            await asyncio.sleep(0.5)
        print("Connection lost.")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await adapter.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
