# MIDI Keyboard Monitor

Monitor MIDI messages from a keyboard and generate visualizations to help with dynamics and rhythm.

!!! repository "Project Source"

    The project files, including schematic and layout, are available on [github](https://github.com/xdylanm/midi-keyboard-monitor).

## Features

* Connects to the keyboard MIDI out (5 pin DIN plug).
* Raspberry Pi Pico W serves a webpage with live data updates over WebSockets

## Documentation

* [Design](./design.md)
* [Assembly Guide](./assembly.md)
* [Schematic](assets/schematic.pdf)

## References

* Firmware generated with GPT-5 mini (GHCP Agent in VSCode), see the [Firmware Spec](./firmware-spec.md)
* [MIDI 5P DIN Electrical Specs](ttps://midi.org/5-pin-din-electrical-specs)