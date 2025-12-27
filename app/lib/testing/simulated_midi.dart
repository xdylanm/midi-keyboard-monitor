// Simulated MIDI provider for testing and validation
// Emits deterministic note-on events (note number, velocity, time offset)

import 'dart:async';
import 'dart:math';
// TODO: replace manual interval tables with `music_notes` helpers
import 'package:music_notes/music_notes.dart';

class SimulatedMidiNote {
  final int note; // MIDI note number (0-127)
  final int velocity; // 0-127
  final Duration timeOffset; // offset from sequence start
  final bool noteOn; // true == note-on

  SimulatedMidiNote({
    required this.note,
    required this.velocity,
    required this.timeOffset,
    this.noteOn = true,
  });
}

class SimulatedMidi {
  final _controller = StreamController<SimulatedMidiNote>.broadcast();
  Stream<SimulatedMidiNote> get stream => _controller.stream;

  bool get isClosed => _controller.isClosed;

  /// Play a precomputed sequence. Events are scheduled relative to now.
  /// Returns a Future that completes when the latest event has been scheduled.
  Future<void> playSequence(List<SimulatedMidiNote> sequence,
      {Duration startDelay = const Duration(milliseconds: 50)}) async {
    if (_controller.isClosed) return;
    final start = DateTime.now();
    for (var ev in sequence) {
      final scheduled = start.add(startDelay).add(ev.timeOffset);
      final delay = scheduled.difference(DateTime.now());
      if (delay > Duration.zero) {
        await Future.delayed(delay);
      }
      if (!_controller.isClosed) _controller.add(ev);
    }
  }

  /// Generate a scale sequence (ascending) according to the spec intervals.
  /// - [root] MIDI root (e.g., 60 == C4)
  /// - [scale] one of: 'major','natural_minor','harmonic_minor','melodic_minor'
  /// - [octaves] 1 or 2
  /// - [tempoBpm] used to place notes on quarter-note grid
  /// - [velocity] base velocity for perfect-play
  /// - [velocityVariance] max +/- variation per note
  /// - [seed] optional RNG seed for deterministic variance
  static List<SimulatedMidiNote> generateScale({
    int root = 60,
    String scale = 'major',
    int octaves = 1,
    double tempoBpm = 60.0,
    int velocity = 80,
    int velocityVariance = 3,
    int? seed,
  }) {
    // TODO: use `music_notes` Scale/Pitch APIs to generate note list instead
    // Example (pseudocode):
    // final rootPitch = Pitch.fromMidi(root);
    // final scalePitches = Scale.generate(rootPitch, ScaleType.fromName(scale), octaves);
    // convert scalePitches to MIDI numbers
    final intervals = _scaleIntervals(scale);
    final rng = seed == null ? Random() : Random(seed);
    final beatMs = (60000.0 / tempoBpm).round();
    final notes = <SimulatedMidiNote>[];
    var index = 0;
    for (var o = 0; o < octaves; o++) {
      for (var i = 0; i < intervals.length; i++) {
        final midi = root + intervals[i] + 12 * o;
        final varVel = velocityVariance > 0 ? rng.nextInt(velocityVariance * 2 + 1) - velocityVariance : 0;
        final vel = (velocity + varVel).clamp(0, 127);
        notes.add(SimulatedMidiNote(
          note: midi,
          velocity: vel,
          timeOffset: Duration(milliseconds: (index * beatMs)),
          noteOn: true,
        ));
        index++;
      }
    }
    // return ascending then a final return-to-root (optional)
    return notes;
  }

  /// Create a deterministic scenario from a list of MIDI note numbers.
  /// velocities can be provided per-note or a constant used.
  static List<SimulatedMidiNote> fromNoteList(List<int> notes,
      {double tempoBpm = 60, int velocity = 80}) {
    final beatMs = (60000.0 / tempoBpm).round();
    final out = <SimulatedMidiNote>[];
    for (var i = 0; i < notes.length; i++) {
      out.add(SimulatedMidiNote(
        note: notes[i],
        velocity: velocity,
        timeOffset: Duration(milliseconds: i * beatMs),
      ));
    }
    return out;
  }

  /// Scenario: perfect play where velocities equal target
  static List<SimulatedMidiNote> perfectPlay(List<int> notes,
      {double tempoBpm = 60, int velocity = 80}) {
    return fromNoteList(notes, tempoBpm: tempoBpm, velocity: velocity);
  }

  /// Scenario: consistent error (all velocities offset by delta)
  static List<SimulatedMidiNote> consistentError(List<int> notes,
      {double tempoBpm = 60, int velocity = 80, int delta = -20}) {
    return fromNoteList(notes,
        tempoBpm: tempoBpm, velocity: (velocity + delta).clamp(0, 127));
  }

  /// Scenario: random noise around velocity (deterministic with optional seed)
  static List<SimulatedMidiNote> randomNoise(List<int> notes,
      {double tempoBpm = 60, int baseVelocity = 80, int variance = 10, int? seed}) {
    final rng = seed == null ? Random() : Random(seed);
    final beatMs = (60000.0 / tempoBpm).round();
    final out = <SimulatedMidiNote>[];
    for (var i = 0; i < notes.length; i++) {
      final varVel = rng.nextInt(variance * 2 + 1) - variance;
      final vel = (baseVelocity + varVel).clamp(0, 127);
      out.add(SimulatedMidiNote(
        note: notes[i],
        velocity: vel,
        timeOffset: Duration(milliseconds: i * beatMs),
      ));
    }
    return out;
  }

  /// Dispose the stream controller when done.
  void dispose() {
    if (!_controller.isClosed) _controller.close();
  }

  static List<int> _scaleIntervals(String s) {
    switch (s) {
      case 'natural_minor':
      case 'minor_natural':
        return [0, 2, 3, 5, 7, 8, 10, 12];
      case 'harmonic_minor':
        return [0, 2, 3, 5, 7, 8, 11, 12];
      case 'melodic_minor':
        return [0, 2, 3, 5, 7, 9, 11, 12];
      case 'major':
      default:
        return [0, 2, 4, 5, 7, 9, 11, 12];
    }
  }
}
