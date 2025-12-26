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
        # self._notify_handle = None
        self._registered = False
        # self._subscribed = False
        print('BLEMidi: initializing, name=', self._name)
        self._init_gatt()

    def _init_gatt(self):
        # Register MIDI service with a single notify characteristic
        # Allow read and write-without-response in addition to notify so
        # centrals (especially some Android clients) can complete setup/subscribe.
        # midi_char = (_MIDI_CHAR_UUID, bt.FLAG_NOTIFY | bt.FLAG_READ | bt.FLAG_WRITE_NO_RESPONSE ,)
        # midi_svc = ( _MIDI_SERVICE_UUID, (midi_char,), )
        # services = (midi_svc,)
        # ((self._notify_handle,),) = self._ble.gatts_register_services(services)
        # self._ble.irq(self._irq_handler)

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
        if self._conn_handle is not None:
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
                        await connection.disconnected()
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

    # def _irq_handler(self, event, data):
    #     # Debug: print raw IRQ events with names and readable payloads so
    #     # pairing/connection failures are easier to diagnose on the REPL.
    #     try:
    #         prefix = 'BLEMidi IRQ: %d' % (event,)

    #         # Format data tuple; convert memoryviews/bytes to hex (truncate)
    #         formatted_parts = []
    #         try:
    #             for part in data:
    #                 if isinstance(part, memoryview) or isinstance(part, (bytes, bytearray)):
    #                     b = bytes(part)
    #                     hx = b.hex()
    #                     if len(hx) > 64:
    #                         hx = hx[:64] + '...'
    #                     formatted_parts.append('<bytes 0x' + hx + '>')
    #                 else:
    #                     formatted_parts.append(str(part))
    #         except Exception:
    #             formatted_parts = [str(data)]

    #         try:
    #             print(prefix + ' ' + '(' + ', '.join(formatted_parts) + ')')
    #         except Exception:
    #             print(prefix, data)
    #     except Exception:
    #         # Ensure IRQ handler doesn't crash if printing fails for any reason
    #         pass

    #     # Support both underscore-prefixed and non-prefixed IRQ constants
    #     if event == _IRQ_CENTRAL_CONNECT:
    #         # (conn_handle, addr_type, addr)
    #         conn_handle, _, _ = data
    #         self._conn_handle = conn_handle
    #         print('BLEMidi: central connected, handle=', conn_handle)
    #     elif event == _IRQ_CENTRAL_DISCONNECT:
    #         conn_handle, _, _ = data
    #         print('BLEMidi: central disconnected, handle=', conn_handle)
    #         if conn_handle == self._conn_handle:
    #             self._conn_handle = None
    #             self._subscribed = False
    #             # resume advertising
    #             self.start_advertising()
    #     elif _IRQ_GATTS_WRITE is not None and event == _IRQ_GATTS_WRITE:
    #         # (conn_handle, attr_handle)
    #         try:
    #             conn_handle, attr_handle = data
    #         except Exception:
    #             conn_handle = data[0]
    #             attr_handle = data[1]
    #         # Read written value
    #         try:
    #             val = self._ble.gatts_read(attr_handle)
    #         except Exception:
    #             val = None
    #         # Pretty-print write
    #         try:
    #             if isinstance(val, (bytes, bytearray, memoryview)):
    #                 hx = bytes(val).hex()
    #                 print('BLEMidi: GATTS_WRITE conn=', conn_handle, 'attr=', attr_handle, 'value=0x' + hx)
    #             else:
    #                 print('BLEMidi: GATTS_WRITE conn=', conn_handle, 'attr=', attr_handle, 'value=', val)
    #         except Exception:
    #             pass
    #         # If write to CCCD (commonly at notify_handle + 1), interpret subscription
    #         try:
    #             if self._notify_handle is not None and attr_handle == (self._notify_handle + 1):
    #                 # CCCD: 0x0001 enables notifications, 0x0002 enables indications
    #                 if val and len(val) >= 2 and bytes(val)[0] == 1:
    #                     self._subscribed = True
    #                     print('BLEMidi: client subscribed to notifications')
    #                 else:
    #                     self._subscribed = False
    #                     print('BLEMidi: client unsubscribed from notifications')
    #         except Exception:
    #             pass


    # def start_advertising(self, interval_us=500000):
    #     # Advertise as a peripheral with name and MIDI service
    #     name = bytes(self._name, 'utf-8')
    #     adv_payload = bytearray()
    #     # Flags
    #     adv_payload += b'\x02\x01\x06'
    #     # Complete local name
    #     adv_payload += bytes([len(name) + 1, 0x09]) + name
    #     # Service UUID (128-bit) - include in scan response would be better, but keep simple
    #     print('BLEMidi: start advertising, name=', self._name)
    #     self._ble.gap_advertise(interval_us, adv_payload)

    # def stop_advertising(self):
    #     # pass None to interval to stop advertising
    #     self._ble.gap_advertise(interval_us=None)

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
        # Different ports expose `gatts_notify` with slightly different signatures.
        # Try the common (conn_handle, value_handle, data) first, then fall back.
        # try:
        #     self._ble.gatts_notify(self._conn_handle, self._notify_handle, midi_bytes)
        #     return True
        # except TypeError:
        #     try:
        #         # Some stubs expect (value_handle, data)
        #         self._ble.gatts_notify(self._notify_handle, midi_bytes)
        #         return True
        #     except Exception:
        #         return False
        # except Exception:
        #     return False

    @staticmethod
    def make_midi_packet(status, note, vel):
        """Create a minimal BLE-MIDI packet for a single MIDI message.

        This is a small, compatible-enough packet for testing single messages.
        It encodes a 13-bit timestamp (milliseconds) into a two-byte header:
        - first byte: upper two bits = 10, lower 6 bits = upper 6 bits of timestamp
        - second byte: MSB = 1, lower 7 bits = lower 7 bits of timestamp
        then the raw MIDI message bytes.
        """
        
        ts = int(time.ticks_ms() & 0x1FFF)  # 13 bits
        high = (ts >> 7) & 0x3F             # upper 6 bits
        low = ts & 0x7F                     # lower 7 bits
        first = 0x80 | high                 # 0b10xxxxxx
        second = 0x80 | low                 # MSB=1 + 7-bit low timestamp
        header = bytes([first, second])
        return header + bytes([status, note, vel])
