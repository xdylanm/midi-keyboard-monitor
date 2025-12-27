class NoteEvent {
  final bool isNoteOn;
  final int channel;
  final int note;
  final int velocity;
  final int tsMs;

  NoteEvent({
    required this.isNoteOn,
    required this.channel,
    required this.note,
    required this.velocity,
    required this.tsMs,
  });

  @override
  String toString() => 'NoteEvent(${isNoteOn ? 'ON' : 'OFF'} ch:$channel n:$note v:$velocity ts:$tsMs)';
}
// Practice plan models aligned with app/lib/schemas/practice_plan.schema.json
class PracticePlan {
  final String? id;
  final String name;
  final String mode; // 'constant' | 'variable'
  final String key; // 'C', 'G#', etc.
  final String scaleType; // 'major' | 'minor'
  final String minorVariant; // 'natural'|'harmonic'|'melodic' (optional)
  final int octaves; // 1|2
  final String hand; // 'LH'|'RH'|'HT'
  final int tempoBpm;
  final int accuracyPercent;
  final String chordMode; // 'mean'|'per-voice'
  final HandSplit? handSplit;
  final List<ConstantTarget>? constantTargets;
  final List<VariableTarget>? variableTargets;
  final int notesPerMeasure;

  PracticePlan({
    this.id,
    required this.name,
    required this.mode,
    required this.key,
    required this.scaleType,
    this.minorVariant = 'natural',
    this.octaves = 1,
    this.hand = 'HT',
    this.tempoBpm = 60,
    this.accuracyPercent = 80,
    this.chordMode = 'mean',
    this.handSplit,
    this.constantTargets,
    this.variableTargets,
    this.notesPerMeasure = 4,
  });

  factory PracticePlan.fromJson(Map<String, dynamic> j) {
    // support older shapes where scaleType included variants like 'natural_minor'
    var scale = (j['scaleType'] as String?) ?? 'major';
    var minorVar = (j['minorVariant'] as String?) ?? 'natural';
    if (scale.contains('minor')) {
      // older format: 'natural_minor' etc.
      if (scale == 'natural_minor' || scale == 'harmonic_minor' || scale == 'melodic_minor') {
        minorVar = scale.split('_').first;
        scale = 'minor';
      }
    }

    HandSplit? hs;
    if (j['handSplit'] is Map<String, dynamic>) {
      hs = HandSplit.fromJson(Map<String, dynamic>.from(j['handSplit'] as Map));
    }

    List<ConstantTarget>? cts;
    if (j['constantTargets'] is List) {
      cts = (j['constantTargets'] as List).map((e) => ConstantTarget.fromJson(Map<String, dynamic>.from(e as Map))).toList();
    }

    List<VariableTarget>? vts;
    if (j['variableTargets'] is List) {
      vts = (j['variableTargets'] as List).map((e) => VariableTarget.fromJson(Map<String, dynamic>.from(e as Map))).toList();
    }

    return PracticePlan(
      id: j['id'] as String?,
      name: j['name'] as String? ?? 'Unnamed',
      mode: j['mode'] as String? ?? 'constant',
      key: j['key'] as String? ?? 'C',
      scaleType: scale,
      minorVariant: minorVar,
      octaves: (j['octaves'] as num?)?.toInt() ?? 1,
      hand: (j['hand'] as String?) ?? (j['handSplit'] is String ? j['handSplit'] as String : 'HT'),
      tempoBpm: (j['tempoBpm'] as num?)?.toInt() ?? 60,
      accuracyPercent: (j['accuracyPercent'] as num?)?.toInt() ?? 80,
      chordMode: (j['chordMode'] as String?) ?? 'mean',
      handSplit: hs,
      constantTargets: cts,
      variableTargets: vts,
      notesPerMeasure: (j['notesPerMeasure'] as num?)?.toInt() ?? 4,
    );
  }

