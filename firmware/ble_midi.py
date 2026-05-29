"""
BLE-MIDI scaffold using MicroPython's ubluetooth.

Provides a simple BLE GATT server that advertises the standard
BLE-MIDI service and a MIDI Data characteristic (notify).

This is intentionally small and focused for scaffolding and testing.
"""
import aioble
import bluetooth as bt
import time
import asyncio

# from the docs: in order to save space in the firmware, [the full list of] constants are not 
# included on the bluetooth module. Add the ones that you need from the list above to your program.
from micropython import const
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_CONNECTION_UPDATE = const(27)

_MIDI_SERVICE_UUID = bt.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
_MIDI_CHAR_UUID = bt.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")

_ADV_INTERVAL_MS = 500

class BLEMidi:
    def __init__(self, ble=None, name="MK Monitor"):
        self._ble = ble or bt.BLE()
        self._ble.active(True)
        self._name = name
        self._midi_characteristic = None
        self._midi_service = None
        self._conn_handle = None
        self._registered = False
        print('BLEMidi: initializing, name=', self._name)
        self._init_gatt()

    def _init_gatt(self):
        self._midi_service = aioble.Service(_MIDI_SERVICE_UUID)
        self._midi_characteristic = aioble.Characteristic(
            service=self._midi_service,
            uuid=_MIDI_CHAR_UUID,
            read=True,
            write_no_response=True,
            notify=True)
        aioble.register_services(self._midi_service)

        print('BLEMidi: GATT registered')   #, notify_handle=', self._notify_handle)
        self._registered = True

    def start(self):
        """Create and return the peripheral task."""
        return asyncio.create_task(self.peripheral_task())
    
    def disconnect(self):
        """Stop BLE advertising and disconnect if connected."""
        if self.is_connected():
            print("Disconnecting...")
            self._conn_handle.disconnect()
            self._conn_handle = None

    async def peripheral_task(self):
        while True:
            try:
                async with await aioble.advertise(
                    _ADV_INTERVAL_MS,
                    name=self._name,
                    services=[_MIDI_SERVICE_UUID]
                    ) as connection:
                        print("Connection from", connection.device)
                        self._conn_handle = connection
                        # try:
                        #     print("Pairing ...")
                        #     await connection.pair(le_secure=False)
                        #     print("... Paired")
                        # except Exception as e:
                        #     print("Pairing failed:", e)
                        await self._conn_handle.disconnected()
                        print("Disconnected")
                        self._conn_handle = None
            except asyncio.CancelledError:
                # Catch the CancelledError
                print("Peripheral task cancelled")
            except Exception as e:
                print("Error in peripheral_task:", e)
            finally:
                # Ensure the loop continues to the next iteration
                await asyncio.sleep_ms(100)

    def is_connected(self):
        return self._conn_handle is not None

    def midi_tx(self, midi_bytes: bytes):
        """Send raw BLE-MIDI packet (already formatted) as a notification.

        If not connected the call is a no-op.
        """
        if not self.is_connected():
            return False
        
        try: 
            if self._midi_characteristic is not None:
                self._midi_characteristic.write(data=midi_bytes, send_update=True)
                return True
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def make_midi_packet(status, note, vel):
        """Create a minimal BLE-MIDI packet for a single MIDI message.

        Encodes a 13-bit timestamp (milliseconds) per the BLE-MIDI 1.0 spec:
        - header byte:    bits 7:6 = 11, bits 5:0 = upper 6 bits of timestamp
        - timestamp byte: bits 7:6 = 10, bits 6:0 = lower 7 bits of timestamp
        then the raw MIDI message bytes.
        """
        ts = int(time.ticks_ms() & 0x1FFF)  # 13 bits
        high = (ts >> 7) & 0x3F             # upper 6 bits
        low = ts & 0x7F                     # lower 7 bits
        first = 0xC0 | high                 # 0b11xxxxxx  (header)
        second = 0x80 | low                 # 0b10xxxxxxx (timestamp byte)
        header = bytes([first, second])
        return header + bytes([status, note, vel])
