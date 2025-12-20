"""
Simple bootstrap for the Pico W MIDI Keyboard Monitor.

This file is a scaffold: it loads `config.json`, starts Wi-Fi (station or AP),
and starts the `midi` and `webserver` modules.
"""
import uasyncio as asyncio
import json
import machine
import time

CONFIG_PATH = "config.json"
WIFI_SSID = "ssid"
WIFI_PASSWORD = "password"

def load_config():
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except Exception:
        # sensible defaults
        return {
            "wifi": {"ssid": WIFI_SSID, "password": WIFI_PASSWORD},
            "midi": {"channel": "all", "uart_rx_pin": 17},
            "smoothing": {"window": 1},
            "server": {"port": 80},
            "simulate": True
        }

async def start():
    cfg = load_config()

    # Defer imports so this file can be safely imported on host for tests
    try:
        import network
        wlan = network.WLAN(network.STA_IF)
    except Exception:
        wlan = None

    # Try to connect to Wi-Fi if configured; otherwise AP fallback handled by webserver
    led = None
    search_task = None
    if wlan:
        try:
            wlan.active(True)

            networks = wlan.scan()
            print("Available networks:")
            for net in networks:
                ssid = net[0].decode()
                rssi = net[3]
                print("  SSID: {}, RSSI: {}".format(ssid, rssi))

            print('Wi-Fi: attempting to connect to', cfg['wifi']['ssid'])

            # start LED search blink
            led = machine.Pin("LED", machine.Pin.OUT)
            async def led_search():
                while True:
                    led.toggle()
                    await asyncio.sleep_ms(300)
                    led.toggle()
                    await asyncio.sleep_ms(700)
            search_task = asyncio.create_task(led_search())

            wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            # wait briefly for connection
            for _ in range(40):
                if wlan.status() >= 3:
                    break
                await asyncio.sleep(0.5)

            if wlan.status() == 3:
                ip = wlan.ifconfig()
                print('Wi-Fi connected, IP:', ip[0])
                # stop search blink
                if search_task:
                    try:
                        search_task.cancel()
                    except Exception:
                        pass
                # solid LED for 2s
                if led:
                    led.value(1)
                    await asyncio.sleep_ms(2000)
                    led.value(0)
            else:
                print('Wi-Fi: connection failed or timeout')
        except Exception as e:
            print('Wi-Fi error:', e)
    else:
        print('network module not available; running without Wi-Fi')

    # Start midi and webserver
    import midi
    import webserver

    ws = webserver.WebServer(port=cfg.get("server", {}).get("port", 80))
    midi_receiver = midi.MidiReceiver(rx_pin=cfg.get("midi", {}).get("uart_rx_pin", 17), simulate=cfg.get("midi", {}).get("simulate", False))

    # register callback: forward MIDI note events to webserver broadcast
    async def _led_pulse():
        if led:
            try:
                led.value(1)
            except Exception:
                pass
            await asyncio.sleep_ms(80)
            try:
                led.value(0)
            except Exception:
                pass

    def note_cb(ev):
        try:
            # print('MIDI event:', ev)
            ws.broadcast(ev)
            # indicate MIDI activity with a short blink
            try:
                asyncio.create_task(_led_pulse())
            except Exception:
                pass
        except Exception as e:
            print('Error in note callback:', e)

    midi_receiver.register_callback(note_cb)

    # start services
    await ws.start()
    # start MIDI receiver if enabled
    await midi_receiver.start()

    print('Services started; entering main wait loop')
    # keep the main task alive to serve clients; wait forever
    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass


def run():
    print('Starting MIDI Keyboard Monitor...')
    try:
        asyncio.run(start())
    except Exception:
        # If asyncio.run is not available fallback to loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(start())


if __name__ == "__main__":
    while True:
        run()
        time.sleep(5)
    print("Main loop terminated.")
