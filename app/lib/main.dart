import 'dart:async';

import 'package:flutter/material.dart';
import 'ble_service.dart';
import 'models.dart';
import 'velocity_view.dart';
import 'sheet_view.dart';

void main() {
  runApp(MyApp());
}

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
  final List<NoteEvent> _recent = [];
  NoteEvent? _latest;
  StreamSubscription<NoteEvent>? _sub;

  @override
  void initState() {
    super.initState();
    _sub = _ble.events.listen((e) {
      setState(() {
        _latest = e;
        _recent.add(e);
        if (_recent.length > 16) _recent.removeAt(0);
      });
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    _ble.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('MIDI Keyboard Monitor')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            StreamBuilder<bool>(
              stream: _ble.connected,
              builder: (context, snap) {
                final connected = snap.data ?? false;
                return Row(
                  children: [
                    Icon(connected ? Icons.bluetooth_connected : Icons.bluetooth_disabled, color: connected ? Colors.blue : Colors.grey),
                    SizedBox(width: 8),
                    Text(connected ? 'Connected' : 'Not connected'),
                    Spacer(),
                    ElevatedButton(onPressed: _simulatePress, child: Text('Simulate')),
                  ],
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
    _ble.mockConnect();
  }
}
