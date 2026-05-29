#!/usr/bin/env python3
"""
Manual Test 1 — USB MIDI Input (Real Keyboard)

Connects to a USB MIDI keyboard and prints each received MidiEvent.
Run this script to validate UsbMidiAdapter against real hardware.

Usage:
    python test/m2/usb_input_test.py
    python test/m2/usb_input_test.py "My Keyboard Name"

Press Ctrl+C to stop.

Evidence to paste in PR notes: the first ~20 lines of event output.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow running from the repo root or from test/m2/.
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.io.usb_midi_adapter import UsbMidiAdapter


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


async def main():
    port_name = sys.argv[1] if len(sys.argv) > 1 else None

    print("Available USB MIDI ports:")
    ports = UsbMidiAdapter.enumerate_devices()
    if not ports:
        print("  (none found — is your keyboard plugged in?)")
        return
    for i, p in enumerate(ports):
        print(f"  [{i}] {p}")

    target = port_name or ports[0]
    print(f"\nConnecting to: {target!r}")

    adapter = UsbMidiAdapter(port_name=target)
    adapter.register_callback(on_event)

    try:
        await adapter.connect()
        print(f"Connected. Play notes on your keyboard (Ctrl+C to stop).\n")
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        await adapter.disconnect()
        print("Disconnected.")


if __name__ == "__main__":
    asyncio.run(main())
