"""
Simple MIDI UART receiver and parser for Note On/Off messages.

This is a lightweight, uasyncio-friendly scaffold. It parses running status and
invokes a registered callback for each note event:

    {"type": "note", "event": "note_on"|"note_off", "channel": n, "note": m, "velocity": v, "ts": ms}

"""
import uasyncio as asyncio
import machine
import time
import ujson as json

# Set to True to enable verbose MIDI event logging on the REPL
DEBUG = False


class MidiReceiver:
    def __init__(self, uart_id=0, rx_pin=17, tx_pin=16, baud=31250, simulate=False):
        self.uart_id = uart_id
        self.rx_pin = rx_pin
        self.tx_pin = tx_pin  # Not used for MIDI input, but required to avoid conflict with pin 0
        self.baud = baud
        self._cb = None
        self._uart = None
        self._running = False
        self.simulate = simulate

    def register_callback(self, cb):
        self._cb = cb

    async def start(self):
        # Initialize UART. Note: pin mapping depends on board
        if not self.simulate:
            try:
                self._uart = machine.UART(self.uart_id, baudrate=self.baud, rx=self.rx_pin, tx=self.tx_pin)
            except Exception:
                try:
                    self._uart = machine.UART(self.uart_id, baudrate=self.baud)
                except Exception:
                    # fall back to simulation mode if UART can't be opened
                    self._uart = None
                    self.simulate = True

        self._running = True
        print('MidiReceiver starting; simulate=' + str(self.simulate))
        if self.simulate:
            asyncio.create_task(self._simulate())
        else:
            asyncio.create_task(self._run())

    async def _run(self):
        last_status = None
        while self._running:
            if not self._uart:
                await asyncio.sleep_ms(10)
                continue
            # read a single byte (non-blocking friendly)
            b = self._uart.read(1)
            if not b:
                await asyncio.sleep_ms(1)
                continue
            byte = b[0]

            if byte & 0x80:
                # status byte
                last_status = byte
                # we only handle note on/off (0x8n and 0x9n) here
                if 0x80 <= (last_status & 0xF0) <= 0x90:
                    # read two data bytes
                    data = self._read_bytes(2)
                    if data is None:
                        continue
                    note = data[0]
                    vel = data[1]
                    chan = last_status & 0x0F
                    if (last_status & 0xF0) == 0x90 and vel != 0:
                        self._emit_note_event("note_on", chan, note, vel)
                    else:
                        self._emit_note_event("note_off", chan, note, vel)
                else:
                    # ignore other status types for now
                    pass
            else:
                # running status: last_status applies
                if last_status is None:
                    # ignore stray data
                    continue
                if 0x80 <= (last_status & 0xF0) <= 0x90:
                    # we already have the first data byte as 'byte'
                    data1 = byte
                    data2_b = self._uart.read(1)
                    if not data2_b:
                        # wait briefly for the next byte
                        await asyncio.sleep_ms(1)
                        data2_b = self._uart.read(1)
                        if not data2_b:
                            continue
                    data2 = data2_b[0]
                    note = data1
                    vel = data2
                    chan = last_status & 0x0F
                    if (last_status & 0xF0) == 0x90 and vel != 0:
                        self._emit_note_event("note_on", chan, note, vel)
                    else:
                        self._emit_note_event("note_off", chan, note, vel)
                else:
                    # ignore
                    pass

    def _read_bytes(self, n, timeout_ms=50):
        if not self._uart:
            return None
        start = time.ticks_ms()
        buf = b""
        while len(buf) < n and (time.ticks_diff(time.ticks_ms(), start) < timeout_ms):
            data = self._uart.read(n - len(buf))
            if data:
                buf += data
        if len(buf) < n:
            return None
        return list(buf)

    def _emit_note_event(self, ev_type, channel, note, velocity):
        obj = {"type": "note", "event": ev_type, "channel": channel, "note": note, "velocity": velocity, "ts": time.ticks_ms()}
        # Log minimal info for debugging
        if DEBUG:
            print('MIDI ->', ev_type, 'ch', channel, 'note', note, 'vel', velocity)
        if self._cb:
            try:
                self._cb(obj)
            except Exception as e:
                try:
                    print('MidiReceiver callback error:', e)
                except Exception:
                    pass

    async def _simulate(self):
        # Generate simple fake notes to allow UI/dev without MIDI hardware.
        while self._running:
            # interval varies with time to simulate presses
            interval = 300 + (time.ticks_ms() % 1700)
            await asyncio.sleep_ms(interval)
            note = 48 + ((time.ticks_ms() // 37) % 25)
            vel = 40 + ((time.ticks_ms() // 97) % 88)
            self._emit_note_event("note_on", 0, int(note), int(vel))
            # short note
            await asyncio.sleep_ms(120)
            self._emit_note_event("note_off", 0, int(note), 0)
