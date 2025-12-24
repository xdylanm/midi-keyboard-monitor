import 'dart:async';

import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:flutter/foundation.dart';
import 'models.dart';

class BleService {
  final _eventController = StreamController<NoteEvent>.broadcast();
  Stream<NoteEvent> get events => _eventController.stream;

  final _connectionStateController = StreamController<bool>.broadcast();
  Stream<bool> get connected => _connectionStateController.stream;

  // Placeholder: real implementation uses flutter_reactive_ble to host peripheral
  // Note: Android BLE peripheral support is limited; this is a client-focused stub

  BleService() {
    // For now, seed with no-op. Provide a test hook.
  }

  void dispose() {
    _eventController.close();
    _connectionStateController.close();
  }

  // Test hook: simulate an incoming Note On event
  void simulateNote(int note, int velocity, {int channel = 0}) {
    final e = NoteEvent(isNoteOn: velocity > 0, channel: channel, note: note, velocity: velocity, tsMs: DateTime.now().millisecondsSinceEpoch & 0xFFFF);
    _eventController.add(e);
  }

  // In a full implementation this would handle BLE advertising, GATT, and MIDI characteristic writes.
  @visibleForTesting
  void mockConnect() {
    _connectionStateController.add(true);
  }

  @visibleForTesting
  void mockDisconnect() {
    _connectionStateController.add(false);
  }
}
