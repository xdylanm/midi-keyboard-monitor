"""Main firmware bootstrap and loop.

Handles configuration, BLE startup, LED and button management and
connects the MIDI parser (`midi.MidiReceiver`) to the BLE transport.
"""
import uasyncio as asyncio
import machine
import time
import ujson

from config import load, save, DEFAULTS
from ble_midi import BLEMidi
from midi import MidiReceiver


# Hardware pins
LED_PIN = 0       # blue LED for BLE status (active-high)
BUTTON_PIN = 15   # active-low push button with pull-up


class LEDController:
    def __init__(self, led_pin_num=LED_PIN):
        self._pin = machine.Pin(led_pin_num, machine.Pin.OUT)
        self._state = "idle"
        self._task = None

    async def _blink(self, on_ms=200, off_ms=800):
        while True:
            self._pin.on()
            await asyncio.sleep_ms(on_ms)
            self._pin.off()
            await asyncio.sleep_ms(off_ms)

    async def _solid(self):
        self._pin.on()
        while True:
            await asyncio.sleep(1)

    def start_searching(self):
        self.stop()
        self._task = asyncio.create_task(self._blink(200, 800))

    def start_connected(self):
        self.stop()
        self._task = asyncio.create_task(self._solid())

    def stop(self):
        if self._task:
            try:
                self._task.cancel()
            except Exception:
                pass
            self._task = None
        try:
            self._pin.off()
        except Exception:
            pass


class ButtonMonitor:
    def __init__(self, pin_num=BUTTON_PIN, hold_ms=5000, callback_hold=None, callback_short=None):
        self._pin = machine.Pin(pin_num, machine.Pin.IN, machine.Pin.PULL_UP)
        self._hold_ms = hold_ms
        self._cb_hold = callback_hold
        self._cb_short = callback_short

    async def run(self):
        pressed = False
        press_start = 0
        while True:
            v = self._pin.value()
            if v == 0 and not pressed:
                # button pressed
                pressed = True
                press_start = time.ticks_ms()
            elif v == 0 and pressed:
                # still pressed
                dur = time.ticks_diff(time.ticks_ms(), press_start)
                if dur >= self._hold_ms:
                    # hold action
                    if self._cb_hold:
                        try:
                            self._cb_hold()
                        except Exception:
                            pass
                    # wait for release
                    while self._pin.value() == 0:
                        await asyncio.sleep_ms(50)
                    pressed = False
            elif v == 1 and pressed:
                # released quickly -> short press
                dur = time.ticks_diff(time.ticks_ms(), press_start)
                if dur < self._hold_ms:
                    if self._cb_short:
                        try:
                            self._cb_short()
                        except Exception:
                            pass
                pressed = False
            await asyncio.sleep_ms(50)


async def midi_event_cb(ev, ble):
    # Only forward MIDI events to BLE when connected (avoid noisy REPL and
    # prevent sending until a client is connected/paired).
    if not ble.is_connected():
        return
    # construct minimal BLE-MIDI packet and send
    if ev.get('type') == 'note':
        status = 0x90 if ev.get('event') == 'note_on' else 0x80
        pkt = BLEMidi.make_midi_packet(status, ev.get('note', 0), ev.get('velocity', 0))
        try:
            ble.midi_tx(pkt)
        except Exception:
            pass


async def main():
    cfg = load(ujson)
    name = cfg.get('device_name', DEFAULTS['device_name'])

    ble = BLEMidi(name=name)

    ble.start()

    led = LEDController()
    if ble.is_connected():
        led.start_connected()
    else:
        led.start_searching()

    # wiring MIDI receiver; use simulate=True when no UART available
    midi = MidiReceiver(simulate=True)
    midi.register_callback(lambda e: asyncio.create_task(midi_event_cb(e, ble)))
    await midi.start()

    # button callbacks
    def on_hold():
        # return to pairing: restart advertising
        try:
            ble.disconnect()
            print('Button: hold -> restart advertising')
        except Exception:
            pass

    def on_short():
        # simulate a single note when connected
        if not ble.is_connected():
            print('Short press: not connected')
            return
        ts = int(time.ticks_ms() & 0x7F)
        note = 60 + ((time.ticks_ms() // 97) % 12)
        vel = 60 + ((time.ticks_ms() // 87) % 64)
        pkt_on = BLEMidi.make_midi_packet(0x90, note, vel)
        pkt_off = BLEMidi.make_midi_packet(0x80, note, 0)
        ble.midi_tx(pkt_on)
        # schedule off after 120ms
        async def _delayed_off():
            await asyncio.sleep_ms(120)
            try:
                ble.midi_tx(pkt_off)
            except Exception:
                pass

        asyncio.create_task(_delayed_off())

    btn = ButtonMonitor(callback_hold=on_hold, callback_short=on_short)
    asyncio.create_task(btn.run())

    # Monitor BLE connect state to update LED
    while True:
        if ble.is_connected():
            led.start_connected()
        else:
            led.start_searching()
        await asyncio.sleep_ms(500)


if __name__ == '__main__':
    asyncio.run(main())
