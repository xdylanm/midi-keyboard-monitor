import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_reactive_ble/flutter_reactive_ble.dart';
import 'package:flutter/foundation.dart';
import 'models.dart';

class BleService {
  final _eventController = StreamController<NoteEvent>.broadcast();
  Stream<NoteEvent> get events => _eventController.stream;

  final _connectionStateController = StreamController<bool>.broadcast();
  Stream<bool> get connected => _connectionStateController.stream;

  final FlutterReactiveBle _ble = FlutterReactiveBle();
  StreamSubscription<DiscoveredDevice>? _scanSub;
  StreamSubscription<ConnectionStateUpdate>? _connSub;
  StreamSubscription<List<int>>? _notifySub;

  // BLE MIDI service/characteristic
  static final Uuid _midiService = Uuid.parse('03B80E5A-EDE8-4B33-A751-6CE34EC4C700');
  static final Uuid _midiChar = Uuid.parse('7772E5DB-3868-4112-A1A9-F2669D106BF3');

  String? _connectedDeviceId;

  BleService() {
    debugPrint('Starting BLE service');
    _startScan();
  }

  void dispose() {
    _scanSub?.cancel();
    _connSub?.cancel();
    _notifySub?.cancel();
    _eventController.close();
    _connectionStateController.close();
  }

  void _startScan() {
    _scanSub?.cancel();
    debugPrint('BleService: starting scan (MIDI service filter)');
    _scanSub = _ble.scanForDevices(withServices: [_midiService]).listen((device) {
      debugPrint('BleService: discovered device: ${device.id} name=${device.name}');
      // Connect to the first device found (only if not already connected).
      if (_connectedDeviceId == null) {
        _connectTo(device.id);
      }
    }, onError: (e) {
      debugPrint('BleService: scan error: $e');
    });
  }

  void _connectTo(String deviceId) {
    _connSub?.cancel();
    debugPrint('BleService: connecting to $deviceId');
    _connSub = _ble.connectToDevice(id: deviceId, connectionTimeout: const Duration(seconds: 5)).listen((update) {
      debugPrint('BleService: connection update for $deviceId: ${update.connectionState}');
      if (update.connectionState == DeviceConnectionState.connected) {
        _connectedDeviceId = deviceId;
        _connectionStateController.add(true);
        _subscribeToMidi(deviceId);
      } else if (update.connectionState == DeviceConnectionState.disconnected) {
        debugPrint('BleService: disconnected from $deviceId');
        _connectedDeviceId = null;
        _connectionStateController.add(false);
        _notifySub?.cancel();
        // restart scanning
        _startScan();
      }
    }, onError: (e) {
      debugPrint('BleService: connection error for $deviceId: $e');
      _connectionStateController.add(false);
      // try scanning again
      _startScan();
    });
  }

  void _subscribeToMidi(String deviceId) {
    _notifySub?.cancel();
    final char = QualifiedCharacteristic(serviceId: _midiService, characteristicId: _midiChar, deviceId: deviceId);
    debugPrint('BleService: subscribing to MIDI characteristic on $deviceId');
    _notifySub = _ble.subscribeToCharacteristic(char).listen((data) {
      //debugPrint('BleService: notify (${data.length} bytes) from $deviceId');
      _handleMidiPacket(Uint8List.fromList(data));
    }, onError: (e) {
      debugPrint('BleService: subscription error: $e');
    });
  }

  void _handleMidiPacket(Uint8List data) {
    // Simple BLE-MIDI parser tailored to the firmware packets (header byte then raw MIDI bytes).
    //int i = 0;
    //debugPrint('BleService: parsing MIDI packet (${data.length} bytes)');
    if (data.length < 5) {
      debugPrint('BleService: invalid MIDI packet, too short (${data.length} bytes)');
      return;
    }
    // header
    int ts_hi = 0;
    int ts_lo = 0;
    if ((data[0] & 0x80) == 0) {
      debugPrint('BleService: bad MIDI packet header byte 0: 0x${data[0].toRadixString(16).toUpperCase().padLeft(2, '0')}');
      return;
    } else {
      ts_hi = data[0] & 0x3F;
    }

    if ((data[1] & 0x80) == 0) {
      debugPrint('BleService: bad MIDI packet header byte 1: 0x${data[1].toRadixString(16).toUpperCase().padLeft(2, '0')}');
      return;
    } else {
      ts_lo = data[1] & 0x7F;
    }

    final ts = (ts_hi << 7) | ts_lo;

    final status = data[2];
    final status_hi = status & 0xF0;
    if (status_hi == 0x90) {
      final note = data[3];
      final vel = data[4];
      final channel = status & 0x0F;
      final ev = NoteEvent(isNoteOn: true, channel: channel, note: note, velocity: vel, tsMs: ts);
      _eventController.add(ev);
    }
  }

  // Test hook: keep simulate helper during development
  void simulateNote(int note, int velocity, {int channel = 0}) {
    final e = NoteEvent(isNoteOn: velocity > 0, channel: channel, note: note, velocity: velocity, tsMs: DateTime.now().millisecondsSinceEpoch & 0xFFFF);
    _eventController.add(e);
  }

  @visibleForTesting
  void mockConnect() {
    _connectionStateController.add(true);
  }

  @visibleForTesting
  void mockDisconnect() {
    _connectionStateController.add(false);
  }
}
