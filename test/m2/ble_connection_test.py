#!/usr/bin/env python3
"""
Diagnostic — BLE connection smoke-test.

Replicates the exact flow of ble_input_test.py so failures can be debugged
without needing a MIDI keyboard:

  1. Scan via BleAdapter.list_devices() — same UUID filter as the real test.
  2. Pick the target device and pass its address to BleAdapter so connect()
     skips a second scan (root cause of the previous DeviceNotFoundError).
  3. Connect, enumerate GATT services, then disconnect cleanly.

Usage:
    python test/m2/ble_connection_test.py
    python test/m2/ble_connection_test.py "MK Monitor"
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.io.ble_adapter import BleAdapter
from core.io.midi_source import DeviceNotFoundError

BLE_MIDI_SERVICE_UUID = "03b80e5a-ede8-4b33-a751-6ce34ec4c700"


async def main() -> None:
    target_name: str = sys.argv[1] if len(sys.argv) > 1 else "MK Monitor"

    # ------------------------------------------------------------------ #
    # Step 1: scan via BleAdapter.list_devices() — caches BLEDevice objs  #
    # ------------------------------------------------------------------ #
    print(f"Scanning for BLE-MIDI devices (5 s)...")
    adapter = BleAdapter(device_name=target_name, scan_timeout_s=5.0)
    found = await adapter.list_devices()

    if not found:
        print("  (none found — is the BLE dongle powered on and advertising?)")
        return

    print(f"  {len(found)} device(s) found:")
    target_info = None
    for info in found:
        marker = "->" if info.name == target_name else "  "
        print(f"  {marker} name={info.name!r}  addr={info.address}")
        if info.name == target_name:
            target_info = info

    if target_info is None:
        print(f"\nDevice {target_name!r} not in scan results.")
        return

    # ------------------------------------------------------------------ #
    # Step 2: connect — reuses cached BLEDevice, no second scan           #
    # ------------------------------------------------------------------ #
    print(f"\nConnecting to {target_info.name!r} at {target_info.address} ...")

    try:
        await adapter.connect(timeout_s=10.0)
    except DeviceNotFoundError as exc:
        print(f"  DeviceNotFoundError: {exc}")
        return

    print(f"  Connected: {adapter.is_connected()}")

    # ------------------------------------------------------------------ #
    # Step 3: enumerate GATT services to confirm the MIDI characteristic  #
    # ------------------------------------------------------------------ #
    client = adapter._client
    print("\n  GATT services:")
    for svc in client.services:
        is_midi = svc.uuid.lower() == BLE_MIDI_SERVICE_UUID
        print(f"    {'[MIDI]' if is_midi else '      '} {svc.uuid}  {svc.description}")
        for char in svc.characteristics:
            print(f"               char {char.uuid}  [{','.join(char.properties)}]")

    # ------------------------------------------------------------------ #
    # Step 4: clean disconnect                                            #
    # ------------------------------------------------------------------ #
    await adapter.disconnect()
    print("\n  Disconnected cleanly.")


if __name__ == "__main__":
    asyncio.run(main())