  Map<String, dynamic> toJson() => {
        if (id != null) 'id': id,
        'name': name,
        'mode': mode,
        'key': key,
        'scaleType': scaleType,
        if (scaleType == 'minor') 'minorVariant': minorVariant,
        'octaves': octaves,
        'hand': hand,
        if (handSplit != null) 'handSplit': handSplit!.toJson(),
        if (constantTargets != null) 'constantTargets': constantTargets!.map((e) => e.toJson()).toList(),
        if (variableTargets != null) 'variableTargets': variableTargets!.map((e) => e.toJson()).toList(),
        'tempoBpm': tempoBpm,
        'accuracyPercent': accuracyPercent,
        'chordMode': chordMode,
        'notesPerMeasure': notesPerMeasure,
      };
}

class HandSplit {
  final String strategy; // e.g., 'automatic'
  final int splitMidiNote;
  HandSplit({required this.strategy, this.splitMidiNote = 60});
  factory HandSplit.fromJson(Map<String, dynamic> j) => HandSplit(strategy: j['strategy'] as String? ?? 'automatic', splitMidiNote: (j['splitMidiNote'] as num?)?.toInt() ?? 60);
  Map<String, dynamic> toJson() => {'strategy': strategy, 'splitMidiNote': splitMidiNote};
}

class ConstantTarget {
  final int octaveIndex;
  final String intensityLabel; // pp,p,mp,mf,f,ff
  ConstantTarget({required this.octaveIndex, required this.intensityLabel});
  factory ConstantTarget.fromJson(Map<String, dynamic> j) => ConstantTarget(octaveIndex: (j['octaveIndex'] as num).toInt(), intensityLabel: j['intensityLabel'] as String);
  Map<String, dynamic> toJson() => {'octaveIndex': octaveIndex, 'intensityLabel': intensityLabel};
}

class VariableTarget {
  final int octaveIndex;
  final double startIntensity;
  final double endIntensity;
  final String? direction; // crescendo/decrescendo
  VariableTarget({required this.octaveIndex, required this.startIntensity, required this.endIntensity, this.direction});
  factory VariableTarget.fromJson(Map<String, dynamic> j) => VariableTarget(octaveIndex: (j['octaveIndex'] as num).toInt(), startIntensity: (j['startIntensity'] as num).toDouble(), endIntensity: (j['endIntensity'] as num).toDouble(), direction: j['direction'] as String?);
  Map<String, dynamic> toJson() => {'octaveIndex': octaveIndex, 'startIntensity': startIntensity, 'endIntensity': endIntensity, if (direction != null) 'direction': direction};
}

// GlobalConfig aligned with app/lib/schemas/global_config.schema.json
class GlobalConfig {
  final String version;
  final String mapping; // linear|square_root|logarithmic
  final Calibration calibration;
  final bool autoBackupEnabled;

  GlobalConfig({required this.version, required this.mapping, required this.calibration, this.autoBackupEnabled = true});

  factory GlobalConfig.fromJson(Map<String, dynamic> j) {
    // Support older flat calibrationMin/calibrationMax fields for backwards compatibility
    Calibration cal;
    if (j['calibration'] is Map) {
      cal = Calibration.fromJson(Map<String, dynamic>.from(j['calibration'] as Map));
    } else {
      final min = (j['calibrationMin'] as num?)?.toDouble() ?? 0.0;
      final max = (j['calibrationMax'] as num?)?.toDouble() ?? 1.0;
      final mode = (j['mapping'] != null) ? 'manual' : 'none';
      cal = Calibration(mode: mode, min: min, max: max);
    }
    return GlobalConfig(
      version: j['version'] as String? ?? '1.0',
      mapping: j['mapping'] as String? ?? 'linear',
      calibration: cal,
      autoBackupEnabled: j['autoBackupEnabled'] as bool? ?? true,
    );
  }

  Map<String, dynamic> toJson() => {
        'version': version,
        'mapping': mapping,
        'calibration': calibration.toJson(),
        'autoBackupEnabled': autoBackupEnabled,
      };
}

class Calibration {
  final String mode; // 'none'|'manual'
  final double min;
  final double max;
  Calibration({required this.mode, required this.min, required this.max});
  factory Calibration.fromJson(Map<String, dynamic> j) => Calibration(mode: j['mode'] as String? ?? 'none', min: (j['min'] as num?)?.toDouble() ?? 0.0, max: (j['max'] as num?)?.toDouble() ?? 1.0);
  Map<String, dynamic> toJson() => {'mode': mode, 'min': min, 'max': max};
}
