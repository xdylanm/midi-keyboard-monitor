import 'dart:async';

import 'package:flutter/material.dart';
// import 'package:permission_handler/permission_handler.dart';
import 'ble_service.dart';
import 'testing/simulated_midi.dart';
import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:flutter/services.dart';
import 'models.dart';
import 'settings_page.dart';
import 'velocity_view.dart';
import 'sheet_view.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // await _requestBlePermissions();
  runApp(MyApp());
}

// Future<void> _requestBlePermissions() async {
//   try {
//     if (Platform.isAndroid) {
//       debugPrint('Requesting Android BLE permissions');
//       final statuses = await [
//         Permission.bluetoothScan,
//         Permission.bluetoothConnect,
//         Permission.bluetooth,
//         Permission.location,
//       ].request();
//       debugPrint('Permission statuses: $statuses');
//     } else if (Platform.isIOS) {
//       debugPrint('Requesting iOS Bluetooth permission');
//       final status = await Permission.bluetooth.request();
//       debugPrint('iOS bluetooth permission: $status');
//     }
//   } catch (e) {
//     debugPrint('Permission request failed: $e');
//   }
// }

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'MIDI Keyboard Monitor',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final BleService _ble = BleService();
  SimulatedMidi? _sim;
  final List<NoteEvent> _recent = [];
  NoteEvent? _latest;
  StreamSubscription<NoteEvent>? _sub;
  StreamSubscription<SimulatedMidiNote>? _simSub;
  bool _useSim = false;

  @override
  void initState() {
    super.initState();
    _checkBluetooth();
    _subscribeToSource();
  }

  void _subscribeToSource() {
    _sub?.cancel();
    _simSub?.cancel();
    if (_useSim) {
      // Stop BLE scanning/periodic scan when running simulation to save resources.
      try {
        _ble.stopPeriodicScan();
      } catch (_) {}
      
      _sim ??= SimulatedMidi();
      _simSub = _sim!.stream.listen((s) {
        final e = NoteEvent(isNoteOn: s.noteOn, channel: 0, note: s.note, velocity: s.velocity, tsMs: DateTime.now().millisecondsSinceEpoch & 0xFFFF);
        setState(() {
          _latest = e;
          _recent.add(e);
          if (_recent.length > 16) _recent.removeAt(0);
        });
      });
    } else {
      // Ensure BLE scanning is active when not using simulation.
      try {
        _ble.startPeriodicScan();
      } catch (_) {}

      _sub = _ble.events.listen((e) {
        setState(() {
          _latest = e;
          _recent.add(e);
          if (_recent.length > 16) _recent.removeAt(0);
        });
      });
    }
  }

  Future<void> _checkBluetooth() async {
    try {
      final bleApi = FlutterReactiveBle();
      // Wait for a stable status (skip transient `unknown`) with a short timeout.
      final status = await bleApi.statusStream
          .firstWhere((s) => s != BleStatus.unknown)
          .timeout(const Duration(seconds: 3));
      debugPrint('Ble status: $status');
      if (status == BleStatus.poweredOff) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          showDialog<void>(
            context: context,
            barrierDismissible: false,
            builder: (context) => AlertDialog(
              title: Text('Bluetooth is off'),
              content: Text('Bluetooth appears to be disabled. Please enable Bluetooth to use the MIDI monitor.'),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.of(context).pop();
                  },
                  child: Text('OK'),
                ),
                TextButton(
                  onPressed: () {
                    Navigator.of(context).pop();
                    _checkBluetooth();
                  },
                  child: Text('Retry'),
                ),
                TextButton(
                  onPressed: () async {
                    Navigator.of(context).pop();
                    const channel = MethodChannel('midi_keyboard_monitor_app/bluetooth');
                    try {
                      await channel.invokeMethod('requestEnable');
                      // Wait for BLE to become ready, then trigger a scan.
                      try {
                        await bleApi.statusStream.firstWhere((s) => s == BleStatus.ready).timeout(const Duration(seconds: 8));
                        _ble.startScan();
                      } catch (e) {
                        debugPrint('Waiting for BLE ready failed: $e');
                      }
                    } catch (e) {
                      debugPrint('Platform requestEnable failed: $e');
                    }
                  },
                  child: Text('Enable'),
                ),
              ],
            ),
          );
        });
      }
    } on TimeoutException catch (e) {
      debugPrint('BLE status check timed out: $e');
    } catch (e) {
      debugPrint('Error checking BLE status: $e');
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    _simSub?.cancel();
    // Request a clean disconnect before disposing the BLE service.
    _ble.disconnect();
    _ble.dispose();
    _sim?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('MIDI Keyboard Monitor'), actions: [IconButton(icon: Icon(Icons.settings), onPressed: () { Navigator.of(context).push(MaterialPageRoute(builder: (_) => SettingsPage())); })]),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            StreamBuilder<bool>(
              stream: _ble.connected,
              builder: (context, snap) {
                final connected = snap.data ?? false;
                return StreamBuilder<bool>(
                  stream: _ble.scanning,
                  builder: (context, scanSnap) {
                    final scanning = scanSnap.data ?? false;
                    final label = connected ? 'Connected' : (scanning ? 'Scanning' : 'Not connected');
                    final icon = connected ? Icons.bluetooth_connected : Icons.bluetooth_disabled;
                    return Row(
                      children: [
                        Icon(icon, color: connected ? Colors.blue : (scanning ? Colors.orange : Colors.grey)),
                        SizedBox(width: 8),
                        Text(label),
                        Spacer(),
                            ElevatedButton(onPressed: _simulatePress, child: Text('Simulate')),
                            SizedBox(width: 8),
                            Row(
                              children: [
                                Text('Use Simulated MIDI'),
                                Switch(value: _useSim, onChanged: (v) {
                                  setState(() {
                                    _useSim = v;
                                    _subscribeToSource();
                                  });
                                }),
                                if (_useSim)
                                  ElevatedButton(
                                    onPressed: () {
                                      // play a default one-octave C4 major scale at 60 BPM
                                      final seq = SimulatedMidi.generateScale(root: 60, scale: 'major', octaves: 1, tempoBpm: 60, velocity: 80, seed: 42);
                                      _sim?.playSequence(seq);
                                    },
                                    child: Text('Play Sequence'),
                                  ),
                              ],
                            ),
                      ],
                    );
                  },
                );
              },
            ),
            SizedBox(height: 24),
            VelocityView(recent: _recent, latest: _latest),
            SizedBox(height: 16),
            Text('Sheet (static): Mary Had a Little Lamb', style: TextStyle(fontSize: 16)),
            SizedBox(height: 8),
            SheetView(),
          ],
        ),
      ),
    );
  }

  void _simulatePress() {
    _ble.simulateNote(60 + (_recent.length % 12), (20 + (_recent.length * 7)) % 128);
  }
}
