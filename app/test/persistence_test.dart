import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

import 'package:midi_keyboard_monitor_app/testing/simulated_midi.dart';
import 'package:midi_keyboard_monitor_app/models.dart';
import 'package:midi_keyboard_monitor_app/persistence.dart';

void main() {
  group('persistence', () {
    late Directory tmp;

    setUpAll(() async {
      tmp = await Directory.systemTemp.createTemp('mkm_test');
      setAppDocsDirForTest(tmp);
    });

    tearDownAll(() async {
      try {
        await tmp.delete(recursive: true);
      } catch (_) {}
    });

    test('save and load practice plan', () async {
      final plan = PracticePlan(
        id: 'test-1',
        name: 'Test Plan',
        key: 'C',
        mode: 'constant',
        scaleType: 'major',
        octaves: 1,
        hand: 'HT',
        handSplit: HandSplit(strategy: 'automatic', splitMidiNote: 60),
        tempoBpm: 60,
        accuracyPercent: 80,
      );
      await savePracticePlan(plan);
      final loaded = await loadPracticePlanById('test-1');
      expect(loaded, isNotNull);
      expect(loaded!.name, equals('Test Plan'));
      final all = await loadAllPracticePlans();
      expect(all.any((p) => p.id == 'test-1'), isTrue);
    });

    test('save and load global config', () async {
      final cfg = GlobalConfig(version: '1', mapping: 'square_root', calibration: Calibration(mode: 'manual', min: 0.1, max: 0.9), autoBackupEnabled: true);
      await saveGlobalConfig(cfg);
      final loaded = await loadGlobalConfig();
      expect(loaded, isNotNull);
      expect(loaded!.mapping, equals('square_root'));
      expect(loaded.calibration.min, closeTo(0.1, 1e-6));
    });

    test('simulated midi can play and not affect persistence', () async {
      final sim = SimulatedMidi();
      final seq = SimulatedMidi.generateScale(root: 60, scale: 'major', octaves: 1, tempoBpm: 60000, velocity: 80, seed: 42);
      // Play quickly by using very high tempo (1ms between notes)
      await sim.playSequence(seq, startDelay: Duration(milliseconds: 0));
      sim.dispose();

      // Ensure plan file still exists
      final dir = Directory('${tmp.path}/practice_plans');
      expect(await dir.exists(), isTrue);
    });
  });
}
